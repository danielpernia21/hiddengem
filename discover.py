#!/usr/bin/env python3
"""
Two jobs:
  1. What can I fly to from BCN, and for how much?
  2. Which of those airports have no row in regions.py yet?

    python discover.py            # next 10 weeks, everything
    python discover.py --max 150  # only under 150 EUR

Both endpoints are unofficial. If they 404, Ryanair changed something —
fall back to their route map page and copy the list by hand once.
Vueling is BCN's biggest carrier and has no public API, so its routes
have to be added manually. Worth doing: it serves the quiet French,
Italian and Spanish regional airports Ryanair skips.
"""

import sys
import datetime as dt
import requests

from regions import REGIONS

ORIGIN = "BCN"
UA = {"User-Agent": "Mozilla/5.0"}
COVERED = {code for code, *_ in REGIONS}


def network():
    """Every airport BCN has a route to."""
    r = requests.get(
        f"https://services-api.ryanair.com/views/locate/searchWidget/routes/en/airport/{ORIGIN}",
        headers=UA, timeout=30)
    r.raise_for_status()
    out = {}
    for item in r.json():
        ap = item.get("arrivalAirport", {})
        code = ap.get("iataCode")
        if code:
            out[code] = (ap.get("name", "?"),
                         ap.get("country", {}).get("name", "?"))
    return out


def fares(weeks=10, min_nights=3, max_nights=5):
    """Cheapest return to EVERY destination. One call, no destination param."""
    today = dt.date.today()
    start = today + dt.timedelta(days=14)
    end = today + dt.timedelta(weeks=weeks)
    r = requests.get(
        "https://services-api.ryanair.com/farfnd/v4/roundTripFares",
        params={
            "departureAirportIataCode": ORIGIN,
            "outboundDepartureDateFrom": start.isoformat(),
            "outboundDepartureDateTo": end.isoformat(),
            "inboundDepartureDateFrom": start.isoformat(),
            "inboundDepartureDateTo": (end + dt.timedelta(days=max_nights)).isoformat(),
            "durationFrom": min_nights,
            "durationTo": max_nights,
            "currency": "EUR",
            "limit": 500,
            "market": "es-es",
        },
        headers=UA, timeout=60)
    r.raise_for_status()
    out = {}
    for f in r.json().get("fares", []):
        try:
            code = f["outbound"]["arrivalAirport"]["iataCode"]
            price = float(f["summary"]["price"]["value"])
            dep = f["outbound"]["departureDate"][:10]
        except (KeyError, TypeError, ValueError):
            continue
        if code not in out or price < out[code][0]:
            out[code] = (price, dep)
    return out


def main():
    cap = float(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 1e9

    try:
        net = network()
    except Exception as e:
        print(f"routes endpoint failed ({e}); using fares only")
        net = {}

    priced = fares()
    print(f"{len(net)} routes known, {len(priced)} with a fare in window\n")

    rows = sorted(priced.items(), key=lambda kv: kv[1][0])
    print(f"{'':2} {'APT':<4} {'PRICE':>7}  {'DEPART':<11} AIRPORT")
    for code, (price, dep) in rows:
        if price > cap:
            continue
        name = net.get(code, ("?", "?"))[0]
        mark = "  " if code in COVERED else "→ "   # → means no region row yet
        print(f"{mark} {code:<4} {price:>6.0f}€  {dep:<11} {name}")

    gaps = [c for c, _ in rows if c not in COVERED]
    print(f"\n{len(gaps)} airports with fares but no region row:")
    print(" ".join(gaps))
    print("\nFor each: what is 60-120 min inland that isn't why people fly there?")


if __name__ == "__main__":
    main()