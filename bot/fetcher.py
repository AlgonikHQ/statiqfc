# ============================================================
# fetcher.py — all external data pulls with graceful fallback
# v1.1 — Understat xG scraper + extended odds markets
# ============================================================

import requests
try:
    from fetcher_fbcouk import fetch_all_leagues_current_season
except ImportError:
    from bot.fetcher_fbcouk import fetch_all_leagues_current_season
import sqlite3
import json
import re
import time
import logging
from datetime import datetime, timedelta
from config import FD_API_KEY, FD_BASE_URL, LEAGUE_CODE, LEAGUE_CODES, ODDS_API_KEY, ODDS_SPORT, ODDS_REGION, ODDS_MARKET, DB_PATH, LOG_PATH

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [FETCHER] %(message)s")
log = logging.getLogger(__name__)

FD_HEADERS = {"X-Auth-Token": FD_API_KEY}

# ── Understat team name mapping ──────────────────────────────
# football-data.org short names → Understat slugs
UNDERSTAT_SLUGS = {
    "Arsenal":          "Arsenal",
    "Aston Villa":      "Aston_Villa",
    "Bournemouth":      "Bournemouth",
    "Brentford":        "Brentford",
    "Brighton":         "Brighton",
    "Chelsea":          "Chelsea",
    "Crystal Palace":   "Crystal_Palace",
    "Everton":          "Everton",
    "Fulham":           "Fulham",
    "Ipswich":          "Ipswich",
    "Leicester":        "Leicester",
    "Liverpool":        "Liverpool",
    "Man City":         "Manchester_City",
    "Man Utd":          "Manchester_United",
    "Newcastle":        "Newcastle_United",
    "Nott'm Forest":   "Nottingham_Forest",
    "Southampton":      "Southampton",
    "Spurs":            "Tottenham",
    "West Ham":         "West_Ham",
    "Wolves":           "Wolverhampton_Wanderers",
}

# ── Helpers ──────────────────────────────────────────────────

def _get(url, headers=None, params=None, label=""):
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"Fetch failed [{label}]: {e}")
        return None

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Fixtures & Results ───────────────────────────────────────

def fetch_fixtures(days_ahead=7):
    """Pull upcoming fixtures via football-data.co.uk fixtures.csv (covers all 8 leagues, no rate limit)."""
    try:
        from fetcher_fbcouk import fetch_upcoming_fixtures
    except ImportError:
        from bot.fetcher_fbcouk import fetch_upcoming_fixtures
    inserted, skipped = fetch_upcoming_fixtures()
    log.info(f"Fixtures refresh: {inserted} fixtures cached across configured leagues ({skipped} non-target rows skipped)")
    return inserted


