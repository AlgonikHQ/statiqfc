#!/usr/bin/env python3
# ============================================================
# statiq_bot.py — main entry point
# v1.4 — per-fixture skip cards, private dashboard, end-of-day
# ============================================================

import schedule
import time
import json
import logging
import sqlite3
import traceback
from datetime import datetime, timezone, timedelta

from config import (DIGEST_TIME, CACHE_REFRESH_TIME, PRE_MATCH_HOURS,
                    RESULT_CHECK_MINUTES, VIP_ROI_TARGET, VIP_MIN_SELECTIONS,
                    BOT_VERSION, PATCH_NOTES, LOG_PATH, DB_PATH,
                    STAKE_BUILDER, STAKE_STANDARD, LEAGUE_CODES, MIN_SCORE_TO_ALERT)
from database  import (init_db, log_selection, settle_selection,
                       get_pending_selections, get_latest_roi, refresh_roi,
                       export_roi_json, count_today_alerts)
from fetcher   import nightly_refresh, fetch_fixtures, fetch_results, fetch_h2h, fetch_odds
from scanner   import scan_today, score_btts, score_clean_sheet, score_over25
from telegram_cards import (
    buttons_edge_alert, buttons_result, buttons_digest, buttons_weekly, buttons_vip,
    card_daily_digest, card_edge_alert, card_result, card_no_alerts_today,
    card_weekly_digest, card_vip_unlock, card_fixture_skip,
    card_private_startup, card_private_morning_briefing, card_private_alert_detail,
    card_private_near_misses, card_private_nightly_report, card_private_roi_summary,
    card_private_error
)
from telegram import send_public, send_private, send_public_buttons

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [MAIN] %(message)s")
log = logging.getLogger(__name__)

_vip_announced    = False
_fixtures_scanned = 0
_near_misses      = []
_top_score        = 0
_leagues_scanned  = set()
_skip_sent        = set()
_last_reset_date  = None


def _daily_reset():
    global _fixtures_scanned, _near_misses, _top_score, _leagues_scanned, _skip_sent, _last_reset_date
    today = datetime.now(timezone.utc).date()
    if _last_reset_date != today:
        _fixtures_scanned = 0
        _near_misses      = []
        _top_score        = 0
        _leagues_scanned  = set()
        _skip_sent        = set()
        _last_reset_date  = today


