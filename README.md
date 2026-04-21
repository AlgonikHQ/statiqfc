# StatiqFC ⚽

**A fully automated Premier League stats service.**
No tips. No hype. Just data — delivered to Telegram before every match.

---

## What it does

- Pulls Premier League fixtures, form, H2H and xG from free public data sources
- Scans each fixture for statistical edge conditions (BTTS, clean sheets, over/under)
- Pushes a clean Telegram card 2 hours before kick-off — max 2 alerts per day
- Logs every selection as a **paper portfolio** with a £25 / £10 displayed stake
- Tracks W/L, P&L and ROI live on a public dashboard
- Auto-settles results and updates the ROI tracker after every match

**VIP tier opens when we hit +20% ROI over 50 selections.** That target is pinned publicly from day one.

---

## Paper portfolio rules

| Type | Displayed stake |
|---|---|
| Standard selection | £25 |
| Builder single | £10 |

No real money is placed. This is a public accountability tracker only.

---

## Data sources (all free)

| Source | Used for |
|---|---|
| [football-data.org](https://football-data.org) | Fixtures, results, form, H2H |
| [Understat](https://understat.com) | xG post-match (scraped) |
| [The Odds API](https://the-odds-api.com) | Odds snapshot at alert time (free tier) |

---

## Stack

- Python 3.11 on Ubuntu 24.04 (Hetzner VPS)
- SQLite local cache
- `schedule` for task scheduling
- Telegram Bot API for delivery
- GitHub Pages for public dashboard

---

## Project structure

```
statiq/
├── bot/
│   ├── config.py          # all constants
│   ├── database.py        # SQLite schema + helpers
│   ├── fetcher.py         # data pulls from all sources
│   ├── scanner.py         # edge condition detection
│   ├── telegram_cards.py  # message templates
│   ├── telegram.py        # send helper
│   ├── statiq_bot.py      # main entry point / scheduler
│   └── requirements.txt
├── dashboard/
│   ├── index.html         # public ROI tracker (GitHub Pages)
│   └── roi.json           # written by bot after every result
└── statiq.service         # systemd unit file
```

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/statiq-fc
cd statiq-fc/bot
cp config.py config.py.bak
# Edit config.py — add your API keys and Telegram credentials
```

### 2. Install dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 3. Create data directory

```bash
mkdir -p /root/statiq/data
```

### 4. Deploy service

```bash
cp ../statiq.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable statiq.service
systemctl start statiq.service
```

### 5. Deploy dashboard

Push `dashboard/` to a GitHub Pages branch. The bot writes `roi.json` to `/root/statiq/dashboard/` — you'll need a sync script or GitHub Action to push it after each update (see wiki).

---

## Keys needed

| Key | Where to get it |
|---|---|
| `FD_API_KEY` | [football-data.org](https://www.football-data.org/client/register) — free |
| `ODDS_API_KEY` | [the-odds-api.com](https://the-odds-api.com) — free tier |
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/botfather) on Telegram |
| `TELEGRAM_CHAT_ID` | Your public channel ID |

---

## Disclaimer

StatiqFC is a statistical data service. It does not provide financial or betting advice.
All displayed stakes are paper only — no real money is placed.
18+. Gamble responsibly. [BeGambleAware.org](https://www.begambleaware.org)

---

*Built by [@AlgonikHQ](https://x.com/AlgonikHQ) — the same system that runs automated trading bots, turned on football data.*