def fetch_results(days_back=3):
    """Pull recent results via football-data.co.uk CSV + sync FINISHED status into fixtures table."""
    log.info("Pulling results via football-data.co.uk CSVs")
    inserted, _ = fetch_all_leagues_current_season()
    # Sync any matching scheduled fixtures to FINISHED
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE fixtures
        SET status='FINISHED',
            home_score=(SELECT fthg FROM results r WHERE r.home=fixtures.home AND r.away=fixtures.away AND r.date=substr(fixtures.kickoff_utc,1,10) LIMIT 1),
            away_score=(SELECT ftag FROM results r WHERE r.home=fixtures.home AND r.away=fixtures.away AND r.date=substr(fixtures.kickoff_utc,1,10) LIMIT 1),
            updated_at=?
        WHERE status IN ('SCHEDULED','TIMED','IN_PLAY')
        AND EXISTS (
            SELECT 1 FROM results r
            WHERE r.home=fixtures.home AND r.away=fixtures.away AND r.date=substr(fixtures.kickoff_utc,1,10)
        )
    """, (datetime.utcnow().isoformat(),))
    synced = cur.rowcount
    conn.commit()
    conn.close()
    log.info(f"Results sync: {inserted} CSV rows ingested, {synced} fixtures marked FINISHED")
    return inserted

def fetch_team_form(team_id, team_name):
    """Compute team form from the results table (last 8 matches)."""
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, home, away, fthg, ftag
        FROM results
        WHERE home=? OR away=?
        ORDER BY date DESC
        LIMIT 8
    """, (team_name, team_name))
    rows = cur.fetchall()
    if not rows:
        conn.close()
        return

    last5_wdl, gf_list, ga_list, cs_list, btts_list = [], [], [], [], []
    home_cs_list, home_btts_list, away_cs_list, away_btts_list = [], [], [], []

    for row in rows:
        date, home, away, fthg, ftag = row["date"], row["home"], row["away"], row["fthg"], row["ftag"]
        if fthg is None or ftag is None:
            continue
        is_home = (home == team_name)
        gf = fthg if is_home else ftag
        ga = ftag if is_home else fthg
        gf_list.append(gf)
        ga_list.append(ga)
        cs_list.append(1 if ga == 0 else 0)
        btts_list.append(1 if fthg > 0 and ftag > 0 else 0)
        if is_home:
            home_cs_list.append(1 if ga == 0 else 0)
            home_btts_list.append(1 if fthg > 0 and ftag > 0 else 0)
        else:
            away_cs_list.append(1 if ga == 0 else 0)
            away_btts_list.append(1 if fthg > 0 and ftag > 0 else 0)
        if len(last5_wdl) < 5:
            if gf > ga:    last5_wdl.append("W")
            elif gf == ga: last5_wdl.append("D")
            else:          last5_wdl.append("L")

    cs_rate_home   = round(sum(home_cs_list)/len(home_cs_list), 2)   if home_cs_list  else None
    btts_rate_home = round(sum(home_btts_list)/len(home_btts_list), 2) if home_btts_list else None
    cs_rate_away   = round(sum(away_cs_list)/len(away_cs_list), 2)   if away_cs_list  else None
    btts_rate_away = round(sum(away_btts_list)/len(away_btts_list), 2) if away_btts_list else None

    conn.execute("""
        INSERT OR REPLACE INTO form
        (team, last5, goals_for, goals_ag, cs_rate, btts_rate,
         cs_rate_home, btts_rate_home, cs_rate_away, btts_rate_away,
         updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        team_name,
        json.dumps(last5_wdl),
        round(sum(gf_list)/len(gf_list), 2) if gf_list else 0,
        round(sum(ga_list)/len(ga_list), 2) if ga_list else 0,
        round(sum(cs_list)/len(cs_list), 2) if cs_list else 0,
        round(sum(btts_list)/len(btts_list), 2) if btts_list else 0,
        cs_rate_home, btts_rate_home, cs_rate_away, btts_rate_away,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

# ── H2H ──────────────────────────────────────────────────────

def fetch_h2h(fixture_id):
    """Pull last 6 H2H meetings from the results table."""
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT home, away FROM fixtures WHERE fixture_id=?", (fixture_id,))
    fix = cur.fetchone()
    if not fix:
        conn.close()
        return []
    home_team, away_team = fix["home"], fix["away"]
    cur.execute("""
        SELECT date, home, away, fthg AS home_score, ftag AS away_score
        FROM results
        WHERE (home=? AND away=?) OR (home=? AND away=?)
        ORDER BY date DESC
        LIMIT 6
    """, (home_team, away_team, away_team, home_team))
    rows = cur.fetchall()
    h2h_rows = []
    for row in rows:
        # Sync into legacy h2h table for any consumers that still read it
        conn.execute("""
            INSERT OR IGNORE INTO h2h
            (fixture_id, home, away, date, home_score, away_score)
            VALUES (?,?,?,?,?,?)
        """, (fixture_id, row["home"], row["away"], row["date"], row["home_score"], row["away_score"]))
        h2h_rows.append({
            "home": row["home"], "away": row["away"],
            "home_score": row["home_score"], "away_score": row["away_score"],
            "date": row["date"]
        })
    conn.commit()
    conn.close()
    return h2h_rows

# ── Understat xG scraper (free, no key needed) ───────────────

def fetch_xg_understat(team_name, last_n=5):
    """
    Scrape xG data for a team from Understat.
    Returns (xg_for_avg, xg_ag_avg) over last_n matches, or (None, None) on failure.
    No API key required — public HTML scrape.
    """
    slug = UNDERSTAT_SLUGS.get(team_name)
    if not slug:
        log.info(f"Understat: no slug mapping for {team_name!r} — skipping xG")
        return None, None

    url = f"https://understat.com/team/{slug}/2024"
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 (StatiqFC bot)"})
        if resp.status_code != 200:
            log.warning(f"Understat HTTP {resp.status_code} for {team_name}")
            return None, None

        html = resp.text

        # Understat embeds match data as JSON inside a JS var
        # Pattern: var datesData = JSON.parse('...')
        match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.*?)'\)", html)
        if not match:
            log.warning(f"Understat: datesData not found for {team_name}")
            return None, None

        # Unescape the JSON string
        raw = match.group(1).encode("utf-8").decode("unicode_escape")
        matches = json.loads(raw)

        # Filter finished matches only, take last N
        finished = [m for m in matches if m.get("isResult")]
        recent   = finished[-last_n:] if len(finished) >= last_n else finished

        if not recent:
            log.info(f"Understat: no finished matches for {team_name}")
            return None, None

        xg_for_list = []
        xg_ag_list  = []
        for m in recent:
            is_home = m.get("side") == "h"
            h_xg    = float(m.get("xG", {}).get("h", 0) or 0)
            a_xg    = float(m.get("xG", {}).get("a", 0) or 0)
            xg_for_list.append(h_xg if is_home else a_xg)
            xg_ag_list.append(a_xg  if is_home else h_xg)

        xg_for = round(sum(xg_for_list) / len(xg_for_list), 2)
        xg_ag  = round(sum(xg_ag_list)  / len(xg_ag_list),  2)
        log.info(f"Understat xG {team_name}: xGf={xg_for} xGa={xg_ag} (last {len(recent)} games)")
        return xg_for, xg_ag

    except Exception as e:
        log.warning(f"Understat scrape error for {team_name}: {e}")
        return None, None


def refresh_xg_all_teams():
    """
    Update xg_for / xg_ag in form table for every team we have form data on.
    Called during nightly_refresh. Rate-limited to be polite to Understat.
    """
    conn  = _db()
    teams = [row["team"] for row in conn.execute("SELECT team FROM form").fetchall()]
    conn.close()

    updated = 0
    for team in teams:
        xg_for, xg_ag = fetch_xg_understat(team)
        if xg_for is None:
            continue
        conn = _db()
        conn.execute(
            "UPDATE form SET xg_for=?, xg_ag=?, updated_at=? WHERE team=?",
            (xg_for, xg_ag, datetime.utcnow().isoformat(), team)
        )
        conn.commit()
        conn.close()
        updated += 1
        time.sleep(2)   # polite delay — Understat is free, don't hammer it

    log.info(f"xG refresh complete: {updated}/{len(teams)} teams updated")

# ── Odds ─────────────────────────────────────────────────────

def fetch_odds(fixture_id, home, away):
    """Pull H2H + BTTS + Over2.5 odds snapshot at alert time."""
    if not ODDS_API_KEY or ODDS_API_KEY.strip() in ("", "YOUR_ODDS_API_KEY"):
        log.info("Odds API key not set — skipping odds fetch")
        return None

    result = {}

    # H2H market
    data_h2h = _get(
        f"https://api.the-odds-api.com/v4/sports/{ODDS_SPORT}/odds",
        params={
            "apiKey":      ODDS_API_KEY,
            "regions":     ODDS_REGION,
            "markets":     "h2h",
            "oddsFormat":  "decimal"
        },
        label=f"odds-h2h-{home}v{away}"
    )
    if data_h2h:
        for game in data_h2h:
            if (home.lower() in game.get("home_team","").lower() or
                    away.lower() in game.get("away_team","").lower()):
                for bm in game.get("bookmakers", [])[:1]:
                    for mkt in bm.get("markets", []):
                        if mkt["key"] == "h2h":
                            oc = {o["name"]: o["price"] for o in mkt["outcomes"]}
                            result["home"] = oc.get(game["home_team"])
                            result["draw"] = oc.get("Draw")
                            result["away"] = oc.get(game["away_team"])
                break

    # BTTS + Over/Under 2.5 markets
    for market_key, result_key in [("btts", "btts_yes"), ("totals", "over25")]:
        data_mkt = _get(
            f"https://api.the-odds-api.com/v4/sports/{ODDS_SPORT}/odds",
            params={
                "apiKey":     ODDS_API_KEY,
                "regions":    ODDS_REGION,
                "markets":    market_key,
                "oddsFormat": "decimal"
            },
            label=f"odds-{market_key}-{home}v{away}"
        )
        if not data_mkt:
            continue
        for game in data_mkt:
            if (home.lower() in game.get("home_team","").lower() or
                    away.lower() in game.get("away_team","").lower()):
                for bm in game.get("bookmakers", [])[:1]:
                    for mkt in bm.get("markets", []):
                        if mkt["key"] == market_key:
                            for outcome in mkt["outcomes"]:
                                name = outcome["name"].lower()
                                if result_key == "btts_yes" and "yes" in name:
                                    result["btts_yes"] = outcome["price"]
                                elif result_key == "over25" and "over" in name:
                                    result["over25"] = outcome["price"]
                break
        time.sleep(0.5)  # stay within free tier rate limit

    if result:
        conn = _db()
        conn.execute("""
            INSERT OR REPLACE INTO odds
            (fixture_id, home_odds, draw_odds, away_odds, btts_yes, over25, pulled_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            fixture_id,
            result.get("home"), result.get("draw"), result.get("away"),
            result.get("btts_yes"), result.get("over25"),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        log.info(f"Odds stored for {fixture_id}: {result}")

    return result if result else None

# ── Nightly cache rebuild ─────────────────────────────────────

def refresh_all_team_forms():
    """Compute form for every team that appears in the results table."""
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT team FROM (
            SELECT home AS team FROM results
            UNION
            SELECT away AS team FROM results
        )
    """)
    teams = [row["team"] for row in cur.fetchall()]
    conn.close()
    log.info(f"Computing form for {len(teams)} teams")
    ok, fail = 0, 0
    for team in teams:
        try:
            fetch_team_form(None, team)
            ok += 1
        except Exception as e:
            log.warning(f"Form failed for {team}: {e}")
            fail += 1
    log.info(f"Form refresh complete: {ok} ok, {fail} failed")
    return ok, fail


def nightly_refresh():
    log.info("Nightly cache refresh started")
    fetch_fixtures(days_ahead=7)
    fetch_results(days_back=3)
    refresh_all_team_forms()
    refresh_xg_all_teams()
    try:
        from apifootball import nightly_apifootball_refresh
        nightly_apifootball_refresh()
    except Exception as e:
        log.warning(f"API-Football refresh error: {e}")
    log.info("Nightly cache refresh complete")
