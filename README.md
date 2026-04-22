# StatiqFC ⚽

Automated football edge detection across 8 European leagues. Paper staked in units. Full ROI tracked transparently. No hype, just data.

**Current version:** v2.1 (engine v1.6)
**Status:** Live — first edge fired 22 Apr 2026

---

## What it does

StatiqFC scans every upcoming fixture across its covered leagues, scores each one across a 6-layer statistical model, and posts clean subscriber-facing updates to a public Telegram channel. Every selection is tracked as a paper portfolio with unit-based stakes — no real money placed. Full ROI, win rate, and P&L are public from day one.

### 6-layer scoring model

A fixture must score **4 or more out of 6** before any pick is posted:

1. **Form** — rolling team performance over last 8 matches
2. **Home/Away split** — venue-specific performance patterns
3. **xG** — expected goals for and against (Understat, PL/BL1/SA/FL1/PD)
4. **H2H** — historical head-to-head strike rates (min 4 meetings)
5. **League standings** — positional context, league-size aware
6. **Market odds** — live odds gate via The Odds API (h2h + totals)

### Markets covered

- Both Teams to Score (BTTS) — Layer 6 uses competitive odds gate (home odds 1.40–3.50)
- Over 2.5 Goals — Layer 6 uses over2.5 market odds
- Home Clean Sheet — Layer 6 uses home win odds

---

## Leagues covered

| League | Country | Odds | Standings |
|---|---|---|---|
| Premier League | England | ✅ | ✅ |
| Championship | England | ✅ | ✅ |
| Bundesliga | Germany | ✅ | ✅ |
| Serie A | Italy | ✅ | ✅ |
| Ligue 1 | France | ✅ | ✅ |
| La Liga | Spain | ✅ | ✅ |
| Eredivisie | Netherlands | ✅ | ✅ |
| Primeira Liga | Portugal | ✅ | ✅ |

Champions League intentionally excluded — too much noise, inconsistent form context across group/knockout stages.

---

## The subscriber experience

Public Telegram channel delivers:

| Time | Message |
|---|---|
| 07:00 daily | Morning fixture card — all today's games grouped by league |
| T-2hrs pre-KO | Edge alert card with buttons if a pick scores 4+/6 |
| T-30 min pre-KO | Clean skip notice if no edge found for a fixture |
| Post-FT | FT result card — includes outcome if we had an edge |
| 22:30 daily | End-of-day summary — today's W/L/ROI + all-time running stats |
| Sunday 20:00 | Weekly digest |
| On target | VIP unlock announcement |

Everything else — restart notifications, error logs, verbose per-fixture scoring, near-misses — routed to a private channel. Subscribers see a clean, professional feed.

---

## Paper portfolio rules

| Pick type | Stake |
|---|---|
| Standard edge | **1u** |
| Builder single | **0.5u** |

**VIP threshold:** +20% ROI over 50 settled selections.

---

## Data sources

| Source | Used for |
|---|---|
| [football-data.co.uk](https://www.football-data.co.uk) | Historical results, form, H2H, upcoming fixtures |
| [football-data.org](https://www.football-data.org) | League standings (all 8 leagues, free tier) |
| [Understat](https://understat.com) | xG per team (scraped, top 5 leagues) |
| [The Odds API](https://the-odds-api.com) | Live odds — h2h + over/under markets (free tier) |

The bot holds **8,392 historical matches** seeding form and H2H computation from real data.

---

## Stack

- Python 3.12 on Ubuntu 24.04 (Hetzner VPS)
- SQLite local cache (`cache.db`)
- `schedule` library for job orchestration
- Telegram Bot API for delivery
- systemd service management
- GitHub for version control

---

## Scheduler

| Job | Frequency |
|---|---|
| Nightly cache refresh (fixtures, results, form, standings, xG) | 00:00 daily |
| Morning digest | 07:00 daily |
| Edge scan (with live odds + H2H pre-fetch) | Every 30 min |
| Public skip notices | Every 5 min |
| Result checker + FT poster | Every 30 min |
| End-of-day summary | 22:30 daily |
| Weekly digest | Sunday 20:00 |

---

## Project structure
statiq/
├── bot/
│   ├── config.py            # constants + credentials (gitignored)
│   ├── database.py          # SQLite schema + helpers
│   ├── fetcher.py           # data fetch layer — results, form, standings, odds
│   ├── fetcher_fbcouk.py    # football-data.co.uk CSV ingestion
│   ├── scanner.py           # 6-layer edge scoring engine
│   ├── telegram_cards.py    # message templates
│   ├── telegram.py          # Telegram send helpers
│   ├── statiq_bot.py        # main entry point + scheduler
│   └── requirements.txt
├── data/
│   └── cache.db             # SQLite store (gitignored)
└── README.md
---

## Transparency

- Every selection logged with reasoning, odds, stake, and settlement
- Daily P&L snapshots in `daily_pnl` table
- All-time ROI computed from settled selections only
- No historical editing — paper record is the record

---

## Disclaimer

StatiqFC is a statistical data service. It does not provide financial or betting advice. All displayed stakes are paper only — no real money is placed. 18+. Gamble responsibly. [BeGambleAware.org](https://www.begambleaware.org)

---

*Built by [@AlgonikHQ](https://x.com/AlgonikHQ) — same operator behind a live forex and crypto algo trading stack. FIRE@45 journey documented publicly.*
