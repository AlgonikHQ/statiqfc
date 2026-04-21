# ============================================================
# scanner.py — edge detection across upcoming fixtures
# v1.1 — home/away split + xG confirmation layer
# ============================================================

import sqlite3
import json
import logging
from datetime import datetime
from config import DB_PATH, LOG_PATH, MAX_ALERTS_PER_DAY

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [SCANNER] %(message)s")
log = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────
BTTS_THRESHOLD      = 0.65   # combined BTTS rate >= this
BTTS_SPLIT_MIN      = 0.55   # home/away specific rate must also be >= this
CS_THRESHOLD        = 0.55   # clean sheet rate >= this
OVER25_THRESHOLD    = 2.8    # combined avg goals >= this
XG_OVER25_CONFIRM   = 2.5    # xG combined >= this confirms over 2.5
XG_CS_MAX_AWAY      = 1.0    # away xG for must be <= this to confirm CS pick
MIN_STRIKE_SAMPLE   = 10     # min H2H meetings to quote a strike rate

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _form(team):
    conn = _db()
    row  = conn.execute("SELECT * FROM form WHERE team=?", (team,)).fetchone()
    conn.close()
    return dict(row) if row else None

def _h2h_stats(home, away):
    conn  = _db()
    rows  = conn.execute(
        "SELECT * FROM h2h WHERE (home=? AND away=?) OR (home=? AND away=?) ORDER BY date DESC LIMIT 8",
        (home, away, away, home)
    ).fetchall()
    conn.close()
    if not rows:
        return None
    btts  = sum(1 for r in rows if r["home_score"] > 0 and r["away_score"] > 0)
    goals = [r["home_score"] + r["away_score"] for r in rows]
    return {
        "matches":   len(rows),
        "btts_rate": round(btts / len(rows), 2),
        "avg_goals": round(sum(goals) / len(goals), 2)
    }

def _h2h_strike_rate(home, away, market):
    conn  = _db()
    rows  = conn.execute(
        "SELECT * FROM h2h WHERE (home=? AND away=?) OR (home=? AND away=?) ORDER BY date DESC LIMIT 8",
        (home, away, away, home)
    ).fetchall()
    conn.close()
    if len(rows) < MIN_STRIKE_SAMPLE:
        return None, len(rows)
    if market == "BTTS":
        hits = sum(1 for r in rows if r["home_score"] > 0 and r["away_score"] > 0)
    elif market == "OVER25":
        hits = sum(1 for r in rows if (r["home_score"] + r["away_score"]) > 2)
    elif market == "CS_HOME":
        hits = sum(1 for r in rows if r["away_score"] == 0)
    else:
        return None, len(rows)
    return round(hits / len(rows) * 100, 1), len(rows)

# ── xG helpers ───────────────────────────────────────────────

def _xg_note(form, label):
    """Return a short xG context string if data is available."""
    if not form:
        return ""
    xg_for = form.get("xg_for")
    xg_ag  = form.get("xg_ag")
    if xg_for is None or xg_ag is None:
        return ""
    return f" ({label} xG: {xg_for:.2f}f / {xg_ag:.2f}a)"

# ── Individual checks ────────────────────────────────────────

def check_btts(fixture_id, home, away):
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    h_btts = hf.get("btts_rate", 0)
    a_btts = af.get("btts_rate", 0)

    # Primary gate: both combined rates above main threshold
    if h_btts < BTTS_THRESHOLD or a_btts < BTTS_THRESHOLD:
        return None

    # Secondary gate: home/away specific rates (fall back to combined if not stored)
    h_home_btts = hf.get("btts_rate_home", h_btts)
    a_away_btts = af.get("btts_rate_away", a_btts)
    if h_home_btts < BTTS_SPLIT_MIN or a_away_btts < BTTS_SPLIT_MIN:
        log.info(f"BTTS split filter: {home} home={h_home_btts:.0%} {away} away={a_away_btts:.0%} — skipped")
        return None

    strike, sample = _h2h_strike_rate(home, away, "BTTS")
    h_xg = _xg_note(hf, home)
    a_xg = _xg_note(af, away)

    return {
        "market":     "BTTS",
        "is_builder": False,
        "reasoning": (
            f"{home} BTTS in {int(h_btts*100)}% of last 8{h_xg}. "
            f"{away} BTTS in {int(a_btts*100)}% of last 8{a_xg}."
            + (f" H2H strike rate: {strike}% ({sample} meetings)." if strike else "")
        )
    }

