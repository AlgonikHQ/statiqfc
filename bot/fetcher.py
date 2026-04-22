# ============================================================
# fetcher.py — all external data pulls with graceful fallback
# v1.2 — league-aware odds, proactive bulk odds fetch, btts removed
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

# ── League → Odds API sport key map ─────────────────────────
LEAGUE_ODDS_SPORT = {
    "PL":  "soccer_epl",
    "ELC": "soccer_efl_champ",
    "FL1": "soccer_france_ligue_one",
    "FL2": "soccer_france_ligue_two",
    "PD":  "soccer_spain_la_liga",
    "BL1": "soccer_germany_bundesliga",
    "SA":  "soccer_italy_serie_a",
    "DED": "soccer_netherlands_eredivisie",
    "PPL": "soccer_portugal_primeira_liga",
    "CL":  "soccer_uefa_champs_league",
}

# ── Understat team name mapping ──────────────────────────────
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

# ── Odds API team name normalisation ────────────────────────
# Odds API names → fixture DB names
ODDS_TEAM_MAP = {
    "Wolverhampton Wanderers": "Wolverhampton",
    "Elche CF":                "Elche",
    "Paris Saint Germain":     "Paris Saint-Germain",
    "Brighton and Hove Albion":"Brighton & Hove Albion",
    "Nottingham Forest":       "Nott'm Forest",
    "Manchester United":       "Man Utd",
    "Manchester City":         "Manchester City",
    "Tottenham Hotspur":       "Spurs",
    "West Ham United":         "West Ham",
    "Newcastle United":        "Newcastle",
}

def _normalise_odds_team(name):
    return ODDS_TEAM_MAP.get(name, name)

def _teams_match(odds_home, odds_away, db_home, db_away):
    """Fuzzy match between odds API team names and fixture DB names."""
    oh = _normalise_odds_team(odds_home).lower()
    oa = _normalise_odds_team(odds_away).lower()
    dh = db_home.lower()
    da = db_away.lower()
    # Direct match or one side contained in the other
    home_match = oh == dh or dh in oh or oh in dh
    away_match = oa == da or da in oa or oa in da
    return home_match and away_match

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
    try:
        from fetcher_fbcouk import fetch_upcoming_fixtures
    except ImportError:
        from bot.fetcher_fbcouk import fetch_upcoming_fixtures
    inserted, skipped = fetch_upcoming_fixtures()
    log.info(f"Fixtures refresh: {inserted} fixtures cached across configured leagues ({skipped} non-target rows skipped)")
    return inserted


def fetch_results(days_back=3):
    log.info("Pulling results via football-data.co.uk CSVs")
    inserted, _ = fetch_all_leagues_current_season()
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



# football-data.org full name → DB short name
FD_NAME_MAP = {
    "AFC Bournemouth":           "Bournemouth",
    "AFC Wimbledon":             "Wimbledon",
    "Albacete Balompié":         "Albacete",
    "Athletic Club":             "Athletic Club",
    "Club Atlético de Madrid":   "Atlético Madrid",
    "Birmingham City FC":        "Birmingham",
    "Blackburn Rovers FC":       "Blackburn",
    "Blackpool FC":              "Blackpool",
    "Bolton Wanderers FC":       "Bolton",
    "Brentford FC":              "Brentford",
    "Brighton & Hove Albion FC": "Brighton",
    "Bristol City FC":           "Bristol City",
    "Burnley FC":                "Burnley",
    "Cardiff City FC":           "Cardiff",
    "Charlton Athletic FC":      "Charlton",
    "Chelsea FC":                "Chelsea",
    "Coventry City FC":          "Coventry",
    "Crystal Palace FC":         "Crystal Palace",
    "Derby County FC":           "Derby",
    "Everton FC":                "Everton",
    "FC Nantes":                 "Nantes",
    "FC Barcelona":              "Barcelona",
    "Fulham FC":                 "Fulham",
    "Getafe CF":                 "Getafe",
    "Huddersfield Town AFC":     "Huddersfield",
    "Hull City AFC":             "Hull",
    "Ipswich Town FC":           "Ipswich",
    "Leeds United FC":           "Leeds United",
    "Leicester City FC":         "Leicester",
    "Luton Town FC":             "Luton",
    "Manchester City FC":        "Manchester City",
    "Manchester United FC":      "Manchester United",
    "Middlesbrough FC":          "Middlesbrough",
    "Millwall FC":               "Millwall",
    "Newcastle United FC":       "Newcastle",
    "Norwich City FC":           "Norwich",
    "Nottingham Forest FC":      "Nottingham Forest",
    "Oxford United FC":          "Oxford",
    "Paris Saint-Germain FC":    "Paris Saint-Germain",
    "Plymouth Argyle FC":        "Plymouth",
    "Portsmouth FC":             "Portsmouth",
    "Preston North End FC":      "Preston",
    "Queens Park Rangers FC":    "QPR",
    "Real Sociedad de Fútbol":   "Real Sociedad",
    "Rotherham United FC":       "Rotherham",
    "Sheffield United FC":       "Sheffield United",
    "Sheffield Wednesday FC":    "Sheffield Wednesday",
    "Southampton FC":            "Southampton",
    "Stoke City FC":             "Stoke",
    "Sunderland AFC":            "Sunderland",
    "Swansea City AFC":          "Swansea",
    "Telstar 1963":              "Telstar",
    "Tottenham Hotspur FC":      "Tottenham",
    "Watford FC":                "Watford",
    "West Bromwich Albion FC":   "West Brom",
    "West Ham United FC":        "West Ham",
    "Wigan Athletic FC":         "Wigan",
    "Wolverhampton Wanderers FC":"Wolves",
}

