"""
fetcher_fbcouk.py — football-data.co.uk CSV ingestion

Free, no key, no rate limit. Powers results, form, H2H, and odds layers.

URL: https://www.football-data.co.uk/mmz4281/{SEASON}/{LEAGUE_CODE}.csv
SEASON: e.g. "2526" for 2025-26
LEAGUE_CODE: E0 (PL), E1 (Champ), D1 (Bundesliga), I1 (Serie A),
             F1 (Ligue 1), SP1 (La Liga), N1 (Eredivisie), P1 (Primeira)
"""

import csv
import io
import sqlite3
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("FBCOUK")

DB_PATH = "/root/statiq/data/cache.db"
BASE_URL = "https://www.football-data.co.uk/mmz4281"

# League code mapping: our internal code -> football-data.co.uk code
FBCOUK_LEAGUES = {
    "PL":   "E0",
    "ELC":  "E1",
    "BL1":  "D1",
    "SA":   "I1",
    "FL1":  "F1",
    "PD":   "SP1",
    "DED":  "N1",
    "PPL":  "P1",
}

# Team name normalization: football-data.co.uk uses different names than API-Football
# Add aliases here as you spot mismatches; bot will warn on unmatched teams.
TEAM_ALIASES = {
    "Man United":    "Manchester United",
    "Man City":      "Manchester City",
    "Nott'm Forest": "Nottingham Forest",
    "Sheffield Weds":"Sheffield Wednesday",
    "QPR":           "Queens Park Rangers",
    "Wolves":        "Wolverhampton Wanderers",
    "Leeds":         "Leeds United",
    "Newcastle":     "Newcastle United",
    "West Ham":      "West Ham United",
    "West Brom":     "West Bromwich Albion",
    "Brighton":      "Brighton & Hove Albion",
    "Spurs":         "Tottenham Hotspur",
    "Tottenham":     "Tottenham Hotspur",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "Bayern Munich": "Bayern München",
    "M'gladbach":    "Borussia Mönchengladbach",
    "Dortmund":      "Borussia Dortmund",
    "Leverkusen":    "Bayer Leverkusen",
    "Inter":         "Inter Milan",
    "AC Milan":      "Milan",
    "Paris SG":      "Paris Saint-Germain",
    "St Etienne":    "Saint-Étienne",
    "Ath Madrid":    "Atlético Madrid",
    "Ath Bilbao":    "Athletic Bilbao",
    "Sociedad":      "Real Sociedad",
    "Betis":         "Real Betis",
    "Celta":         "Celta Vigo",
    "Espanol":       "Espanyol",
    "PSV Eindhoven": "PSV",
    "Ajax":          "Ajax Amsterdam",
    "Sp Lisbon":     "Sporting CP",
    "FC Porto":      "Porto",
}


