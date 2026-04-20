# ============================================================
# scanner.py — edge detection with 6-layer scoring engine
# v1.3 — alert fires only if score >= MIN_SCORE_TO_ALERT
# ============================================================

import sqlite3
import json
import logging
from datetime import datetime
from config import DB_PATH, LOG_PATH, MAX_ALERTS_PER_DAY, MIN_SCORE_TO_ALERT

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [SCANNER] %(message)s")
log = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────
BTTS_THRESHOLD     = 0.65
BTTS_SPLIT_MIN     = 0.55
CS_THRESHOLD       = 0.55
OVER25_THRESHOLD   = 2.8
XG_OVER25_CONFIRM  = 2.5
XG_CS_MAX_AWAY     = 1.0
ODDS_MIN           = 1.70   # below this = already priced in, no edge
MIN_STRIKE_SAMPLE  = 10

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _form(team):
    conn = _db()
    row  = conn.execute("SELECT * FROM form WHERE team=?", (team,)).fetchone()
    conn.close()
    return dict(row) if row else None

def _standings(team):
    conn = _db()
    row  = conn.execute(
        "SELECT * FROM standings WHERE team=?", (team,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def _odds(fixture_id):
    conn = _db()
    row  = conn.execute(
        "SELECT * FROM odds WHERE fixture_id=?", (fixture_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

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

# ── Scoring engine ───────────────────────────────────────────

def score_btts(fixture_id, home, away):
    """
    Score a BTTS pick across 6 layers.
    Returns (score, max_score, layers_passed, reasoning) or None if base fails.
    """
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    h_btts = hf.get("btts_rate", 0)
    a_btts = af.get("btts_rate", 0)

    # Base gate — must pass to proceed
    if h_btts < BTTS_THRESHOLD or a_btts < BTTS_THRESHOLD:
        return None

    score   = 1  # base form passed
    layers  = [f"Form ✅ ({int(h_btts*100)}% / {int(a_btts*100)}%)"]
    reasons = [
        f"{home} BTTS in {int(h_btts*100)}% of last 8. "
        f"{away} BTTS in {int(a_btts*100)}% of last 8."
    ]

    # Layer 2 — home/away split
    h_home_btts = hf.get("btts_rate_home", h_btts)
    a_away_btts = af.get("btts_rate_away", a_btts)
    if h_home_btts >= BTTS_SPLIT_MIN and a_away_btts >= BTTS_SPLIT_MIN:
        score += 1
        layers.append(f"Split ✅ (H={int(h_home_btts*100)}% A={int(a_away_btts*100)}%)")
    else:
        layers.append(f"Split ❌")

    # Layer 3 — xG confirms both teams generating chances
    h_xg = hf.get("xg_for")
    a_xg = af.get("xg_for")
    if h_xg and a_xg and h_xg >= 1.0 and a_xg >= 1.0:
        score += 1
        layers.append(f"xG ✅ ({h_xg:.2f} / {a_xg:.2f})")
        reasons.append(f"xG for: {home} {h_xg:.2f}, {away} {a_xg:.2f}.")
    else:
        layers.append("xG ❌")

    # Layer 4 — H2H strike rate
    strike, sample = _h2h_strike_rate(home, away, "BTTS")
    if strike and strike >= 60:
        score += 1
        layers.append(f"H2H ✅ ({strike}% in {sample})")
        reasons.append(f"H2H BTTS rate: {strike}% ({sample} meetings).")
    else:
        layers.append("H2H ❌" if not strike else f"H2H ❌ ({strike}%)")

    # Layer 5 — standings (both teams in top half = more attacking)
    hs = _standings(home)
    as_ = _standings(away)
    if hs and as_:
        total_teams = 20  # default PL size
        if hs["position"] <= total_teams // 2 or as_["position"] <= total_teams // 2:
            score += 1
            layers.append(f"Standings ✅ (#{hs['position']} vs #{as_['position']})")
        else:
            layers.append(f"Standings ❌ (#{hs['position']} vs #{as_['position']})")
    else:
        layers.append("Standings —")

    # Layer 6 — odds gate
    odds = _odds(fixture_id)
    btts_odds = odds.get("btts_yes") if odds else None
    if btts_odds and btts_odds >= ODDS_MIN:
        score += 1
        layers.append(f"Odds ✅ ({btts_odds})")
        reasons.append(f"Market odds: {btts_odds} — edge confirmed.")
    elif btts_odds and btts_odds < ODDS_MIN:
        layers.append(f"Odds ❌ ({btts_odds} — already priced in)")
    else:
        layers.append("Odds —")

    return {
        "score":      score,
        "max_score":  6,
        "layers":     layers,
        "reasoning":  " ".join(reasons),
        "market":     "BTTS",
        "is_builder": False,
    }


def score_clean_sheet(fixture_id, home, away):
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    home_cs_h = hf.get("cs_rate_home", hf.get("cs_rate", 0))
    away_gf   = af.get("goals_for", 99)

    if home_cs_h < CS_THRESHOLD:
        return None
    if away_gf >= 1.0:
        return None

    score   = 1
    layers  = [f"Form ✅ (CS={int(home_cs_h*100)}%, Away GF={away_gf})"]
    reasons = [
        f"{home} kept {int(home_cs_h*100)}% clean sheets at home. "
        f"{away} averaging {away_gf} goals away."
    ]

    # Layer 2 — xG confirms away team not creating much
    away_xg = af.get("xg_for")
    if away_xg is not None and away_xg <= XG_CS_MAX_AWAY:
        score += 1
        layers.append(f"xG ✅ (Away xG={away_xg:.2f})")
        reasons.append(f"Away xG: {away_xg:.2f} — low threat confirmed.")
    else:
        layers.append(f"xG ❌" if away_xg is None else f"xG ❌ ({away_xg:.2f})")

    # Layer 3 — home/away split CS
    if home_cs_h >= CS_THRESHOLD:
        score += 1
        layers.append(f"Split ✅")
    else:
        layers.append("Split ❌")

    # Layer 4 — H2H
    strike, sample = _h2h_strike_rate(home, away, "CS_HOME")
    if strike and strike >= 50:
        score += 1
        layers.append(f"H2H ✅ ({strike}% in {sample})")
        reasons.append(f"H2H CS rate: {strike}% ({sample} meetings).")
    else:
        layers.append("H2H ❌" if not strike else f"H2H ❌ ({strike}%)")

    # Layer 5 — standings (home team higher = more dominant)
    hs  = _standings(home)
    as_ = _standings(away)
    if hs and as_ and hs["position"] < as_["position"]:
        score += 1
        layers.append(f"Standings ✅ (#{hs['position']} vs #{as_['position']})")
    else:
        pos_h = hs["position"] if hs else "?"
        pos_a = as_["position"] if as_ else "?"
        layers.append(f"Standings ❌ (#{pos_h} vs #{pos_a})")

    # Layer 6 — odds gate
    odds     = _odds(fixture_id)
    cs_odds  = odds.get("home_odds") if odds else None
    if cs_odds and cs_odds >= ODDS_MIN:
        score += 1
        layers.append(f"Odds ✅ ({cs_odds})")
    elif cs_odds:
        layers.append(f"Odds ❌ ({cs_odds})")
    else:
        layers.append("Odds —")

    return {
        "score":      score,
        "max_score":  6,
        "layers":     layers,
        "reasoning":  " ".join(reasons),
        "market":     "CS_HOME",
        "is_builder": True,
    }


def score_over25(fixture_id, home, away):
    hf = _form(home)
    af = _form(away)
    if not hf or not af:
        return None

    avg_goals = (
        hf.get("goals_for", 0) + hf.get("goals_ag", 0) +
        af.get("goals_for", 0) + af.get("goals_ag", 0)
    ) / 2

    if avg_goals < OVER25_THRESHOLD:
        return None

    score   = 1
    layers  = [f"Form ✅ (avg {round(avg_goals,1)} goals/g)"]
    reasons = [f"Combined avg goals/game: {round(avg_goals,1)}."]

    # Layer 2 — xG combined
    h_xg_for = hf.get("xg_for")
    h_xg_ag  = hf.get("xg_ag")
    a_xg_for = af.get("xg_for")
    a_xg_ag  = af.get("xg_ag")
    if all(v is not None for v in [h_xg_for, h_xg_ag, a_xg_for, a_xg_ag]):
        xg_combined = (h_xg_for + h_xg_ag + a_xg_for + a_xg_ag) / 2
        if xg_combined >= XG_OVER25_CONFIRM:
            score += 1
            layers.append(f"xG ✅ ({xg_combined:.2f}/g)")
            reasons.append(f"xG combined: {xg_combined:.2f}/g.")
        else:
            layers.append(f"xG ❌ ({xg_combined:.2f}/g)")
    else:
        layers.append("xG —")

    # Layer 3 — home/away split both high scoring
    h_gf_home = hf.get("goals_for", 0)
    a_gf_away = af.get("goals_for", 0)
    if h_gf_home >= 1.5 and a_gf_away >= 1.0:
        score += 1
        layers.append(f"Split ✅")
    else:
        layers.append("Split ❌")

    # Layer 4 — H2H
    strike, sample = _h2h_strike_rate(home, away, "OVER25")
    if strike and strike >= 60:
        score += 1
        layers.append(f"H2H ✅ ({strike}% in {sample})")
        reasons.append(f"H2H over 2.5: {strike}% ({sample} meetings).")
    else:
        layers.append("H2H ❌" if not strike else f"H2H ❌ ({strike}%)")

    # Layer 5 — standings (neither team in bottom 3 = not parking the bus)
    hs  = _standings(home)
    as_ = _standings(away)
    if hs and as_:
        total = 20
        if hs["position"] <= total - 3 and as_["position"] <= total - 3:
            score += 1
            layers.append(f"Standings ✅")
        else:
            layers.append(f"Standings ❌")
    else:
        layers.append("Standings —")

    # Layer 6 — odds gate
    odds      = _odds(fixture_id)
    o25_odds  = odds.get("over25") if odds else None
    if o25_odds and o25_odds >= ODDS_MIN:
        score += 1
        layers.append(f"Odds ✅ ({o25_odds})")
        reasons.append(f"Over 2.5 odds: {o25_odds}.")
    elif o25_odds:
        layers.append(f"Odds ❌ ({o25_odds} — priced in)")
    else:
        layers.append("Odds —")

    return {
        "score":      score,
        "max_score":  6,
        "layers":     layers,
        "reasoning":  " ".join(reasons),
        "market":     "OVER25",
        "is_builder": True,
    }

# ── Main scan ─────────────────────────────────────────────────

def scan_today(today_fixtures):
    from database import count_today_alerts
    already_sent = count_today_alerts()
    remaining    = MAX_ALERTS_PER_DAY - already_sent

    if remaining <= 0:
        log.info("Daily alert cap reached")
        return []

    candidates = []
    for fix in today_fixtures:
        fid  = fix["fixture_id"]
        home = fix["home"]
        away = fix["away"]

        for score_fn in [score_btts, score_clean_sheet, score_over25]:
            result = score_fn(fid, home, away)
            if not result:
                continue

            score = result["score"]
            log.info(
                f"{home} vs {away} [{result['market']}] — "
                f"score {score}/{result['max_score']} — "
                f"{' | '.join(result['layers'])}"
            )

            if score < MIN_SCORE_TO_ALERT:
                log.info(f"  → Below threshold ({score} < {MIN_SCORE_TO_ALERT}) — skipped")
                continue

            result["fixture_id"] = fid
            result["home"]       = home
            result["away"]       = away
            result["kickoff"]    = fix["kickoff_utc"]
            result["league"]     = fix.get("league", "PL")
            result["score_str"]  = f"{score}/{result['max_score']}"
            candidates.append(result)

    # Sort by score descending — strongest alerts first
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # De-dupe: one alert per fixture
    seen   = set()
    unique = []
    for c in candidates:
        if c["fixture_id"] not in seen:
            seen.add(c["fixture_id"])
            unique.append(c)

    selected = unique[:remaining]
    log.info(f"Scan: {len(candidates)} candidates scored, {len(selected)} selected (threshold={MIN_SCORE_TO_ALERT})")
    return selected
