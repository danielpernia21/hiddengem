"""
Hotel lookup via the RapidAPI "Booking.com" wrapper (booking-com15,
https://rapidapi.com/DataCrawler/api/booking-com15). Unofficial wrapper
around Booking.com's internal API — param/response names drift, and the
free tier has a small monthly quota (we've already hit it once testing
this file; check your remaining quota on the RapidAPI dashboard).

Needs env var: RAPIDAPI_KEY

--- Confirmed against live responses (2026-08-24) ---
  GET /api/v1/hotels/searchDestination?query=...
    -> {"data": [{"dest_id", "dest_type" (city/region/district/hotel/...),
                  "name", "city_name", ...}, ...]}
  GET /api/v1/hotels/searchHotels?dest_id=...&search_type=...&arrival_date=...
      &departure_date=...&adults=...&room_qty=...&currency_code=...&sort_by=...
    -> {"data": {"hotels": [{"hotel_id", "property": {"name", "reviewScore"
       (0-10, may be absent for un-reviewed places),
       "priceBreakdown": {"grossPrice": {"value"}}}}, ...]}}
    Already sorted by price (sort_by=price) and already carries the review
    score, so the area-search path filters on quality with zero extra calls.
  GET /api/v1/hotels/getRoomList?hotel_id=...&arrival_date=...&departure_date=...
      &adults=...&room_qty=...&currency_code=...&languagecode=...
    -> per-property room/price list, used when searchDestination resolves the
       region straight to one hotel instead of an area. No review score here,
       so this path calls getHotelReviewScores separately.
  GET /api/v1/hotels/getHotelReviewScores?hotel_id=...&languagecode=...
    -> {"data": {"score_breakdown": [{"customer_type": "total",
       "question": [{"question": "total", "score": <0-10>}, ...]}, ...]}}
    The "total"/"total" entry is the overall guest score across all reviews.
  GET /api/v1/hotels/getHotelDetails?hotel_id=...&arrival_date=...&departure_date=...
      &adults=...&room_qty=...&currency_code=...&languagecode=...
    -> {"data": {"url": "https://www.booking.com/hotel/{cc}/{slug}.html",
                 "soldout": 0|1, "available_rooms": <int>, ...}}
       The only endpoint with a real deep-link URL (searchHotels/getRoomList
       don't have one), and it also carries availability — so it doubles as
       our availability check instead of a separate getAvailability call.
       One extra call per pick, made only for a candidate that already
       passed the price/score filters.

Regions in regions.py are editorial descriptions ("Sierra de Ayllon",
"Lunigiana / Garfagnana"), not real bookable place names — plain
searchDestination on the raw region string resolves well under half the
time. _dest_id() tries a few fallback queries (full string, comma parts,
slash parts) and prefers an actual city/region/district match over a
same-named individual hotel, but expect a lot of "no hotel quote" until
regions.py grows a real per-region town name to search on.
"""

import os
from urllib.parse import quote_plus
import requests

TIMEOUT = 20
HOST = "booking-com15.p.rapidapi.com"
CURRENCY = "EUR"
AREA_TYPES = {"city", "region", "district", "country"}
MIN_REVIEW_SCORE = 7.0  # Booking's 0-10 guest score; ~3.5/5 stars doubled

_dest_cache = {}


def _headers():
    return {
        "X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": HOST,
    }


