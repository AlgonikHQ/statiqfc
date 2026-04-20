import re

# ── Read current files ────────────────────────────────────────
with open("/root/statiq/bot/telegram.py", "r") as f:
    tg = f.read()

with open("/root/statiq/bot/telegram_cards.py", "r") as f:
    cards = f.read()

# ── Patch telegram.py — add send_public_with_buttons ─────────
button_func = '''
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
'''

tg = tg.replace(
    'def send_public(text, parse_mode="Markdown"):',
    button_func + '\ndef send_public(text, parse_mode="Markdown"):'
)

with open("/root/statiq/bot/telegram.py", "w") as f:
    f.write(tg)

# ── Patch telegram_cards.py — add buttons to each card ───────

# Button sets
BUTTONS_ALERT = '''
def buttons_edge_alert(home, away):
    hs = home.replace(" ", "+")
    as_ = away.replace(" ", "+")
    query = f"{hs}+vs+{as_}+premier+league"
    return [
        [
            {"text": "📊 Sofascore",   "url": f"https://www.sofascore.com/search/{query}"},
            {"text": "🔢 Flashscore",  "url": f"https://www.flashscore.com/search/?q={hs}+{as_}"}
        ],
        [
            {"text": "📈 Whoscored",   "url": f"https://www.whoscored.com"},
            {"text": "🏆 PL Website",  "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "⚠️ Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]

def buttons_result():
    return [
        [
            {"text": "📊 Full ROI",     "url": "https://t.me/StatiqFC"},
            {"text": "📅 PL Fixtures",  "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"}
        ]
    ]

def buttons_digest():
    return [
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"},
            {"text": "📈 Whoscored",   "url": "https://www.whoscored.com/Regions/252/Tournaments/2/Seasons/9618/Stages/22076/Show/England-Premier-League-2024-2025"}
        ],
        [
            {"text": "🔢 Flashscore",  "url": "https://www.flashscore.com/football/england/premier-league/"},
            {"text": "📊 Sofascore",   "url": "https://www.sofascore.com/tournament/football/england/premier-league/17"}
        ]
    ]

def buttons_weekly():
    return [
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"},
            {"text": "📊 Sofascore",   "url": "https://www.sofascore.com/tournament/football/england/premier-league/17"}
        ],
        [
            {"text": "📈 Whoscored",   "url": "https://www.whoscored.com"},
            {"text": "🔢 Flashscore",  "url": "https://www.flashscore.com/football/england/premier-league/"}
        ]
    ]

def buttons_vip():
    return [
        [
            {"text": "📊 Our Record",  "url": "https://t.me/StatiqFC"},
            {"text": "⚠️ Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]
'''

cards = cards.replace(
    "from datetime import datetime",
    "from datetime import datetime\n" + BUTTONS_ALERT
)

with open("/root/statiq/bot/telegram_cards.py", "w") as f:
    f.write(cards)

print("✅ Patch applied — buttons added to telegram.py and telegram_cards.py")
