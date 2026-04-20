# ============================================================
# telegram.py — public and private channel routing
# ============================================================

import requests
import logging
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_PRIVATE_ID, LOG_PATH

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [TELEGRAM] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def _send(text, chat_id, parse_mode="Markdown"):
    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }, timeout=10)
        r.raise_for_status()
        log.info(f"Sent to {chat_id} ({len(text)} chars)")
        return True
    except Exception as e:
        log.error(f"Telegram send failed [{chat_id}]: {e}")
        return False


def send_public_buttons(text, buttons, parse_mode="Markdown"):
    """Send to public channel with inline URL buttons."""
    try:
        keyboard = {"inline_keyboard": buttons}
        r = requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       text,
            "parse_mode": parse_mode,
            "reply_markup": keyboard,
            "disable_web_page_preview": True
        }, timeout=10)
        r.raise_for_status()
        log.info(f"Sent+buttons to {TELEGRAM_CHAT_ID} ({len(text)} chars)")
        return True
    except Exception as e:
        log.error(f"Telegram button send failed: {e}")
        return False

def send_public(text, parse_mode="Markdown"):
    """Public channel — alerts, results, digests."""
    return _send(text, TELEGRAM_CHAT_ID, parse_mode)

def send_private(text, parse_mode="Markdown"):
    """Your private chat — start/stop, errors, ROI summaries."""
    return _send(text, TELEGRAM_PRIVATE_ID, parse_mode)

def send(text, parse_mode="Markdown", chat_id=None):
    """Legacy helper — defaults to public."""
    return _send(text, chat_id or TELEGRAM_CHAT_ID, parse_mode)
