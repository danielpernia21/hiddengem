"""
Fare lookup. Two providers behind one interface so you can swap without
touching main.py.

Amadeus Self-Service is dead (portal decommissioned 17 July 2026), so:

  travelpayouts  - free with an affiliate account, gives you booking links
                   you can monetise later. Needs TRAVELPAYOUTS_TOKEN.
  ryanair        - unofficial public endpoint, no key, works tonight.
                   Covers a big slice of the BCN/GRO low-cost network.
                   Unofficial means it can change without notice.

Both return: {"price": float, "depart": "YYYY-MM-DD", "url": str} or None.
"""

import os
import datetime as dt
import requests

TIMEOUT = 20
ORIGIN = os.getenv("ORIGIN", "BCN")
CURRENCY = "EUR"


# ---------------------------------------------------------------- travelpayouts

def _travelpayouts(dest, window_start, window_end, min_nights, max_nights):
    token = os.environ["TRAVELPAYOUTS_TOKEN"]
    # NOTE: verify param names against current docs before trusting output.
    r = requests.get(
        "https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
        params={
            "origin": ORIGIN,
            "destination": dest,
            "departure_at": window_start.strftime("%Y-%m"),
            "currency": CURRENCY.lower(),
            "sorting": "price",
            "one_way": "false",
            "direct": "true",
            "limit": 30,
        },
        headers={"X-Access-Token": token},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    best = None
    for item in r.json().get("data", []):
        try:
            dep = dt.date.fromisoformat(item["departure_at"][:10])
            ret = dt.date.fromisoformat(item["return_at"][:10])
        except (KeyError, ValueError):
            continue
        nights = (ret - dep).days
        if not (window_start <= dep <= window_end):
            continue
        if not (min_nights <= nights <= max_nights):
            continue
        if dep.weekday() not in (3, 4):  # Thu / Fri only
            continue
        price = float(item["price"])
        if best is None or price < best["price"]:
            best = {
                "price": price,
                "depart": dep.isoformat(),
                "nights": nights,
                "url": "https://www.aviasales.com" + item.get("link", ""),
            }
    return best


# --------------------------------------------------------------------- ryanair

def _ryanair(dest, window_start, window_end, min_nights, max_nights):
    r = requests.get(
        "https://services-api.ryanair.com/farfnd/v4/roundTripFares",
        params={
            "departureAirportIataCode": ORIGIN,
            "arrivalAirportIataCode": dest,
            "outboundDepartureDateFrom": window_start.isoformat(),
            "outboundDepartureDateTo": window_end.isoformat(),
            "inboundDepartureDateFrom": window_start.isoformat(),
            "inboundDepartureDateTo": (window_end + dt.timedelta(days=max_nights)).isoformat(),
            "durationFrom": min_nights,
            "durationTo": max_nights,
            "currency": CURRENCY,
            "limit": 20,
            "market": "es-es",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        return None
    best = None
    for f in r.json().get("fares", []):
        try:
            out, inb = f["outbound"], f["inbound"]
            dep = dt.date.fromisoformat(out["departureDate"][:10])
            ret = dt.date.fromisoformat(inb["departureDate"][:10])
            price = float(out["price"]["value"]) + float(inb["price"]["value"])
            nights = (ret - dep).days
        except (KeyError, ValueError, TypeError):
            continue
        if dep.weekday() not in (3, 4):
            continue
        if best is None or price < best["price"]:
            best = {
                "price": price,
                "depart": dep.isoformat(),
                "nights": nights,
                "url": f"https://www.ryanair.com/es/es/trip/flights/select?adults=1"
                       f"&originIata={ORIGIN}&destinationIata={dest}"
                       f"&dateOut={dep.isoformat()}&dateIn={ret.isoformat()}",
            }
    return best


PROVIDERS = {"travelpayouts": _travelpayouts, "ryanair": _ryanair}


def cheapest(dest, window_start, window_end, min_nights=3, max_nights=5):
    fn = PROVIDERS[os.getenv("FARE_PROVIDER", "ryanair")]
    try:
        return fn(dest, window_start, window_end, min_nights, max_nights)
    except Exception as e:  # never let one dead airport kill the run
        print(f"  ! {dest}: {type(e).__name__}: {e}")
        return None