def fetch_live_results_today():
    """
    Fetch today's finished results from football-data.org live API.
    Called from run_result_checker every 30 min.
    Updates fixtures to FINISHED and writes to results table.
    Returns count of fixtures updated.
    """
    from difflib import get_close_matches
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            FD_BASE_URL + "/matches",
            headers={"X-Auth-Token": FD_API_KEY},
            params={"status": "FINISHED", "date": today},
            timeout=15
        )
        r.raise_for_status()
        matches = r.json().get("matches", [])
    except Exception as e:
        log.warning(f"fetch_live_results_today error: {e}")
        return 0

    if not matches:
        return 0

    conn = _db()
    updated = 0
    for m in matches:
        comp_code = m.get("competition", {}).get("code", "")
        api_home  = m.get("homeTeam", {}).get("name", "")
        api_away  = m.get("awayTeam", {}).get("name", "")
        api_home  = FD_NAME_MAP.get(api_home, api_home)
        api_away  = FD_NAME_MAP.get(api_away, api_away)
        ft        = m.get("score", {}).get("fullTime", {})
        hg        = ft.get("home")
        ag        = ft.get("away")
        if hg is None or ag is None:
            continue

        # Find candidates in fixtures table for this league+date
        candidates = conn.execute("""
            SELECT fixture_id, home, away FROM fixtures
            WHERE league=? AND substr(kickoff_utc,1,10)=?
        """, (comp_code, today)).fetchall()

        if not candidates:
            continue

        matched = None
        for c in candidates:
            hm = get_close_matches(api_home, [c["home"]], n=1, cutoff=0.5)
            am = get_close_matches(api_away, [c["away"]], n=1, cutoff=0.5)
            if hm and am:
                matched = c
                break

        if not matched:
            log.warning(f"No DB match: {api_home} vs {api_away} [{comp_code}]")
            continue

        fid      = matched["fixture_id"]
        db_home  = matched["home"]
        db_away  = matched["away"]

        conn.execute("""
            UPDATE fixtures SET status='FINISHED', home_score=?, away_score=?, updated_at=?
            WHERE fixture_id=? AND status IN ('SCHEDULED','TIMED','IN_PLAY')
        """, (hg, ag, datetime.utcnow().isoformat(), fid))

        match_id = f"{today}_{db_home}_{db_away}".replace(" ", "_")
        conn.execute("""
            INSERT OR REPLACE INTO results (match_id, league, season, date, home, away, fthg, ftag)
            VALUES (?,?,?,?,?,?,?,?)
        """, (match_id, comp_code, "2025-26", today, db_home, db_away, hg, ag))

        updated += 1
        log.info(f"Live result: {db_home} {hg}-{ag} {db_away} [{comp_code}]")

    conn.commit()
    conn.close()
    return updated

def fetch_team_form(team_id, team_name):
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

# ── Understat xG scraper ─────────────────────────────────────

def fetch_xg_understat(team_name, last_n=5):
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
        match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.*?)'\)", html)
        if not match:
            log.warning(f"Understat: datesData not found for {team_name}")
            return None, None

        raw     = match.group(1).encode("utf-8").decode("unicode_escape")
        matches = json.loads(raw)
        finished = [m for m in matches if m.get("isResult")]
        recent   = finished[-last_n:] if len(finished) >= last_n else finished

        if not recent:
            log.info(f"Understat: no finished matches for {team_name}")
            return None, None

        xg_for_list, xg_ag_list = [], []
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
        time.sleep(2)
    log.info(f"xG refresh complete: {updated}/{len(teams)} teams updated")

# ── Odds ─────────────────────────────────────────────────────

