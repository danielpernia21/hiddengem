# travelbot

Three quiet, priced, reachable trips from BCN. Sundays, on Telegram. One user: you.

## Setup (~30 min)

**1. Telegram bot**

Open Telegram, message `@BotFather` → `/newbot` → name it → copy the token.
Then message your new bot anything, and get your chat id:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getUpdates" | grep -o '"id":[0-9-]*' | head -1
```

**2. Run locally**

```bash
pip install requests
export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... FARE_PROVIDER=ryanair
python main.py --dry     # prints, sends nothing
python main.py           # sends for real
```

**3. Schedule it**

Push to a private GitHub repo. Settings → Secrets: `TELEGRAM_TOKEN`,
`TELEGRAM_CHAT_ID`, optionally `TRAVELPAYOUTS_TOKEN`. Variables: `ORIGIN`,
`FARE_PROVIDER`. The workflow does the rest. Free.

## Fare providers

- `ryanair` (default) — no key, works immediately, unofficial endpoint.
- `travelpayouts` — sign up at travelpayouts.com, free, wider coverage,
  and the links are affiliate links if this ever becomes a product.
  Verify the v3 param names against their docs before trusting the output.

Amadeus Self-Service was decommissioned on 17 July 2026. Don't go looking.

## What to actually do with it

Nothing, for eight weeks. Just react to the buttons. Then:

```bash
sort feedback.jsonl | python -c "import sys,json,collections; \
c=collections.Counter(json.loads(l)['label'] for l in sys.stdin); print(c)"
```

**Success:** you book one trip.
**Kill it:** you stop tapping by week four, or the same 10 regions keep cycling.

Do not add a web UI. Do not add accounts. Do not add other users.
