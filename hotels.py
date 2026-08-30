"""
Hotel lookup via the RapidAPI "Booking.com" wrapper (booking-com15,
https://rapidapi.com/DataCrawler/api/booking-com15). Unofficial wrapper
around Booking.com's internal API — param/response names drift, and the
free tier hard-caps at 50 requests/month across ALL endpoints combined
(checked live 2026-08-30: X-RateLimit-requests-Limit: 50). That cap, not
raw correctness, drives most of the design below — minimize calls first.

Needs env var: RAPIDAPI_KEY

--- Confirmed against live responses (2026-08-30) ---
  GET /api/v1/meta/locationToLatLong?query=...
    -> {"data": [{"geometry": {"location": {"lat", "lng"}}, ...}, ...]}
    Google-Places-backed geocoding. Resolves editorial region names
    ("Sierra de Ayllon") that plain searchDestination mostly misses
    (that endpoint expects real bookable place names, and regions.py is
    deliberately not that). Region names never move, so results are
    cached to disk FOREVER in geo_cache.json (committed by CI) — this
    call should only ever fire once per region across the life of the
    project, not once per run.
  GET /api/v1/hotels/searchHotelsByCoordinates?latitude=...&longitude=...
      &radius=...&arrival_date=...&departure_date=...&adults=...&room_qty=...
      &currency_code=...
    -> {"data": {"result": [{"hotel_id", "hotel_name", "review_score"
       (0-10, absent for un-reviewed places), "soldout" (0/1),
       "min_total_price"}, ...]}}
    radius is in km and matters: without it this returns ~4000 hotels
    across the whole metro area (e.g. as far as Madrid for a rural
    Guadalajara region), not "nearby". review_score, soldout and price
    all come back in this one call, so filtering/picking the cheapest
    candidate needs no second call — the details call below only fires
    once, for the single winning pick.
  GET /api/v1/hotels/getHotelDetails?hotel_id=...&arrival_date=...
      &departure_date=...&adults=...&room_qty=...&currency_code=...
    -> {"data": {"url": "https://www.booking.com/hotel/{cc}/{slug}.html", ...}}
    The only endpoint with a real deep-link URL (searchHotelsByCoordinates
    doesn't have one). Called only for the already-filtered winning pick,
    not per candidate, so it's one extra call per successful hotel match —
    same cost pattern the old dest_id design used for the same reason.

Old approach (searchDestination -> dest_id -> searchHotels/getRoomList)
is retired: it burned 2-3 calls per pick and re-resolved every region
from scratch each run (in-memory-only cache), for worse hit rate than
geocoding + a radius search gives here.
"""

import os
import json
import pathlib
from urllib.parse import quote_plus
import requests

TIMEOUT = 20
HOST = "booking-com15.p.rapidapi.com"
CURRENCY = "EUR"
RADIUS_KM = 15
MIN_REVIEW_SCORE = 7.0  # Booking's 0-10 guest score; strictly above, not >=

GEO_CACHE = pathlib.Path(__file__).parent / "geo_cache.json"


def _headers():
    return {
        "X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": HOST,
    }


def _load_geo_cache():
    if GEO_CACHE.exists():
        return json.loads(GEO_CACHE.read_text())
    return {}


def _save_geo_cache(cache):
    GEO_CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def _geocode_query(query):
    r = requests.get(
        f"https://{HOST}/api/v1/meta/locationToLatLong",
        params={"query": query},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    results = r.json().get("data", [])
    loc = results[0]["geometry"]["location"] if results else None
    return (loc["lat"], loc["lng"]) if loc else None


def _geocode(region):
    """Region name -> (lat, lng), cached to disk forever once resolved.
    regions.py names are editorial ("Lunigiana / Garfagnana"), so on a
    bare miss also try the slash/comma parts before giving up — but only
    cache a hit, so a transient miss gets retried next run instead of
    dead-caching the region forever."""
    cache = _load_geo_cache()
    if region in cache and cache[region]:
        return tuple(cache[region])

    candidates = [region]
    if "/" in region:
        candidates += [p.strip() for p in region.split("/")]
    if "," in region:
        candidates += [p.strip() for p in region.split(",")[::-1]]

    coords = None
    for q in candidates:
        coords = _geocode_query(q)
        if coords:
            break

    if coords:
        cache[region] = list(coords)
        _save_geo_cache(cache)
    return coords


def _search_url(name, checkin, checkout, adults):
    """Booking.com hotel pages need a country+slug we don't reliably have
    (the API only gives a numeric hotel_id) — link to a search instead of
    guessing a page that 404s."""
    return (
        "https://www.booking.com/searchresults.html?"
        f"ss={quote_plus(name)}&checkin={checkin.isoformat()}"
        f"&checkout={checkout.isoformat()}&group_adults={adults}"
    )


def _hotel_url(hotel_id, checkin, checkout, adults, fallback_name):
    """Real Booking.com deep link for a hotel. Falls back to a search
    link on any failure so a lookup never dies just for the nicer URL."""
    try:
        r = requests.get(
            f"https://{HOST}/api/v1/hotels/getHotelDetails",
            params={
                "hotel_id": hotel_id,
                "arrival_date": checkin.isoformat(),
                "departure_date": checkout.isoformat(),
                "adults": adults,
                "room_qty": 1,
                "units": "metric",
                "temperature_unit": "c",
                "languagecode": "en-us",
                "currency_code": CURRENCY,
            },
            headers=_headers(),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("data", {}).get("url") or _search_url(
            fallback_name, checkin, checkout, adults)
    except Exception:
        return _search_url(fallback_name, checkin, checkout, adults)


def _cheapest_near(lat, lng, checkin, checkout, adults):
    r = requests.get(
        f"https://{HOST}/api/v1/hotels/searchHotelsByCoordinates",
        params={
            "latitude": lat,
            "longitude": lng,
            "radius": RADIUS_KM,
            "arrival_date": checkin.isoformat(),
            "departure_date": checkout.isoformat(),
            "adults": adults,
            "room_qty": 1,
            "page_number": 1,
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": CURRENCY,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        print(f"  ! hotels search {r.status_code}: {r.text[:200]}")
        return None

    candidates = []
    for h in r.json().get("data", {}).get("result", []):
        try:
            price = float(h["min_total_price"])
            name = h["hotel_name"]
            hotel_id = h["hotel_id"]
        except (KeyError, TypeError, ValueError):
            continue
        if h.get("soldout"):
            continue
        score = h.get("review_score")
        if score is None or score <= MIN_REVIEW_SCORE:
            continue
        candidates.append((price, name, hotel_id, score))

    if not candidates:
        return None
    price, name, hotel_id, score = min(candidates, key=lambda c: c[0])
    return {
        "price": price,
        "hotel": name,
        "score": score,
        "url": _hotel_url(hotel_id, checkin, checkout, adults, name),
    }


def cheapest(region, checkin, checkout, adults=1):
    coords = _geocode(region)
    if not coords:
        return None
    lat, lng = coords
    return _cheapest_near(lat, lng, checkin, checkout, adults)


def cheapest_safe(region, checkin, checkout, adults=1):
    """Like cheapest(), but never lets a dead lookup kill the run."""
    if "RAPIDAPI_KEY" not in os.environ:
        return None
    try:
        return cheapest(region, checkin, checkout, adults)
    except Exception as e:
        print(f"  ! hotel lookup {region}: {type(e).__name__}: {e}")
        return None