def fetch_odds(fixture_id, home, away, league="PL"):
    """Pull h2h + over2.5 odds for a single fixture and store in DB."""
    if not ODDS_API_KEY or ODDS_API_KEY.strip() in ("", "YOUR_ODDS_API_KEY"):
        log.info("Odds API key not set — skipping odds fetch")
        return None

    sport = LEAGUE_ODDS_SPORT.get(league, "soccer_epl")
    result = {}

    for market_key in ["h2h", "totals"]:
        data = _get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
            params={
                "apiKey":     ODDS_API_KEY,
                "regions":    ODDS_REGION,
                "markets":    market_key,
                "oddsFormat": "decimal"
            },
            label=f"odds-{market_key}-{home}v{away}"
        )
        if not data:
            continue

        for game in data:
            if not _teams_match(game.get("home_team",""), game.get("away_team",""), home, away):
                continue
            for bm in game.get("bookmakers", [])[:1]:
                for mkt in bm.get("markets", []):
                    if mkt["key"] == "h2h":
                        oc = {o["name"]: o["price"] for o in mkt["outcomes"]}
                        result["home_odds"] = oc.get(game["home_team"])
                        result["draw_odds"] = oc.get("Draw")
                        result["away_odds"] = oc.get(game["away_team"])
                    elif mkt["key"] == "totals":
                        for o in mkt["outcomes"]:
                            if "over" in o["name"].lower():
                                result["over25"] = o["price"]
            break
        time.sleep(0.3)

    if result:
        conn = _db()
        conn.execute("""
            INSERT OR REPLACE INTO odds
            (fixture_id, home_odds, draw_odds, away_odds, btts_yes, over25, pulled_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            fixture_id,
            result.get("home_odds"), result.get("draw_odds"), result.get("away_odds"),
            None,  # btts not available on free tier
            result.get("over25"),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        log.info(f"Odds stored [{league}] {home} vs {away}: {result}")

    return result if result else None


def fetch_odds_for_today():
    """Proactively fetch and store odds for all of today's scheduled fixtures."""
    conn = _db()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    fixtures = conn.execute("""
        SELECT fixture_id, home, away, league FROM fixtures
        WHERE date(kickoff_utc)=? AND status IN ('SCHEDULED','TIMED')
    """, (today,)).fetchall()
    conn.close()

    total, ok, fail = len(fixtures), 0, 0
    log.info(f"Proactive odds fetch: {total} fixtures today")
    for fix in fixtures:
        try:
            r = fetch_odds(fix["fixture_id"], fix["home"], fix["away"], fix["league"])
            if r:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            log.warning(f"Odds fetch error {fix['home']} vs {fix['away']}: {e}")
            fail += 1
        time.sleep(0.5)
    log.info(f"Odds fetch complete: {ok} stored, {fail} failed")
    return ok, fail

# ── Nightly cache rebuild ─────────────────────────────────────

def refresh_all_team_forms():
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
    fetch_standings()
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

# ── Standings ─────────────────────────────────────────────────

def fetch_standings():
    """Pull current standings for all configured leagues from football-data.org."""
    from config import LEAGUE_CODES, FD_API_KEY, FD_BASE_URL
    headers = {"X-Auth-Token": FD_API_KEY}
    conn = _db()
    total = 0

    for league in LEAGUE_CODES:
        url  = f"{FD_BASE_URL}/competitions/{league}/standings"
        data = _get(url, headers=headers, label=f"standings-{league}")
        if not data:
            log.warning(f"Standings fetch failed for {league}")
            continue

        try:
            table = data["standings"][0]["table"]
        except (KeyError, IndexError) as e:
            log.warning(f"Standings parse error for {league}: {e}")
            continue

        for entry in table:
            raw_name = entry["team"]["name"]
            team = raw_name
            for suffix in [" FC", " AFC", " CF", " SC", " AC", " AS", " SD", " UD", " RC"]:
                if team.endswith(suffix):
                    team = team[:-len(suffix)].strip()
                    break
            conn.execute("""
                INSERT OR REPLACE INTO standings
                (team, league, position, played, won, drawn, lost,
                 goals_for, goals_ag, points, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                team, league,
                entry["position"],
                entry["playedGames"],
                entry["won"],
                entry["draw"],
                entry["lost"],
                entry["goalsFor"],
                entry["goalsAgainst"],
                entry["points"],
                datetime.utcnow().isoformat()
            ))
            total += 1

        conn.commit()
        log.info(f"Standings fetched: {league} ({len(table)} teams)")
        time.sleep(1)  # football-data.org free tier: 10 req/min

    conn.close()
    log.info(f"Standings refresh complete: {total} rows written")
    return total
