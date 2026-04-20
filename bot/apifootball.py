# ============================================================
# apifootball.py — API-Football data layer
# 100 free requests/day — used only in nightly refresh
# Provides: standings, team stats, referee data, injuries
# ============================================================

import requests
import sqlite3
import json
import time
import logging
from datetime import datetime
from config import API_FOOTBALL_KEY, API_FOOTBALL_URL, DB_PATH, LOG_PATH, LEAGUE_CODES

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [APIFB] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY
}

# Map our league codes to API-Football league IDs
LEAGUE_ID_MAP = {
    "PL":  39,    # Premier League
    "BL1": 78,    # Bundesliga
    "SA":  135,   # Serie A
    "FL1": 61,    # Ligue 1
    "PD":  140,   # La Liga
    "CL":  2,     # Champions League
    "EC":  4,     # Euros
    "WC":  1,     # World Cup
}

CURRENT_SEASON = 2024  # update each season

def _get(endpoint, params=None):
    """Single API-Football GET with rate limit awareness."""
    url = f"{API_FOOTBALL_URL}/{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        remaining = r.headers.get("x-ratelimit-requests-remaining", "?")
        log.info(f"API-Football [{endpoint}] — {remaining} requests remaining today")
        return data.get("response", [])
    except Exception as e:
        log.warning(f"API-Football error [{endpoint}]: {e}")
        return []

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Standings ────────────────────────────────────────────────

def fetch_standings_all():
    """Fetch league table positions for all leagues. ~8 requests."""
    conn = _db()
    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            team        TEXT,
            league      TEXT,
            position    INTEGER,
            played      INTEGER,
            won         INTEGER,
            drawn       INTEGER,
            lost        INTEGER,
            goals_for   INTEGER,
            goals_ag    INTEGER,
            points      INTEGER,
            updated_at  TEXT,
            PRIMARY KEY (team, league)
        )
    """)
    conn.commit()

    for league_code in LEAGUE_CODES:
        league_id = LEAGUE_ID_MAP.get(league_code)
        if not league_id:
            continue
        # Skip tournament-only competitions that have no standing table
        if league_code in ("EC", "WC"):
            continue

        data = _get("standings", {"league": league_id, "season": CURRENT_SEASON})
        if not data:
            time.sleep(1)
            continue

        try:
            standings = data[0]["league"]["standings"][0]
            for team in standings:
                conn.execute("""
                    INSERT OR REPLACE INTO standings
                    (team, league, position, played, won, drawn, lost,
                     goals_for, goals_ag, points, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    team["team"]["name"],
                    league_code,
                    team["rank"],
                    team["all"]["played"],
                    team["all"]["win"],
                    team["all"]["draw"],
                    team["all"]["lose"],
                    team["all"]["goals"]["for"],
                    team["all"]["goals"]["against"],
                    team["points"],
                    datetime.utcnow().isoformat()
                ))
            conn.commit()
            log.info(f"Standings cached [{league_code}]: {len(standings)} teams")
        except Exception as e:
            log.warning(f"Standings parse error [{league_code}]: {e}")

        time.sleep(1.5)  # stay well within rate limit

    conn.close()

# ── Team statistics ──────────────────────────────────────────

def fetch_team_stats(team_name, league_code):
    """
    Fetch team stats from API-Football: shots, corners, possession.
    Returns dict or None. Costs 1 request.
    """
    league_id = LEAGUE_ID_MAP.get(league_code)
    if not league_id:
        return None

    # We need the API-Football team ID — look it up from standings table
    conn = _db()
    row = conn.execute(
        "SELECT apifb_team_id FROM team_ids WHERE team=? AND league=?",
        (team_name, league_code)
    ).fetchone()
    conn.close()

    if not row:
        return None

    team_id = row["apifb_team_id"]
    data = _get("teams/statistics", {
        "team":   team_id,
        "league": league_id,
        "season": CURRENT_SEASON
    })

    if not data:
        return None

    try:
        stats = data[0]
        shots_on_avg = None
        corners_avg  = None

        # shots on target per game
        shots_on = stats.get("shots", {}).get("on", {})
        played   = stats.get("fixtures", {}).get("played", {}).get("total", 0)
        if shots_on.get("total") and played:
            shots_on_avg = round(shots_on["total"] / played, 2)

        return {
            "shots_on_avg": shots_on_avg,
            "corners_avg":  corners_avg,
        }
    except Exception as e:
        log.warning(f"Team stats parse error [{team_name}]: {e}")
        return None

# ── Referee data ─────────────────────────────────────────────

def fetch_fixture_referee(fixture_id_apifb):
    """
    Get referee name for a fixture. Then look up referee stats.
    Costs 1 request per fixture.
    Returns dict: {name, yellow_avg, red_avg, foul_avg} or None.
    """
    data = _get("fixtures", {"id": fixture_id_apifb})
    if not data:
        return None
    try:
        referee_name = data[0]["fixture"].get("referee")
        if not referee_name:
            return None
        return {"name": referee_name}
    except Exception as e:
        log.warning(f"Referee fetch error: {e}")
        return None

# ── Injuries ─────────────────────────────────────────────────

def fetch_injuries(league_code, fixture_id_apifb):
    """
    Check for injuries/suspensions for a fixture.
    Returns list of injured/suspended players or [].
    Costs 1 request.
    """
    league_id = LEAGUE_ID_MAP.get(league_code)
    if not league_id:
        return []

    data = _get("injuries", {"fixture": fixture_id_apifb})
    if not data:
        return []

    key_players = []
    for p in data:
        player = p.get("player", {})
        reason = p.get("type", "")
        key_players.append({
            "name":   player.get("name"),
            "team":   p.get("team", {}).get("name"),
            "reason": reason
        })
    return key_players

# ── Team ID mapping (one-time fetch per league) ───────────────

def build_team_id_map():
    """
    Fetch team list for each league and store name→API-Football ID mapping.
    Run once to populate team_ids table. Costs 1 request per league.
    """
    conn = _db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_ids (
            team         TEXT,
            league       TEXT,
            apifb_team_id INTEGER,
            PRIMARY KEY (team, league)
        )
    """)
    conn.commit()

    for league_code in LEAGUE_CODES:
        if league_code in ("EC", "WC"):
            continue
        league_id = LEAGUE_ID_MAP.get(league_code)
        if not league_id:
            continue

        data = _get("teams", {"league": league_id, "season": CURRENT_SEASON})
        if not data:
            time.sleep(1)
            continue

        for entry in data:
            team = entry.get("team", {})
            conn.execute("""
                INSERT OR REPLACE INTO team_ids (team, league, apifb_team_id)
                VALUES (?,?,?)
            """, (team.get("name"), league_code, team.get("id")))

        conn.commit()
        log.info(f"Team IDs cached [{league_code}]: {len(data)} teams")
        time.sleep(1.5)

    conn.close()
    log.info("Team ID map build complete")

# ── Nightly refresh entry point ───────────────────────────────

def nightly_apifootball_refresh():
    """Called from fetcher.nightly_refresh(). Uses ~8-10 requests."""
    log.info("API-Football nightly refresh started")
    fetch_standings_all()
    log.info("API-Football nightly refresh complete")