def _norm_team(name):
    """Normalize team name using alias table; fallback to original."""
    if not name:
        return name
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def _parse_date(date_str):
    """football-data.co.uk uses DD/MM/YY or DD/MM/YYYY format."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _safe_int(v):
    try:
        return int(float(v)) if v not in (None, "", "NA") else None
    except (ValueError, TypeError):
        return None


def _safe_float(v):
    try:
        return float(v) if v not in (None, "", "NA") else None
    except (ValueError, TypeError):
        return None


def _season_code(season_start_year):
    """2025 -> '2526', 2024 -> '2425' (football-data.co.uk format)."""
    return f"{season_start_year % 100:02d}{(season_start_year + 1) % 100:02d}"


def _make_match_id(league, season, date, home, away):
    """Stable match ID for primary key dedup."""
    return f"{league}_{season}_{date}_{home}_{away}".replace(" ", "_")


def fetch_league_season(internal_league, season_start_year):
    """
    Download one season of one league. Returns (rows_inserted, rows_skipped).
    """
    fbcouk_code = FBCOUK_LEAGUES.get(internal_league)
    if not fbcouk_code:
        log.warning(f"No fbcouk code for league {internal_league}")
        return 0, 0

    season = _season_code(season_start_year)
    url = f"{BASE_URL}/{season}/{fbcouk_code}.csv"

    log.info(f"Fetching {internal_league} season {season} from {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Fetch failed [{internal_league}/{season}]: {e}")
        return 0, 0

    # CSV may have BOM, encoding quirks
    content = r.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    inserted, skipped = 0, 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for row in reader:
        date = _parse_date(row.get("Date"))
        home = _norm_team(row.get("HomeTeam"))
        away = _norm_team(row.get("AwayTeam"))

        if not (date and home and away):
            skipped += 1
            continue

        fthg = _safe_int(row.get("FTHG"))
        ftag = _safe_int(row.get("FTAG"))

        # Skip unplayed games (no score yet)
        if fthg is None or ftag is None:
            skipped += 1
            continue

        match_id = _make_match_id(internal_league, season, date, home, away)

        # Derive helper flags
        btts    = 1 if (fthg > 0 and ftag > 0) else 0
        over_25 = 1 if (fthg + ftag) > 2 else 0
        home_cs = 1 if ftag == 0 else 0
        away_cs = 1 if fthg == 0 else 0

        try:
            cur.execute("""
                INSERT OR REPLACE INTO results (
                    match_id, league, season, date, home, away,
                    fthg, ftag, ftr, hthg, htag,
                    hs, as_, hst, ast, hc, ac, hy, ay, hr, ar,
                    b365h, b365d, b365a, psh, psd, psa,
                    avg_over_25, avg_under_25,
                    btts, over_25, home_cs, away_cs, ingested_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?, ?
                )
            """, (
                match_id, internal_league, season, date, home, away,
                fthg, ftag, row.get("FTR"),
                _safe_int(row.get("HTHG")), _safe_int(row.get("HTAG")),
                _safe_int(row.get("HS")), _safe_int(row.get("AS")),
                _safe_int(row.get("HST")), _safe_int(row.get("AST")),
                _safe_int(row.get("HC")), _safe_int(row.get("AC")),
                _safe_int(row.get("HY")), _safe_int(row.get("AY")),
                _safe_int(row.get("HR")), _safe_int(row.get("AR")),
                _safe_float(row.get("B365H")), _safe_float(row.get("B365D")), _safe_float(row.get("B365A")),
                _safe_float(row.get("PSH")), _safe_float(row.get("PSD")), _safe_float(row.get("PSA")),
                _safe_float(row.get("Avg>2.5")), _safe_float(row.get("Avg<2.5")),
                btts, over_25, home_cs, away_cs, now
            ))
            inserted += 1
        except Exception as e:
            log.warning(f"Insert failed [{match_id}]: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    log.info(f"[{internal_league}/{season}] inserted={inserted} skipped={skipped}")
    return inserted, skipped


def fetch_all_leagues_current_season():
    """Daily refresh — pull current season for all leagues."""
    # Determine current season start year (Aug = new season)
    now = datetime.now(timezone.utc)
    season_start = now.year if now.month >= 8 else now.year - 1

    total_inserted, total_skipped = 0, 0
    for league in FBCOUK_LEAGUES.keys():
        ins, skp = fetch_league_season(league, season_start)
        total_inserted += ins
        total_skipped  += skp
    log.info(f"Daily refresh complete: {total_inserted} inserted, {total_skipped} skipped across {len(FBCOUK_LEAGUES)} leagues")
    return total_inserted, total_skipped


def backfill_history(years=3):
    """One-off: pull last N seasons for all leagues."""
    now = datetime.now(timezone.utc)
    current_start = now.year if now.month >= 8 else now.year - 1
    seasons = [current_start - i for i in range(years)]

    total_inserted, total_skipped = 0, 0
    for season_start in seasons:
        for league in FBCOUK_LEAGUES.keys():
            ins, skp = fetch_league_season(league, season_start)
            total_inserted += ins
            total_skipped  += skp
    log.info(f"Backfill complete ({years} seasons): {total_inserted} inserted, {total_skipped} skipped")
    return total_inserted, total_skipped




# ── Upcoming fixtures from fixtures.csv ──────────────────────

FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"


def _make_fixture_id(league, date, home, away):
    """Stable fixture ID for primary key dedup."""
    return f"FX_{league}_{date}_{home}_{away}".replace(" ", "_")


def _combine_kickoff(date_iso, time_str):
    """Combine 'YYYY-MM-DD' + 'HH:MM' (UK local time from fbcouk) into ISO UTC.
    fbcouk times are UK local (BST/GMT). Convert to true UTC before storage."""
    if not date_iso:
        return None
    if not time_str or time_str.strip() == "":
        time_str = "12:00"
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        local = datetime.fromisoformat(f"{date_iso}T{time_str.strip()}:00").replace(tzinfo=ZoneInfo("Europe/London"))
        utc   = local.astimezone(ZoneInfo("UTC"))
        return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Fallback: naive UK-local -> UTC via fixed +1h during BST (April)
        return f"{date_iso}T{time_str.strip()}:00Z"


def fetch_upcoming_fixtures():
    """Pull upcoming fixtures from football-data.co.uk fixtures.csv (filtered to our 8 leagues)."""
    log.info(f"Fetching upcoming fixtures from {FIXTURES_URL}")
    try:
        r = requests.get(FIXTURES_URL, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Fixtures fetch failed: {e}")
        return 0, 0

    content = r.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    # Reverse map: fbcouk code -> internal league code
    fbcouk_to_internal = {v: k for k, v in FBCOUK_LEAGUES.items()}

    inserted, skipped = 0, 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for row in reader:
        div = row.get("Div", "").strip()
        internal = fbcouk_to_internal.get(div)
        if not internal:
            skipped += 1
            continue

        date = _parse_date(row.get("Date"))
        if not date:
            skipped += 1
            continue

        home = _norm_team(row.get("HomeTeam"))
        away = _norm_team(row.get("AwayTeam"))
        if not (home and away):
            skipped += 1
            continue

        kickoff = _combine_kickoff(date, row.get("Time", ""))
        fixture_id = _make_fixture_id(internal, date, home, away)

        try:
            cur.execute("""
                INSERT OR REPLACE INTO fixtures (
                    fixture_id, home, away, kickoff_utc, league,
                    status, home_score, away_score, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'SCHEDULED', NULL, NULL, ?)
            """, (fixture_id, home, away, kickoff, internal, now))
            inserted += 1
        except Exception as e:
            log.warning(f"Fixture insert failed [{fixture_id}]: {e}")
            skipped += 1

        # Also store closing odds in odds table if it exists
        b365h = _safe_float(row.get("B365H"))
        b365d = _safe_float(row.get("B365D"))
        b365a = _safe_float(row.get("B365A"))
        avg_over = _safe_float(row.get("Avg>2.5"))
        avg_under = _safe_float(row.get("Avg<2.5"))
        if b365h or avg_over:
            try:
                cur.execute("""
                    INSERT OR REPLACE INTO odds
                    (fixture_id, home_win, draw, away_win, btts_yes, over_25, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (fixture_id, b365h, b365d, b365a, None, avg_over, now))
            except Exception:
                pass  # odds table may not exist yet; non-critical

    conn.commit()
    conn.close()
    log.info(f"Upcoming fixtures: {inserted} inserted, {skipped} skipped (non-target leagues)")
    return inserted, skipped

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s"
    )
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fixtures":
        fetch_upcoming_fixtures()
    elif len(sys.argv) > 1 and sys.argv[1] == "backfill":
        years = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        backfill_history(years)
    else:
        fetch_all_leagues_current_season()