def _search_destination(query):
    r = requests.get(
        f"https://{HOST}/api/v1/hotels/searchDestination",
        params={"query": query},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def _dest_id(region):
    """Resolve an editorial region name to a Booking.com dest_id/type,
    preferring an actual place over a same-named individual hotel."""
    if region in _dest_cache:
        return _dest_cache[region]

    candidates = [region]
    if "," in region:
        candidates += [p.strip() for p in region.split(",")[::-1]]
    if "/" in region:
        candidates += [p.strip() for p in region.split("/")]

    area_hit, hotel_hit = None, None
    for q in candidates:
        for d in _search_destination(q):
            dtype = d.get("dest_type")
            if dtype in AREA_TYPES and area_hit is None:
                area_hit = (d["dest_id"], dtype)
            elif dtype == "hotel" and hotel_hit is None:
                hotel_hit = (d["dest_id"], "hotel")
        if area_hit:
            break

    result = area_hit or hotel_hit
    _dest_cache[region] = result
    return result


def _search_url(name, checkin, checkout, adults):
    """Booking.com hotel pages need a country+slug we don't reliably have
    (the API only gives a numeric hotel_id) — link to a search instead of
    guessing a page that 404s."""
    return (
        "https://www.booking.com/searchresults.html?"
        f"ss={quote_plus(name)}&checkin={checkin.isoformat()}"
        f"&checkout={checkout.isoformat()}&group_adults={adults}"
    )


def _review_score(hotel_id):
    """Overall 0-10 guest score, or None if unavailable/unreviewed."""
    r = requests.get(
        f"https://{HOST}/api/v1/hotels/getHotelReviewScores",
        params={"hotel_id": hotel_id, "languagecode": "en-us"},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        return None
    for entry in r.json().get("data", []):
        for block in entry.get("score_breakdown", []):
            if block.get("customer_type") != "total":
                continue
            for q in block.get("question", []):
                if q.get("question") == "total":
                    return q.get("score")
    return None


def _hotel_details(hotel_id, checkin, checkout, adults, fallback_name):
    """URL + availability in one call. Falls back to a search link (and
    treats availability as unknown-but-assumed-ok) on any failure, so a
    lookup never dies just for the nicer URL/availability check."""
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
        data = r.json().get("data", {})
        available = data.get("soldout") == 0 and data.get("available_rooms", 1) > 0
        return {
            "url": data.get("url") or _search_url(fallback_name, checkin, checkout, adults),
            "available": available,
        }
    except Exception:
        return {"url": _search_url(fallback_name, checkin, checkout, adults),
                "available": True}


def _cheapest_in_area(dest_id, dest_type, checkin, checkout, adults):
    r = requests.get(
        f"https://{HOST}/api/v1/hotels/searchHotels",
        params={
            "dest_id": dest_id,
            "search_type": dest_type.upper(),
            "arrival_date": checkin.isoformat(),
            "departure_date": checkout.isoformat(),
            "adults": adults,
            "room_qty": 1,
            "page_number": 1,
            "currency_code": CURRENCY,
            "sort_by": "price",
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        return None
    candidates = []
    for h in r.json().get("data", {}).get("hotels", []):
        try:
            prop = h["property"]
            price = float(prop["priceBreakdown"]["grossPrice"]["value"])
            name = prop["name"]
            hotel_id = h["hotel_id"]
        except (KeyError, TypeError, ValueError):
            continue
        score = prop.get("reviewScore")
        candidates.append((price, name, hotel_id, score))
    candidates.sort(key=lambda c: c[0])  # cheapest first; API sort_by=price, but don't trust it blindly

    for price, name, hotel_id, score in candidates:
        if score is None or score < MIN_REVIEW_SCORE:
            continue
        details = _hotel_details(hotel_id, checkin, checkout, adults, name)
        if not details["available"]:
            continue
        return {"price": price, "hotel": name, "score": score, "url": details["url"]}
    return None


def _one_hotel_price(hotel_id, checkin, checkout, adults):
    r = requests.get(
        f"https://{HOST}/api/v1/hotels/getRoomList",
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
    if r.status_code != 200:
        return None
    rooms = r.json().get("data", [])
    if isinstance(rooms, dict):
        rooms = rooms.get("rooms", [])
    best = None
    for room in rooms:
        try:
            price = float(room["price"]["value"])
            name = room.get("roomName") or room.get("name") or "hotel"
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or price < best["price"]:
            best = {"price": price, "hotel": name}
    if not best:
        return None

    score = _review_score(hotel_id)
    if score is None or score < MIN_REVIEW_SCORE:
        return None
    details = _hotel_details(hotel_id, checkin, checkout, adults, best["hotel"])
    if not details["available"]:
        return None
    best["score"] = score
    best["url"] = details["url"]
    return best


def cheapest(region, checkin, checkout, adults=1):
    dest = _dest_id(region)
    if not dest:
        return None
    dest_id, dest_type = dest
    if dest_type in AREA_TYPES:
        return _cheapest_in_area(dest_id, dest_type, checkin, checkout, adults)
    return _one_hotel_price(dest_id, checkin, checkout, adults)


def cheapest_safe(region, checkin, checkout, adults=1):
    """Like cheapest(), but never lets a dead lookup kill the run."""
    if "RAPIDAPI_KEY" not in os.environ:
        return None
    try:
        return cheapest(region, checkin, checkout, adults)
    except Exception as e:
        print(f"  ! hotel lookup {region}: {type(e).__name__}: {e}")
        return None