def _ko_time_safe(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone(__import__("zoneinfo").ZoneInfo("Europe/London")).strftime("%H:%M BST")
    except Exception:
        return utc_str


# ── Startup ───────────────────────────────────────────────────

def startup():
    init_db()
    try:
        nightly_refresh()
    except Exception as e:
        send_private(card_private_error("startup/nightly_refresh", e))

    send_private(card_private_startup(BOT_VERSION, PATCH_NOTES, LEAGUE_CODES))
    send_public(
        "\U0001f504 *StatiqFC " + BOT_VERSION + " \u2014 Online*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\u2705 All systems operational\n"
        "\U0001f4e6 Version: " + BOT_VERSION + "\n"
        "\U0001f4cb " + PATCH_NOTES + "\n"
        "\U0001f550 " + datetime.now(__import__("zoneinfo").ZoneInfo("Europe/London")).strftime("%d %b %Y, %H:%M BST") + "\n\n"
        "Alerts resume as scheduled."
    )
    log.info("Bot started — " + BOT_VERSION)


# ── Daily digest ──────────────────────────────────────────────

def run_daily_digest():
    if _last_reset_date == datetime.utcnow().date() and _fixtures_scanned > 0:
        return
    _daily_reset()
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        conn  = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows  = conn.execute(
            "SELECT * FROM fixtures WHERE kickoff_utc LIKE ? AND status IN ('SCHEDULED','TIMED') ORDER BY league, kickoff_utc",
            (today + "%",)
        ).fetchall()
        conn.close()
        fixtures = [dict(r) for r in rows]
        if fixtures:
            send_public_buttons(card_daily_digest(fixtures), buttons_digest())
            send_private(card_private_morning_briefing(fixtures, BOT_VERSION))
        log.info("Daily digest: " + str(len(fixtures)) + " fixtures")
    except Exception as e:
        send_private(card_private_error("run_daily_digest", e))


# ── Edge scan ─────────────────────────────────────────────────

def run_edge_scan():
    global _fixtures_scanned, _near_misses, _top_score, _leagues_scanned, _skip_sent
    _daily_reset()
    try:
        now    = datetime.now(timezone.utc)
        window = now + timedelta(hours=PRE_MATCH_HOURS + 0.5)
        conn   = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows   = conn.execute(
            "SELECT * FROM fixtures WHERE status IN ('SCHEDULED','TIMED') ORDER BY kickoff_utc"
        ).fetchall()
        conn.close()

        upcoming = []
        for r in rows:
            try:
                ko = datetime.fromisoformat(r["kickoff_utc"].replace("Z", "+00:00"))
                if now < ko <= window:
                    upcoming.append(dict(r))
            except Exception:
                continue

        if not upcoming:
            return

        edges = scan_today(upcoming)

        for fix in upcoming:
            fid  = fix["fixture_id"]
            home = fix["home"]
            away = fix["away"]
            _fixtures_scanned += 1
            _leagues_scanned.add(fix.get("league", "PL"))

            fix_has_alert = any(e["fixture_id"] == fid for e in edges)
            if fix_has_alert:
                continue

            best_score  = 0
            best_result = None
            for score_fn in [score_btts, score_clean_sheet, score_over25]:
                result = score_fn(fid, home, away)
                if result and result["score"] > best_score:
                    best_score  = result["score"]
                    best_result = result

            if best_result:
                if best_result["score"] > _top_score:
                    _top_score = best_result["score"]
                if best_result["score"] == MIN_SCORE_TO_ALERT - 1:
                    nm = {
                        "fixture_id": fid,
                        "home":       home,
                        "away":       away,
                        "market":     best_result["market"],
                        "score":      best_result["score"],
                        "layers":     best_result.get("layers", []),
                        "league":     fix.get("league", "PL"),
                    }
                    if not any(n["fixture_id"] == fid for n in _near_misses):
                        _near_misses.append(nm)

                if fid not in _skip_sent:
                    _skip_sent.add(fid)
                    remaining = [f for f in upcoming if f["fixture_id"] != fid]
                    next_ko   = _ko_time_safe(remaining[0]["kickoff_utc"]) if remaining else None
                    send_public(card_fixture_skip(
                        home, away,
                        fix.get("league", "PL"),
                        fix["kickoff_utc"],
                        best_result["score"],
                        best_result["max_score"],
                        next_ko
                    ))

        for edge in edges:
            h2h_rows = fetch_h2h(edge["fixture_id"])
            odds     = fetch_odds(edge["fixture_id"], edge["home"], edge["away"])

            odds_val = None
            if odds:
                odds_val = {"BTTS": odds.get("btts_yes"),
                            "OVER25": odds.get("over25"),
                            "CS_HOME": odds.get("home")}.get(edge["market"])

            display_odds = odds_val if odds_val else 1.80
            stake        = STAKE_BUILDER if edge.get("is_builder") else STAKE_STANDARD
            potential    = round(stake * display_odds, 2)
            edge.update({"odds": display_odds, "stake": stake, "potential": potential})

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            fh = conn.execute("SELECT * FROM form WHERE team=?", (edge["home"],)).fetchone()
            fa = conn.execute("SELECT * FROM form WHERE team=?", (edge["away"],)).fetchone()
            conn.close()

            def _to_form_dict(row):
                if not row:
                    return None
                d = dict(row)
                d["last5_list"] = json.loads(d.get("last5", "[]"))
                return d

            log_selection(edge["fixture_id"], edge["home"], edge["away"],
                          edge["market"], display_odds,
                          edge.get("is_builder", False), edge.get("reasoning", ""))

            msg = card_edge_alert(edge, _to_form_dict(fh), _to_form_dict(fa),
                                  h2h_rows, odds, BOT_VERSION)
            send_public_buttons(msg, buttons_edge_alert(edge["home"], edge["away"]))
            send_private(card_private_alert_detail(edge, BOT_VERSION))
            log.info("Alert: " + edge["home"] + " vs " + edge["away"] + " [" + edge["market"] + "] score " + str(edge.get("score_str")))

    except Exception as e:
        send_private(card_private_error("run_edge_scan", e))
        log.error(traceback.format_exc())


# ── End of day (21:00 UTC) ────────────────────────────────────

def run_end_of_day():
    global _near_misses, _fixtures_scanned, _top_score, _leagues_scanned
    _daily_reset()
    try:
        alerts_today = count_today_alerts()
        if alerts_today == 0 and _fixtures_scanned > 0:
            send_public_buttons(card_no_alerts_today(_fixtures_scanned, _top_score, _leagues_scanned), buttons_digest())
        if _near_misses:
            msg = card_private_near_misses(_near_misses, BOT_VERSION)
            if msg:
                send_private(msg)
        roi = get_latest_roi()
        send_private(card_private_roi_summary(roi, label="Daily ROI Summary"))
        log.info("End of day: " + str(alerts_today) + " alerts, " + str(len(_near_misses)) + " near-misses, " + str(_fixtures_scanned) + " scanned")
    except Exception as e:
        send_private(card_private_error("run_end_of_day", e))


# ── Result checker ────────────────────────────────────────────

def run_result_checker():
    global _vip_announced
    try:
        finished     = fetch_results(days_back=1)
        pending      = get_pending_selections()
        if not pending:
            return
        finished_ids = {f["fixture_id"]: f for f in finished}
        for sel in pending:
            fid = sel["fixture_id"]
            if fid not in finished_ids:
                continue
            rd     = finished_ids[fid]
            hs     = rd["home_score"]
            as_    = rd["away_score"]
            market = sel["market"]
            if market == "BTTS":
                result = "WIN" if hs > 0 and as_ > 0 else "LOSS"
            elif market == "CS_HOME":
                result = "WIN" if as_ == 0 else "LOSS"
            elif market == "OVER25":
                result = "WIN" if (hs + as_) > 2 else "LOSS"
            else:
                result = "VOID"
            settle_selection(sel["id"], result, hs, as_)
            roi    = get_latest_roi()
            export_roi_json()
            profit = round(sel["stake"] * sel["odds"] - sel["stake"], 2) if result == "WIN" else (-sel["stake"] if result == "LOSS" else 0)
            sel_dict           = dict(sel)
            sel_dict["result"] = result
            sel_dict["profit"] = profit
            send_public_buttons(card_result(sel_dict, roi), buttons_result())
            send_private(card_private_roi_summary(roi, label="ROI updated"))
            log.info("Settled: " + sel["home"] + " vs " + sel["away"] + " [" + market + "] -> " + result)
            if (not _vip_announced and roi and
                    roi["selections"] >= VIP_MIN_SELECTIONS and
                    roi["roi_pct"] >= VIP_ROI_TARGET):
                send_public_buttons(card_vip_unlock(roi), buttons_vip())
                send_private("\U0001f3c6 *VIP threshold hit!*\nROI: " + str(roi["roi_pct"]) + "% over " + str(roi["selections"]) + " selections.")
                _vip_announced = True
    except Exception as e:
        send_private(card_private_error("run_result_checker", e))
        log.error(traceback.format_exc())


# ── Nightly refresh ───────────────────────────────────────────

def run_nightly_refresh():
    sources = {"football-data.org": False, "Understat": False, "API-Football": False}
    try:
        nightly_refresh()
        sources = {"football-data.org": True, "Understat": True, "API-Football": True}
        ok = True
    except Exception as e:
        ok = False
        send_private(card_private_error("nightly_refresh", e))
    api_budget = None
    try:
        import requests
        from config import API_FOOTBALL_KEY, API_FOOTBALL_URL
        r = requests.get(API_FOOTBALL_URL + "/status",
                         headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("response", {})
            api_budget = data.get("requests", {}).get("current", None)
    except Exception:
        pass
    send_private(card_private_nightly_report(ok, sources, api_budget))


# ── Weekly digest ─────────────────────────────────────────────

def run_weekly_digest():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM form").fetchall()
        conn.close()
        teams = [dict(r) for r in rows]
        stats = {
            "btts_leaders": sorted(teams, key=lambda x: x.get("btts_rate", 0), reverse=True)[:5],
            "cs_leaders":   sorted(teams, key=lambda x: x.get("cs_rate",   0), reverse=True)[:5],
        }
        send_public(card_weekly_digest(stats, BOT_VERSION))
        roi = get_latest_roi()
        send_private(card_private_roi_summary(roi, label="Weekly ROI Summary"))
    except Exception as e:
        send_private(card_private_error("run_weekly_digest", e))


# ── Schedule ──────────────────────────────────────────────────

def main():
    startup()
    schedule.every().day.at(CACHE_REFRESH_TIME).do(run_nightly_refresh)
    schedule.every().day.at(DIGEST_TIME).do(run_daily_digest)
    schedule.every(30).minutes.do(run_edge_scan)
    schedule.every(30).minutes.do(run_result_checker)
    schedule.every().day.at("21:00").do(run_end_of_day)
    schedule.every().sunday.at("20:00").do(run_weekly_digest)
    log.info("Scheduler running")
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            send_private(card_private_error("scheduler loop", e))
            log.error(traceback.format_exc())
        time.sleep(60)


if __name__ == "__main__":
    main()
