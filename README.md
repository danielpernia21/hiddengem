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

## Hotel prices

Optional. Set `RAPIDAPI_KEY` (sign up at rapidapi.com, subscribe to the
"Booking.com" API — host `booking-com15.p.rapidapi.com`, free tier has a
small monthly quota, watch it) and picks get a cheapest-hotel quote and
booking link added, shown as flight + hotel = total. Unset, `hotels.py` is
skipped silently and picks show flight price only, same as before.

Hotels are filtered to guest score ≥ 7.0/10 (Booking's 0-10 scale — roughly
3.5/5 stars doubled, see `MIN_REVIEW_SCORE` in `hotels.py`) with confirmed
availability for the trip dates; the cheapest one clearing both bars wins.

Env var must be set as a proper Windows environment variable (not `.env` —
this project doesn't load one) *before* the shell/terminal you run `python`
in is opened; a shell started earlier won't see a var added after the fact.

One known gap, see `hotels.py`'s module docstring for detail: regions in
`regions.py` are editorial descriptions ("Sierra de Ayllon"), not real place
names Booking.com's search recognizes — lookups resolve well under half the
time even with fallback queries. Expect "no hotel quote" for those until
regions get a real nearby town name to search on.

## What to actually do with it

Nothing, for eight weeks. Just react to the buttons. Then:

```bash
sort feedback.jsonl | python -c "import sys,json,collections; \
c=collections.Counter(json.loads(l)['label'] for l in sys.stdin); print(c)"
```

**Success:** you book one trip.
**Kill it:** you stop tapping by week four, or the same 10 regions keep cycling.

Do not add a web UI. Do not add accounts. Do not add other users.
