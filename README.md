# StatiqFC ⚽

Automated football edge detection across 8 European leagues. Paper staked in units. Full ROI tracked transparently. No hype, just data.

**Current version:** v2.1
**Status:** Live

---

## What it does

StatiqFC scans every upcoming fixture across its covered leagues, scores each one across a 6-layer statistical model, and posts clean subscriber-facing updates to a public Telegram channel. Every selection is tracked as a paper portfolio with unit-based stakes — no real money placed. Full ROI, win rate, and P&L are public from day one.

### 6-layer scoring model

A fixture must score **4 or more out of 6** before any pick is posted:

1. **Form** — rolling team performance over last 8 matches
2. **Home/Away split** — venue-specific performance patterns
3. **xG** — expected goals for and against (Understat)
4. **H2H** — historical head-to-head strike rates
5. **League standings** — positional context
6. **Market odds** — value gate against closing prices

### Markets covered

- Both Teams to Score (BTTS)
- Over 2.5 Goals
- Home Clean Sheet

---

## Leagues covered

| League | Country |
|---|---|
| Premier League | England |
| Championship | England |
| Bundesliga | Germany |
| Serie A | Italy |
| Ligue 1 | France |
| La Liga | Spain |
| Eredivisie | Netherlands |
| Primeira Liga | Portugal |

Champions League is intentionally excluded — the CSV data source does not cover it, and falling back to a rate-limited API introduced too much fragility.

---

## The subscriber experience

Public Telegram channel delivers (and only delivers):

| Time | Message |
|---|---|
| 07:00 daily | Morning fixture card — all today's games grouped by league |
| T-30 min pre-KO | Clean skip notice if no edge found for a fixture |
| Anytime | Edge alert card with buttons if a pick scores 4+/6 |
| Post-FT | FT result card — includes "Our pick: W/L" if we had an edge |
| 21:00 daily | End-of-day summary — today's W/L/ROI + all-time running stats |
| Sunday 20:00 | Weekly digest |
| On target | VIP unlock announcement |

Everything else — restart notifications, error logs, verbose per-fixture scoring, near-misses — is routed to a private channel. Subscribers see a clean, professional feed.

---

## Paper portfolio rules

| Pick type | Stake |
|---|---|
| Standard edge | **1u** |
| Builder single | **0.5u** |

Unit-based stakes are the professional tipster convention. Subscribers scale to their own bankroll when the VIP tier opens.

**VIP threshold:** +20% ROI over 50 settled selections. That target is pinned publicly from day one.

---

## Data sources (all free, no API keys required for primary)

| Source | Used for |
|---|---|
| [football-data.co.uk](https://www.football-data.co.uk) | **Primary** — historical results, form, H2H, upcoming fixtures, closing odds |
| [Understat](https://understat.com) | xG per team (scraped) |
| [API-Football](https://www.api-football.com) | League standings (free tier) |

The bot currently holds **8,392 historical matches across 3 seasons** from football-data.co.uk — seeding form and H2H computation entirely from real data, not rate-limited API calls.

---

## Stack

- Python 3.12 on Ubuntu 24.04 (Hetzner VPS)
- SQLite local cache (`cache.db`)
- `schedule` library for job orchestration
- Telegram Bot API for delivery
- systemd for service management
- GitHub Pages for public ROI dashboard

---

## Scheduler

Seven scheduled jobs run continuously:

| Job | Frequency |
|---|---|
| Nightly cache refresh | Once daily |
| Morning digest post | 07:00 |
| Edge scan | Every 30 min |
| Public skip notices | Every 5 min |
| Result checker + FT poster | Every 30 min |
| End-of-day summary | 21:00 |
| Weekly digest | Sunday 20:00 |

---

## Project structure

```
statiq/
├── bot/
│   ├── config.py            # constants + credentials (gitignored)
│   ├── database.py          # SQLite schema + helpers
│   ├── fetcher.py           # legacy fetch layer (rewired to results table)
│   ├── fetcher_fbcouk.py    # football-data.co.uk CSV ingestion
│   ├── scanner.py           # 6-layer edge scoring
│   ├── telegram_cards.py    # message templates
│   ├── telegram.py          # Telegram send helpers
│   ├── statiq_bot.py        # main entry point + scheduler
│   └── requirements.txt
├── data/
│   └── cache.db             # SQLite store (results, fixtures, form, H2H, P&L)
└── README.md
```


---

## Transparency

- Every selection is logged with reasoning, odds, stake, and settlement
- Daily P&L snapshots stored in the `daily_pnl` table
- All-time ROI computed from settled selections
- No historical editing — paper record is the record

---

## Disclaimer

StatiqFC is a statistical data service. It does not provide financial or betting advice. All displayed stakes are paper only — no real money is placed. 18+. Gamble responsibly. [BeGambleAware.org](https://www.begambleaware.org)

---

*Built by [@AlgonikHQ](https://x.com/AlgonikHQ) — same operator behind a live forex and crypto algo trading stack.*
