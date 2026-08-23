"""Telegram delivery. One message per suggestion so feedback maps 1:1."""

import os
import html
import requests

API = "https://api.telegram.org/bot{}/{}"
TIMEOUT = 20

BUTTONS = [
    [("Booking it", "yes"), ("Maybe", "maybe")],
    [("Too far", "far"), ("Been there", "seen"), ("Boring", "dull")],
]


def _call(method, payload):
    token = os.environ["TELEGRAM_TOKEN"]
    r = requests.post(API.format(token, method), json=payload, timeout=TIMEOUT)
    if not r.ok:
        raise RuntimeError(f"Telegram {method} failed ({r.status_code}): {r.text}")
    return r.json()


def send_suggestion(pick):
    """pick: dict with region, code, price, depart, nights, why, quiet, url"""
    text = (
        f"<b>{html.escape(pick['region'])}</b>\n"
        f"fly {os.getenv('ORIGIN', 'BCN')} → {pick['code']} · "
        f"{pick['depart']} · {pick['nights']} nights · <b>{pick['price']:.0f}€</b>\n\n"
        f"{html.escape(pick['why'])}\n"
        f"<i>quiet score {pick['quiet']}/5</i>"
    )
    keyboard = [
        [{"text": label, "callback_data": f"{code}|{pick['code']}"} for label, code in row]
        for row in BUTTONS
    ]
    keyboard.append([{"text": "See fares", "url": pick["url"]}])
    return _call("sendMessage", {
        "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": keyboard},
    })


def send_plain(text):
    return _call("sendMessage", {
        "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        "text": text,
    })
