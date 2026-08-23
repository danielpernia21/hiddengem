#!/usr/bin/env python3
"""
Weekly run. Picks 3 quiet, reachable, priced trips and pushes them to Telegram.

  python main.py          send for real
  python main.py --dry    print to stdout, send nothing, touch no state
"""

import sys
import json
import pathlib
import datetime as dt

import fares
import notify
from regions import REGIONS

# --- knobs. Change these, not the code. -------------------------------------
MAX_PRICE = 180         # euros, return
MIN_QUIET = 3           # drop anything you scored below this
LEAD_MIN_DAYS = 14      # earliest departure
LEAD_MAX_DAYS = 70      # latest departure
MIN_NIGHTS, MAX_NIGHTS = 3, 5
COOLDOWN_DAYS = 56      # no region repeats inside 8 weeks
N_PICKS = 3
# ----------------------------------------------------------------------------

STATE = pathlib.Path(__file__).parent / "state.json"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True))


def eligible(state, today):
    window_start = today + dt.timedelta(days=LEAD_MIN_DAYS)
    window_end = today + dt.timedelta(days=LEAD_MAX_DAYS)
    for code, region, quiet, months, why in REGIONS:
        if quiet < MIN_QUIET:
            continue
        # in season at some point inside the window
        span = {(window_start + dt.timedelta(days=d)).month
                for d in range(0, (window_end - window_start).days + 1, 7)}
        if not span & set(months):
            continue
        last = state.get(region)
        if last and (today - dt.date.fromisoformat(last)).days < COOLDOWN_DAYS:
            continue
        yield {"code": code, "region": region, "quiet": quiet, "why": why}


def main(dry=False):
    sys.stdout.reconfigure(encoding="utf-8")
    today = dt.date.today()
    state = load_state()
    window_start = today + dt.timedelta(days=LEAD_MIN_DAYS)
    window_end = today + dt.timedelta(days=LEAD_MAX_DAYS)

    candidates = list(eligible(state, today))
    print(f"{len(candidates)} regions eligible for {window_start} → {window_end}")

    priced = []
    seen_airports = set()
    for c in candidates:
        fare = fares.cheapest(c["code"], window_start, window_end,
                              MIN_NIGHTS, MAX_NIGHTS)
        if not fare or fare["price"] > MAX_PRICE:
            continue
        priced.append({**c, **fare})
        print(f"  ✓ {c['region']:<35} {fare['price']:>6.0f}€  {fare['depart']}")

    # quiet first, price as tiebreak. One pick per airport.
    priced.sort(key=lambda p: (-p["quiet"], p["price"]))
    picks = []
    for p in priced:
        if p["code"] in seen_airports:
            continue
        seen_airports.add(p["code"])
        picks.append(p)
        if len(picks) == N_PICKS:
            break

    if not picks:
        msg = (f"Nothing under {MAX_PRICE}€ this week. "
               f"{len(candidates)} regions checked.")
        print(msg)
        if not dry:
            notify.send_plain(msg)
        return

    for p in picks:
        if dry:
            print(f"\n{p['region']} ({p['code']}) — {p['price']:.0f}€ "
                  f"{p['depart']} {p['nights']}n\n{p['why']}\n{p['url']}")
        else:
            notify.send_suggestion(p)
            state[p["region"]] = today.isoformat()

    if not dry:
        save_state(state)
    print(f"\nsent {len(picks)}")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
