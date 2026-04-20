# StatiqFC

Automated football edge detection bot for the Premier League.

## What it does
- Scans upcoming PL fixtures for statistical edges (BTTS, Clean Sheet, Over 2.5)
- Pulls team form, H2H data, xG (Understat), and optional odds confirmation
- Posts alerts to a public Telegram channel 2 hours before kick-off
- Tracks paper P&L and ROI over time

## Stack
- Python 3 + SQLite
- football-data.org API (free tier)
- Understat xG scraper (free, no key)
- The Odds API (optional, free tier)
- Runs as `statiqfc.service` on Ubuntu 24.04

## Data sources
| Source | Data | Cost |
|--------|------|------|
| football-data.org | Fixtures, results, form | Free |
| Understat | xG for/against | Free (scrape) |
| The Odds API | Market odds snapshot | Free (500 calls/month) |

## Bot version
See `bot/config.py` → `BOT_VERSION`
