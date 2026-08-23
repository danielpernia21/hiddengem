#!/usr/bin/env python3
"""
Collects your button taps. Run daily.

This file is the whole point. The rejection log is the spec for v2 —
it is the only honest signal about your taste you will ever get.
"""

import os
import json
import pathlib
import datetime as dt
import requests

API = "https://api.telegram.org/bot{}/{}"
HERE = pathlib.Path(__file__).parent
OFFSET = HERE / "offset.json"
LOG = HERE / "feedback.jsonl"

LABELS = {"yes": "booking it", "maybe": "maybe", "far": "too far",
          "seen": "been there", "dull": "boring"}


def main():
    token = os.environ["TELEGRAM_TOKEN"]
    offset = json.loads(OFFSET.read_text())["offset"] if OFFSET.exists() else 0

    r = requests.get(API.format(token, "getUpdates"),
                     params={"offset": offset, "timeout": 5}, timeout=20)
    r.raise_for_status()
    updates = r.json().get("result", [])

    with LOG.open("a") as fh:
        for u in updates:
            offset = max(offset, u["update_id"] + 1)
            cq = u.get("callback_query")
            if not cq:
                continue
            verdict, airport = (cq["data"].split("|") + [""])[:2]
            fh.write(json.dumps({
                "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "airport": airport,
                "verdict": verdict,
                "label": LABELS.get(verdict, verdict),
            }) + "\n")
            requests.post(API.format(token, "answerCallbackQuery"),
                          json={"callback_query_id": cq["id"],
                                "text": LABELS.get(verdict, "noted")},
                          timeout=20)
            print(f"{airport}: {LABELS.get(verdict, verdict)}")

    OFFSET.write_text(json.dumps({"offset": offset}))


if __name__ == "__main__":
    main()
