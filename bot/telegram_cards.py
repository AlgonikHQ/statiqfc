# ============================================================
# telegram_cards.py — all message templates
# v1.4 — multi-league, private dashboard, per-fixture skip cards
# ============================================================

from datetime import datetime
from collections import defaultdict

LEAGUE_LABELS = {
    "PL":  "\U0001f3f4 Premier League",
    "BL1": "\U0001f1e9\U0001f1ea Bundesliga",
    "SA":  "\U0001f1ee\U0001f1f9 Serie A",
    "FL1": "\U0001f1eb\U0001f1f7 Ligue 1",
    "PD":  "\U0001f1ea\U0001f1f8 La Liga",
    "CL":  "\u2b50 Champions League",
    "EC":  "\U0001f30d European Championship",
    "WC":  "\U0001f30e World Cup",
    "ELC": "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f Championship",
    "DED": "\U0001f1f3\U0001f1f1 Eredivisie",
    "PPL": "\U0001f1f5\U0001f1f9 Primeira Liga",
}

DISCLAIMER = "\n\n\u26a0\ufe0f Paper portfolio only. No financial advice. 18+ Gamble responsibly."
FOOTER     = "\n\n\u2699\ufe0f StatiqFC {version} | data: football-data.org + Understat + API-Football"


def _ko_time(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        uk=dt.astimezone(__import__("zoneinfo").ZoneInfo("Europe/London"));tz="BST" if int(uk.utcoffset().seconds)==3600 else "GMT";return uk.strftime("%H:%M")+" "+tz
    except Exception:
        return utc_str


def _form_emoji(wdl_list):
    mapping = {"W": "\U0001f7e2", "D": "\U0001f7e1", "L": "\U0001f534"}
    return " ".join(mapping.get(r, "\u2b1c") for r in wdl_list)


def _league_label(code):
    return LEAGUE_LABELS.get(code, code)


# ── Buttons ───────────────────────────────────────────────────

def buttons_edge_alert(home, away):
    hs  = home.replace(" ", "+")
    as_ = away.replace(" ", "+")
    return [
        [
            {"text": "\U0001f4ca Sofascore",  "url": "https://www.sofascore.com/search/" + hs + "+vs+" + as_},
            {"text": "\U0001f522 Flashscore", "url": "https://www.flashscore.com/search/?q=" + hs + "+" + as_}
        ],
        [
            {"text": "\U0001f4c8 Whoscored",  "url": "https://www.whoscored.com"},
            {"text": "\U0001f4c5 Fixtures",   "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "\u26a0\ufe0f Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]


def buttons_result():
    return [
        [
            {"text": "\U0001f4ca Full Record", "url": "https://t.me/StatiqFC"},
            {"text": "\U0001f4c5 Fixtures",    "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "\u26a0\ufe0f Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]


def buttons_digest():
    return [
        [
            {"text": "\U0001f522 Flashscore", "url": "https://www.flashscore.com/football/"},
            {"text": "\U0001f4ca Sofascore",  "url": "https://www.sofascore.com"}
        ],
        [
            {"text": "\U0001f4c8 Whoscored",  "url": "https://www.whoscored.com"},
            {"text": "\u2b50 UEFA",            "url": "https://www.uefa.com/uefachampionsleague/"}
        ]
    ]


def buttons_weekly():
    return [
        [
            {"text": "\U0001f522 Flashscore", "url": "https://www.flashscore.com/football/"},
            {"text": "\U0001f4ca Sofascore",  "url": "https://www.sofascore.com"}
        ],
        [
            {"text": "\U0001f4c8 Whoscored",  "url": "https://www.whoscored.com"},
            {"text": "\u2b50 UEFA",            "url": "https://www.uefa.com"}
        ]
    ]


def buttons_vip():
    return [
        [
            {"text": "\U0001f4ca Our Record",      "url": "https://t.me/StatiqFC"},
            {"text": "\u26a0\ufe0f Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]


# ── PUBLIC: Daily digest ──────────────────────────────────────

def card_daily_digest(fixtures):
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        today_str = datetime.now(ZoneInfo("Europe/London")).strftime("%A %d %B %Y")
    except Exception:
        today_str = datetime.utcnow().strftime("%A %d %B %Y")

    by_league = defaultdict(list)
    for f in fixtures:
        by_league[f.get("league", "PL")].append(f)
    total = len(fixtures)

    lines = [
        "\U0001f5d3\ufe0f *Today\u2019s Fixture Card*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "_" + today_str + "_",
        "",
        str(total) + " fixtures scanning across " + str(len(by_league)) + " leagues.",
        ""
    ]

    league_order = ["PL", "ELC", "BL1", "SA", "FL1", "PD", "DED", "PPL"]
    ordered_codes = [c for c in league_order if c in by_league] + [c for c in sorted(by_league) if c not in league_order]

    for code in ordered_codes:
        lines.append("*" + _league_label(code) + "*")
        for f in sorted(by_league[code], key=lambda x: x["kickoff_utc"]):
            ko = _ko_time(f["kickoff_utc"])
            lines.append("  \u26bd " + f["home"] + " vs " + f["away"] + "  \u2022  " + ko)
        lines.append("")

    lines.extend([
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "_Picks announced individually 30 mins before each kickoff._",
        "_Edge alerts fire when our 6-layer model scores \u2265 4/6._"
    ])
    return "\n".join(lines)


# ── PUBLIC: Edge alert ────────────────────────────────────────

def card_edge_alert(edge, form_home, form_away, h2h_rows, odds, version):
    home         = edge["home"]
    away         = edge["away"]
    market       = edge["market"]
    stake        = edge["stake"]
    odds_val     = edge["odds"]
    potential    = edge["potential"]
    ko           = _ko_time(edge["kickoff"])
    reasoning    = edge.get("reasoning", "")
    league_code  = edge.get("league", "PL")
    league_label = _league_label(league_code)
    score_str    = edge.get("score_str", "?/6")
    layers       = edge.get("layers", [])

    market_labels = {
        "BTTS":    "Both Teams to Score",
        "CS_HOME": "Home Clean Sheet",
        "OVER25":  "Over 2.5 Goals"
    }
    market_label = market_labels.get(market, market)
    sel_type     = "\U0001f528 *Builder Single*" if edge.get("is_builder") else "\u26a1 *Edge Alert*"

    h_form = _form_emoji(form_home.get("last5_list", [])) if form_home else "N/A"
    a_form = _form_emoji(form_away.get("last5_list", [])) if form_away else "N/A"

    h2h_summary = ""
    if h2h_rows:
        h2h_lines = []
        for r in h2h_rows[:3]:
            h2h_lines.append("  " + r["home"] + " " + str(r["home_score"]) + "\u2013" + str(r["away_score"]) + " " + r["away"] + " (" + r["date"] + ")")
        h2h_summary = "\n\n*H2H (last 3)*\n" + "\n".join(h2h_lines)

    odds_line = ""
    if odds:
        odds_line = (
            "\n\n*Reference odds (snapshot)*"
            "\n  " + home + " win: " + str(odds.get("home", "N/A")) +
            "\n  Draw: " + str(odds.get("draw", "N/A")) +
            "\n  " + away + " win: " + str(odds.get("away", "N/A")) +
            "\n  \u23f1\ufe0f Verify before placing"
        )

    layers_short = " | ".join(layers[:3]) if layers else ""

    return (
        sel_type + "\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f3c6  " + league_label + "\n"
        "\U0001f3df\ufe0f  *" + home + " vs " + away + "*\n"
        "\u23f0  Kick-off: " + ko + "\n\n"
        "\U0001f4cc  *Market:* " + market_label + "\n"
        "\U0001f4b7  Stake: " + str(stake) + "u  |  Odds: " + str(odds_val) + "  |  Potential: " + str(round(potential, 2)) + "u\n\n"
        "\U0001f4ca  *Form (last 5)*\n"
        "  " + home + ": " + h_form + "\n"
        "  " + away + ": " + a_form + "\n\n"
        "\U0001f522  *Stat basis*\n"
        "  " + reasoning + "\n\n"
        "\U0001f4d0  *Signal strength: " + score_str + "*\n"
        "  " + layers_short +
        h2h_summary +
        odds_line +
        DISCLAIMER +
        FOOTER.format(version=version)
    )


# ── PUBLIC: Per-fixture skip card ─────────────────────────────

def card_fixture_skip(home, away, league, kickoff_utc, score, max_score, next_ko=None):
    ko           = _ko_time(kickoff_utc)
    league_label = _league_label(league)
    next_line    = "\nNext fixture in scan window: " + next_ko if next_ko else ""
    return (
        "\U0001f50d *No edge \u2014 " + home + " vs " + away + "*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        + league_label + " | " + ko + "\n\n"
        "Scanned this fixture \u2014 signal scored " + str(score) + "/" + str(max_score) + ".\n"
        "Conditions didn't meet our threshold." + next_line + "\n\n"
        "_Scanning remaining fixtures as scheduled._"
    )


# ── PUBLIC: End-of-day no alerts ──────────────────────────────

# ── PUBLIC: Clean skip notice (T-30 mins before kickoff) ─────

# ── PUBLIC: Full-time result (no scorers, 1-3h lag via CSV) ──

def card_public_ft_result(home, away, home_score, away_score, league, was_edge=False, edge_result=None):
    """Clean FT result card for subscribers. Shows edge result if applicable."""
    league_label = _league_label(league)
    edge_line    = ""
    if was_edge and edge_result:
        emoji = {"WIN":"\u2705","LOSS":"\u274c","VOID":"\u21a9\ufe0f","PUSH":"\u21a9\ufe0f"}.get(edge_result, "")
        edge_line = "\n\n" + emoji + " *Our pick: " + edge_result + "*"
    return (
        "\u23f1 *FT \u2014 " + home + " " + str(home_score) + "-" + str(away_score) + " " + away + "*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        + league_label
        + edge_line
    )


def card_public_skip(home, away, league, kickoff_utc):
    """Clean, professional skip notice for subscribers. No verbose scoring."""
    league_label = _league_label(league)
    ko           = _ko_time(kickoff_utc)
    return (
        "\u26aa *Skipped \u2014 " + home + " vs " + away + "*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        + league_label + " | " + ko + "\n\n"
        "No viable edge \u2014 no pick posted."
    )


# ── PUBLIC: End-of-day unified summary ───────────────────────

def card_public_eod_summary(today_stats, alltime_stats, leagues_scanned=None):
    """End-of-day summary for subscribers. Always posts.
    today_stats from get_daily_pnl(), alltime_stats from get_alltime_stats()."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        date_str = datetime.now(ZoneInfo("Europe/London")).strftime("%A %d %B %Y")
    except Exception:
        date_str = datetime.utcnow().strftime("%A %d %B %Y")

    edges = today_stats.get("edges_placed", 0) if today_stats else 0
    if today_stats and today_stats.get("edges", 0):
        edges = today_stats["edges"]

    # Normalise key names (refresh_daily_pnl returns slightly different shape than get_daily_pnl)
    def _g(d, *keys, default=0):
        for k in keys:
            if d and d.get(k) is not None:
                return d[k]
        return default

    wins    = _g(today_stats, "wins")
    losses  = _g(today_stats, "losses")
    pushes  = _g(today_stats, "pushes")
    voids   = _g(today_stats, "voids")
    staked  = _g(today_stats, "stake_units", "staked")
    ret     = _g(today_stats, "return_units", "returned")
    pnl     = _g(today_stats, "pnl_units", "pnl")
    roi     = _g(today_stats, "daily_roi_pct", "roi_pct")

    at_edges  = _g(alltime_stats, "total_edges")
    at_wins   = _g(alltime_stats, "total_wins")
    at_losses = _g(alltime_stats, "total_losses")
    at_staked = _g(alltime_stats, "total_staked")
    at_pnl    = _g(alltime_stats, "total_pnl")
    at_roi    = _g(alltime_stats, "roi_pct")
    at_days   = _g(alltime_stats, "active_days")

    pnl_emoji = "\U0001f7e2" if pnl > 0 else ("\U0001f534" if pnl < 0 else "\u26aa")
    at_pnl_emoji = "\U0001f7e2" if at_pnl > 0 else ("\U0001f534" if at_pnl < 0 else "\u26aa")

    lines = [
        "\U0001f4ca *End of Day Summary*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "_" + date_str + "_",
        ""
    ]

    if edges == 0:
        lines.extend([
            "\u26aa *No edges today*",
            "Our 6-layer model didn\u2019t find any picks meeting threshold (4/6).",
            "When the data doesn\u2019t align, we stay out. Quality over quantity.",
            ""
        ])
    else:
        win_line = str(wins) + "W"
        if losses: win_line += " \u2013 " + str(losses) + "L"
        if pushes: win_line += " \u2013 " + str(pushes) + "P"
        if voids:  win_line += " \u2013 " + str(voids) + "V"

        lines.extend([
            "\U0001f4cd *Today\u2019s picks: " + str(edges) + "*",
            "   " + win_line,
            "   Staked: " + str(round(staked, 2)) + "u  |  Returned: " + str(round(ret, 2)) + "u",
            "   " + pnl_emoji + " P&L: " + ("+" if pnl >= 0 else "") + str(round(pnl, 2)) + "u  |  ROI: " + ("+" if roi >= 0 else "") + str(round(roi, 2)) + "%",
            ""
        ])

    lines.extend([
        "\U0001f4c8 *All-time (over " + str(at_days) + " active day" + ("s" if at_days != 1 else "") + ")*",
        "   Picks: " + str(at_edges) + "  |  " + str(at_wins) + "W\u2013" + str(at_losses) + "L",
        "   Staked: " + str(round(at_staked, 2)) + "u  |  " + at_pnl_emoji + " P&L: " + ("+" if at_pnl >= 0 else "") + str(round(at_pnl, 2)) + "u  |  ROI: " + ("+" if at_roi >= 0 else "") + str(round(at_roi, 2)) + "%",
        "",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "_Results track paper stakes only. 18+ gamble responsibly._"
    ])
    return "\n".join(lines)


def card_no_alerts_today(fixtures_scanned, top_score=0, leagues_scanned=None):
    scanned_str   = str(fixtures_scanned) if fixtures_scanned else "today's"
    league_labels = {"PL":"PL","BL1":"Bundesliga","SA":"Serie A","FL1":"Ligue 1","PD":"La Liga","CL":"UCL","EC":"Euros","WC":"World Cup"}
    leagues_str   = " & ".join(sorted(league_labels.get(l, l) for l in leagues_scanned)) if leagues_scanned else "all leagues"
    return (
        "\U0001f4ca *End of day \u2014 no edges found*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Today's scan: " + scanned_str + " fixtures across " + leagues_str + ". Top score: " + str(top_score) + "/6. Our threshold is 4/6.\n\n"
        "When our 6-layer model (form, xG, splits, H2H, standings, odds) doesn't align, we stay out. No forced picks, no filler content.\n\n"
        "_Quality over quantity. Back tomorrow._"
    )


# ── PUBLIC: Result card ───────────────────────────────────────

def card_result(selection, roi):
    result       = selection["result"]
    profit       = selection["profit"]
    home         = selection["home"]
    away         = selection["away"]
    market       = selection["market"]
    odds_val     = selection["odds"]
    stake        = selection["stake"]
    result_emoji = {"WIN": "\u2705", "LOSS": "\u274c", "VOID": "\u21a9\ufe0f"}.get(result, "\u2753")
    pl_sign      = "+" if profit >= 0 else ""

    market_labels = {"BTTS": "Both Teams to Score", "CS_HOME": "Home Clean Sheet", "OVER25": "Over 2.5 Goals"}
    market_label  = market_labels.get(market, market)

    roi_line = ""
    if roi:
        roi_sign = "+" if roi["roi_pct"] >= 0 else ""
        pl_s     = "+" if roi["net_pl"] >= 0 else ""
        roi_line = (
            "\n\n\U0001f4c8 *Running record*"
            "\n  W" + str(roi["wins"]) + " L" + str(roi["losses"]) +
            " | Staked: " + str(round(roi["total_staked"], 2)) + "u" +
            " | P&L: " + pl_s + str(round(roi["net_pl"], 2)) + "u" +
            " | ROI: " + roi_sign + str(roi["roi_pct"]) + "%"
        )

    return (
        result_emoji + " *Result \u2014 " + home + " vs " + away + "*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Market: " + market_label + " | Odds: " + str(odds_val) + " | Stake: " + str(stake) + "u\n"
        "*Profit: " + pl_sign + str(round(profit, 2)) + "u*" +
        roi_line +
        DISCLAIMER
    )


# ── PUBLIC: Weekly digest ─────────────────────────────────────

def card_weekly_digest(stats, version):
    btts_leaders = stats.get("btts_leaders", [])
    cs_leaders   = stats.get("cs_leaders",   [])

    btts_lines = "\n".join("  " + t["team"] + ": " + str(int(t["btts_rate"] * 100)) + "%" for t in btts_leaders[:5])
    cs_lines   = "\n".join("  " + t["team"] + ": " + str(int(t["cs_rate"]   * 100)) + "%" for t in cs_leaders[:5])

    return (
        "\U0001f4ca *Weekly Stats Digest*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "\u26bd *BTTS leaders (last 8 games)*\n" + btts_lines + "\n\n"
        "\U0001f512 *Clean sheet leaders (last 8 games)*\n" + cs_lines +
        FOOTER.format(version=version)
    )


# ── PUBLIC: VIP unlock ────────────────────────────────────────

def card_vip_unlock(roi):
    return (
        "\U0001f3c6 *VIP Tier Now Open*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "We hit our target: *+" + str(roi["roi_pct"]) + "% ROI over " + str(roi["selections"]) + " selections*.\n\n"
        "The public record speaks for itself. No hype, just data.\n\n"
        "VIP members get:\n"
        "  \u2192 Alerts 1 hour earlier\n"
        "  \u2192 Full 6-layer signal breakdown\n"
        "  \u2192 Near-miss picks\n"
        "  \u2192 Monthly performance reports\n\n"
        "Free channel stays live \u2014 always.\n"
        "Link to subscribe: [coming soon]"
    )


# ── PRIVATE: Startup card ─────────────────────────────────────

def card_private_startup(version, patch_notes, leagues):
    league_list = "\n".join("  \u2022 " + LEAGUE_LABELS.get(l, l) for l in leagues)
    return (
        "\u2705 *StatiqFC " + version + " \u2014 ONLINE*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f7e2 Service started\n"
        "\U0001f4e1 Public channel: active\n"
        "\U0001f5d3\ufe0f Scheduler: running\n\n"
        "\U0001f4cb *Leagues active:*\n" + league_list + "\n\n"
        "\U0001f4b7 Stakes: 1u standard / 0.5u builder\n"
        "\U0001f3af Alert threshold: 4/6 layers\n"
        "\U0001f3af VIP target: +20% ROI / 50 selections\n\n"
        "_" + patch_notes + "_"
    )


# ── PRIVATE: Morning briefing ─────────────────────────────────

def card_private_morning_briefing(fixtures, version):
    total     = len(fixtures)
    by_league = defaultdict(list)
    for f in fixtures:
        by_league[f.get("league", "PL")].append(f)

    today_str = datetime.utcnow().strftime("%d %b %Y")
    lines = [
        "\U0001f305 *Morning Briefing \u2014 " + today_str + "*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "\U0001f4cb " + str(total) + " fixture(s) to scan today\n"
    ]
    for league_code, lf in sorted(by_league.items()):
        lines.append(_league_label(league_code))
        for f in lf:
            ko = _ko_time(f["kickoff_utc"])
            lines.append("  \u26bd " + f["home"] + " vs " + f["away"] + " \u2014 " + ko)

    lines.append("\n_Edge scans fire 2hrs before each KO._")
    lines.append("\u2699\ufe0f StatiqFC " + version)
    return "\n".join(lines)


# ── PRIVATE: Full alert breakdown ─────────────────────────────

def card_private_alert_detail(edge, version):
    home      = edge["home"]
    away      = edge["away"]
    market    = edge["market"]
    layers    = edge.get("layers", [])
    score_str = edge.get("score_str", "?/6")
    reasoning = edge.get("reasoning", "")
    league    = _league_label(edge.get("league", "PL"))

    market_labels = {"BTTS": "Both Teams to Score", "CS_HOME": "Home Clean Sheet", "OVER25": "Over 2.5 Goals"}
    market_label  = market_labels.get(market, market)
    all_layers    = "\n".join("  " + l for l in layers) if layers else "  No layer data"

    return (
        "\U0001f52c *Private \u2014 Full Signal Breakdown*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f3c6 " + league + "\n"
        "\U0001f3df\ufe0f " + home + " vs " + away + "\n"
        "\U0001f4cc " + market_label + "\n\n"
        "\U0001f4d0 *Score: " + score_str + "*\n" +
        all_layers + "\n\n"
        "\U0001f522 *Full reasoning:*\n"
        "  " + reasoning + "\n\n"
        "\u2699\ufe0f StatiqFC " + version
    )


# ── PRIVATE: Near-miss log ────────────────────────────────────

def card_private_near_misses(near_misses, version):
    if not near_misses:
        return None
    lines = [
        "\U0001f4cb *Near-Miss Picks Today*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "These fixtures scored 3/6 \u2014 just below threshold:\n"
    ]
    for nm in near_misses:
        league = _league_label(nm.get("league", "PL"))
        layers = " | ".join(nm.get("layers", []))
        lines.append(
            "\U0001f3df\ufe0f " + nm["home"] + " vs " + nm["away"] + " [" + nm["market"] + "]\n"
            "  " + league + " | Score: " + str(nm["score"]) + "/6\n"
            "  " + layers
        )
    lines.append("\n_Threshold is 4/6. Adjust MIN_SCORE_TO_ALERT in config if needed._")
    lines.append("\u2699\ufe0f StatiqFC " + version)
    return "\n".join(lines)


# ── PRIVATE: Nightly cache report ─────────────────────────────

def card_private_nightly_report(ok, data_sources, api_budget=None):
    status = "\u2705 All sources OK" if ok else "\u26a0\ufe0f Some sources failed"
    lines  = [
        "\U0001f504 *Nightly Cache Report*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "Status: " + status,
        "Time: " + datetime.utcnow().strftime("%H:%M UTC") + "\n",
        "*Data sources:*"
    ]
    for source, source_ok in data_sources.items():
        icon = "\u2705" if source_ok else "\u274c"
        lines.append("  " + icon + " " + source)

    if api_budget is not None:
        lines.append("\n*API-Football budget:*\n  Used today: " + str(api_budget) + " / 100 requests")

    return "\n".join(lines)


# ── PRIVATE: ROI summary ──────────────────────────────────────

def card_private_roi_summary(roi, label="Daily ROI Summary"):
    if not roi:
        return "\U0001f4ca *" + label + "*\nNo settled selections yet."
    sign = lambda v: "+" if v >= 0 else ""
    return (
        "\U0001f4ca *" + label + "*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Selections: " + str(roi["selections"]) + "  (W" + str(roi["wins"]) + " L" + str(roi["losses"]) + " V" + str(roi.get("voids", 0)) + ")\n"
        "Staked:     " + str(round(roi["total_staked"], 2)) + "u\n"
        "Returned:   " + str(round(roi["total_return"], 2)) + "u\n"
        "Net P&L:    " + sign(roi["net_pl"]) + str(round(roi["net_pl"], 2)) + "u\n"
        "ROI:        " + sign(roi["roi_pct"]) + str(roi["roi_pct"]) + "%\n\n"
        "VIP progress: " + str(roi["selections"]) + "/50 sels | " + sign(roi["roi_pct"]) + str(roi["roi_pct"]) + "% ROI"
    )


# ── PRIVATE: Error card ───────────────────────────────────────

def card_private_error(context, err):
    return (
        "\u26a0\ufe0f *StatiqFC \u2014 Error*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Context: `" + str(context) + "`\n"
        "Error: `" + str(err)[:300] + "`\n"
        "Time: " + datetime.utcnow().strftime("%H:%M UTC")
    )


# ── Legacy aliases ────────────────────────────────────────────

def card_no_alert():
    return card_no_alerts_today(0)

def _private_startup_card():
    from config import BOT_VERSION, PATCH_NOTES, LEAGUE_CODES
    return card_private_startup(BOT_VERSION, PATCH_NOTES, LEAGUE_CODES)

def _private_error_card(context, err):
    return card_private_error(context, err)

def _private_roi_summary(roi, label="Daily ROI Summary"):
    return card_private_roi_summary(roi, label)

def _private_nightly_cache_card(ok):
    return card_private_nightly_report(ok, {"football-data.org": ok, "Understat": ok, "API-Football": ok})

def card_public_ft_results_block(results):
    """Single consolidated FT results block for EOD. results = list of dicts with home/away/fthg/ftag/league/was_edge/edge_result."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        date_str = datetime.now(ZoneInfo("Europe/London")).strftime("%d %b %Y")
    except Exception:
        date_str = datetime.utcnow().strftime("%d %b %Y")

    lines = [
        "\u23f1 *Today\u2019s Results \u2014 " + date_str + "*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
    ]
    current_league = None
    for r in results:
        league_label = _league_label(r.get("league", "PL"))
        if league_label != current_league:
            lines.append("\n" + league_label)
            current_league = league_label
        score_line = "\u2022 " + r["home"] + " *" + str(r["fthg"]) + "\u2013" + str(r["ftag"]) + "* " + r["away"]
        if r.get("was_edge") and r.get("edge_result"):
            emoji = {"WIN": "\u2705", "LOSS": "\u274c", "VOID": "\u21a9\ufe0f"}.get(r["edge_result"], "")
            score_line += "  " + emoji + " _" + r["edge_result"] + "_"
        lines.append(score_line)

    lines.append("\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    lines.append("_Powered by StatiqFC_")
    return "\n".join(lines)