def check_clean_sheet(fixture_id, home, away):
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    home_cs   = hf.get("cs_rate", 0)
    # Use home-specific CS rate if available, else fall back to combined
    home_cs_h = hf.get("cs_rate_home", home_cs)
    away_gf   = af.get("goals_for", 99)

    if home_cs_h < CS_THRESHOLD:
        return None
    if away_gf >= 1.0:
        return None

    # xG confirmation: away xG for also low
    away_xg_for = af.get("xg_for")
    xg_confirmed = away_xg_for is not None and away_xg_for <= XG_CS_MAX_AWAY

    strike, sample = _h2h_strike_rate(home, away, "CS_HOME")
    xg_note = f" Away xG: {away_xg_for:.2f}/g — xG confirms." if xg_confirmed else (
        f" Away xG: {away_xg_for:.2f}/g — slight xG concern." if away_xg_for and away_xg_for > XG_CS_MAX_AWAY else ""
    )

    return {
        "market":     "CS_HOME",
        "is_builder": True,
        "reasoning": (
            f"{home} kept {int(home_cs_h*100)}% clean sheets at home (last 8). "
            f"{away} averaging {away_gf} goals away last 8.{xg_note}"
            + (f" H2H CS rate: {strike}% ({sample} meetings)." if strike else "")
        )
    }

def check_over25(fixture_id, home, away):
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    avg_goals_combined = (
        hf.get("goals_for", 0) + hf.get("goals_ag", 0) +
        af.get("goals_for", 0) + af.get("goals_ag", 0)
    ) / 2

    if avg_goals_combined < OVER25_THRESHOLD:
        return None

    # xG confirmation layer
    h_xg_for = hf.get("xg_for")
    h_xg_ag  = hf.get("xg_ag")
    a_xg_for = af.get("xg_for")
    a_xg_ag  = af.get("xg_ag")

    xg_note = ""
    if all(v is not None for v in [h_xg_for, h_xg_ag, a_xg_for, a_xg_ag]):
        xg_combined = (h_xg_for + h_xg_ag + a_xg_for + a_xg_ag) / 2
        if xg_combined >= XG_OVER25_CONFIRM:
            xg_note = f" xG combined: {xg_combined:.2f}/g — confirmed by xG."
        else:
            xg_note = f" xG combined: {xg_combined:.2f}/g — xG slightly below goals avg."

    strike, sample = _h2h_strike_rate(home, away, "OVER25")

    return {
        "market":     "OVER25",
        "is_builder": True,
        "reasoning": (
            f"Combined avg goals/game: {round(avg_goals_combined,1)}.{xg_note}"
            + (f" H2H over 2.5 rate: {strike}% ({sample} meetings)." if strike else "")
        )
    }

# ── Main scan ─────────────────────────────────────────────────

def scan_today(today_fixtures):
    from database import count_today_alerts
    already_sent = count_today_alerts()
    remaining    = MAX_ALERTS_PER_DAY - already_sent

    if remaining <= 0:
        log.info("Daily alert cap reached — no new alerts")
        return []

    candidates = []
    for fix in today_fixtures:
        fid  = fix["fixture_id"]
        home = fix["home"]
        away = fix["away"]

        for check_fn in [check_btts, check_clean_sheet, check_over25]:
            result = check_fn(fid, home, away)
            if result:
                result["fixture_id"] = fid
                result["home"]       = home
                result["away"]       = away
                result["kickoff"]    = fix["kickoff_utc"]
                candidates.append(result)

    # de-dupe: one alert per fixture max
    seen   = set()
    unique = []
    for c in candidates:
        if c["fixture_id"] not in seen:
            seen.add(c["fixture_id"])
            unique.append(c)

    selected = unique[:remaining]
    log.info(f"Scan complete: {len(candidates)} candidates, {len(selected)} selected")
    return selected
