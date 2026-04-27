# ============================================================
# NEW CARDS — VIP rebuild Apr 2026
# Append to telegram_cards.py
# ============================================================

# ── ONE-SHOT: Public welcome ──────────────────────────────────
def card_public_welcome():
    """One-shot welcome message for new public channel @StatiqFCpicks."""
    return (
        "\U0001f3af *Welcome to StatiqFC*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\n"
        "We're a stats-driven football model that scans 9+ leagues every day,\n"
        "running a 6-layer signal stack across BTTS, Clean Sheets, and Over/Under markets.\n"
        "\n"
        "\U0001f4cd *What you'll see here*\n"
        "   \U0001f4c5 Daily morning briefing \u2014 fixtures we're watching\n"
        "   \u26bd FT results \u2014 every pick, win or lose, fully transparent\n"
        "   \U0001f4ca Daily summary \u2014 running ROI, never hidden\n"
        "   \U0001f4c8 Weekly recap \u2014 every Sunday\n"
        "   \U0001f3c6 Monthly milestones\n"
        "\n"
        "\U0001f514 *Want live picks before kickoff?*\n"
        "   The actual edge alerts (with stake, odds, full reasoning)\n"
        "   fire to our VIP channel in real-time. Tap below to join.\n"
        "\n"
        "\u26a0\ufe0f Paper portfolio only. No financial advice. 18+ Gamble responsibly.\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
    )


# ── ONE-SHOT: VIP welcome ─────────────────────────────────────
def card_vip_welcome():
    """One-shot welcome message for VIP channel StatiqFCVIP."""
    return (
        "\U0001f48e *Welcome to StatiqFC VIP*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\n"
        "You're in the room where the picks fire.\n"
        "\n"
        "\U0001f4cd *What you'll see here*\n"
        "   \u26a1 Live edge alerts \u2014 the moment our model finds a pick\n"
        "   \U0001f6ab T-30 skip notices \u2014 the matches we passed on, and why\n"
        "   \U0001f4ca Deeper reasoning \u2014 xG, form, H2H, layered signal breakdown\n"
        "   \U0001f4c8 VIP weekly deep dive \u2014 markets, leagues, drawdowns (Sundays)\n"
        "   \U0001f4ac Commentary \u2014 the human read on the data\n"
        "\n"
        "\U0001f3af *Current status*\n"
        "   Paper portfolio mode. Free VIP access for early adopters.\n"
        "   When the model has 50+ picks at break-even or better,\n"
        "   we'll move to a paid VIP tier. You'll keep your spot.\n"
        "\n"
        "\u26a0\ufe0f Paper portfolio only. No financial advice. 18+ Gamble responsibly.\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
    )


# ── PUBLIC: Monthly milestone ─────────────────────────────────
def card_public_monthly_milestone(month_stats, alltime_stats, top_market=None, top_leagues=None):
    """First-of-month review card for public channel.
    month_stats expected keys: edges, wins, losses, pushes, staked, returned, pnl, roi_pct, month_name
    top_market expected: {'name': 'BTTS', 'picks': N, 'pnl': X}
    top_leagues expected: list of league names sorted by pick volume."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        now = datetime.utcnow()

    month_name = month_stats.get("month_name") if month_stats else None
    if not month_name:
        # default to previous month name
        prev_month = now.replace(day=1)
        # roll back one day to get last month
        from datetime import timedelta
        prev_month = prev_month - timedelta(days=1)
        month_name = prev_month.strftime("%B %Y")

    def _g(d, *keys, default=0):
        for k in keys:
            if d and d.get(k) is not None:
                return d[k]
        return default

    edges    = _g(month_stats, "edges", "total_edges")
    wins     = _g(month_stats, "wins", "total_wins")
    losses   = _g(month_stats, "losses", "total_losses")
    pushes   = _g(month_stats, "pushes")
    staked   = _g(month_stats, "staked", "total_staked")
    ret      = _g(month_stats, "returned")
    pnl      = _g(month_stats, "pnl", "total_pnl")
    roi      = _g(month_stats, "roi_pct")

    at_edges = _g(alltime_stats, "total_edges")
    at_pnl   = _g(alltime_stats, "total_pnl")
    at_roi   = _g(alltime_stats, "roi_pct")

    pnl_emoji    = "\U0001f7e2" if pnl > 0 else ("\U0001f534" if pnl < 0 else "\u26aa")
    at_pnl_emoji = "\U0001f7e2" if at_pnl > 0 else ("\U0001f534" if at_pnl < 0 else "\u26aa")

    lines = [
        "\U0001f3c6 *Month in Review \u2014 " + str(month_name) + "*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "",
        "\U0001f4ca *Performance*",
        "   Picks: " + str(edges),
        "   \u2705 " + str(wins) + "W  \u274c " + str(losses) + "L" + ("  \u2013 " + str(pushes) + "P" if pushes else ""),
        "   Staked: " + str(round(staked, 2)) + "u  |  Returned: " + str(round(ret, 2)) + "u",
        "   " + pnl_emoji + " P&L: " + ("+" if pnl >= 0 else "") + str(round(pnl, 2)) + "u  |  ROI: " + ("+" if roi >= 0 else "") + str(round(roi, 2)) + "%",
        ""
    ]

    if top_market and top_market.get("name"):
        tm_pnl = top_market.get("pnl", 0)
        lines.extend([
            "\U0001f4c8 *Best market this month*",
            "   " + str(top_market["name"]) + " \u2014 " + str(top_market.get("picks", 0)) + " picks, " + ("+" if tm_pnl >= 0 else "") + str(round(tm_pnl, 2)) + "u P&L",
            ""
        ])

    if top_leagues:
        leagues_str = " \u00b7 ".join(top_leagues[:3])
        lines.extend([
            "\U0001f30d *Most active leagues*",
            "   " + leagues_str,
            ""
        ])

    lines.extend([
        "\U0001f4ca *All-time (since launch)*",
        "   " + str(at_edges) + " picks  |  ROI: " + ("+" if at_roi >= 0 else "") + str(round(at_roi, 2)) + "%  |  " + at_pnl_emoji + " P&L: " + ("+" if at_pnl >= 0 else "") + str(round(at_pnl, 2)) + "u",
        "",
        "\U0001f514 Live picks fire to VIP in real-time \u2192 tap below to join.",
        "",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "_Paper portfolio. 18+ Gamble responsibly._"
    ])
    return "\n".join(lines)


# ── VIP: Weekly deep dive ─────────────────────────────────────
def card_vip_weekly_deep_dive(week_stats, by_market=None, by_league=None,
                               drawdown=None, hot_streak=None,
                               commentary=None, next_week_count=0,
                               week_ending_str=None):
    """Sunday VIP-only deep-dive card.
    week_stats: {edges, wins, losses, staked, pnl_units, roi_pct}
    by_market: dict like {'BTTS': {'picks': N, 'pnl': X}, ...}
    by_league: list of (league_name, picks, pnl) tuples
    drawdown: float (most negative running pnl this week)
    hot_streak: dict {'count': N, 'pnl': X}
    commentary: optional manual string for 'Read of the week'
    next_week_count: int (high-scoring matches already on radar)
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        now = datetime.utcnow()
    if not week_ending_str:
        week_ending_str = now.strftime("%d %b %Y")

    def _g(d, *keys, default=0):
        for k in keys:
            if d and d.get(k) is not None:
                return d[k]
        return default

    edges  = _g(week_stats, "edges", "total_edges")
    wins   = _g(week_stats, "wins", "total_wins")
    losses = _g(week_stats, "losses", "total_losses")
    staked = _g(week_stats, "staked", "total_staked", "stake_units")
    pnl    = _g(week_stats, "pnl_units", "total_pnl", "pnl")
    roi    = _g(week_stats, "roi_pct")

    pnl_emoji = "\U0001f7e2" if pnl > 0 else ("\U0001f534" if pnl < 0 else "\u26aa")

    lines = [
        "\U0001f48e *VIP Weekly Deep Dive \u2014 Week ending " + week_ending_str + "*",
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
        "",
        "\U0001f50d *This week's signal*",
        "   Picks fired: " + str(edges),
        "   \u2705 " + str(wins) + "W  \u274c " + str(losses) + "L",
        "   Staked: " + str(round(staked, 2)) + "u  |  " + pnl_emoji + " P&L: " + ("+" if pnl >= 0 else "") + str(round(pnl, 2)) + "u  |  ROI: " + ("+" if roi >= 0 else "") + str(round(roi, 2)) + "%",
        ""
    ]

    if by_market:
        lines.append("\U0001f4ca *By market*")
        for mkt_name in ("BTTS", "CS_HOME", "OVER25"):
            if mkt_name in by_market:
                m = by_market[mkt_name]
                m_pnl = m.get("pnl", 0)
                lines.append("   " + mkt_name + ": " + str(m.get("picks", 0)) + " picks, " + ("+" if m_pnl >= 0 else "") + str(round(m_pnl, 2)) + "u")
        lines.append("")

    if by_league:
        lines.append("\U0001f30d *By league*")
        for entry in by_league[:5]:
            try:
                lname, lpicks, lpnl = entry[0], entry[1], entry[2]
                lines.append("   " + str(lname) + ": " + str(lpicks) + " picks, " + ("+" if lpnl >= 0 else "") + str(round(lpnl, 2)) + "u")
            except Exception:
                continue
        lines.append("")

    if drawdown is not None or hot_streak:
        lines.append("\U0001f4c9 *Drawdown / hot streak*")
        if hot_streak and hot_streak.get("count"):
            hs_pnl = hot_streak.get("pnl", 0)
            lines.append("   Best run: +" + str(round(hs_pnl, 2)) + "u over " + str(hot_streak["count"]) + " picks")
        if drawdown is not None:
            lines.append("   Worst drawdown this week: " + str(round(drawdown, 2)) + "u")
        lines.append("")

    if commentary:
        lines.extend([
            "\U0001f9e0 *Read of the week*",
            "   " + str(commentary),
            ""
        ])

    if next_week_count and next_week_count > 0:
        lines.extend([
            "\U0001f4c5 *Next week's signal pipeline*",
            "   " + str(next_week_count) + " high-scoring matches already on the radar.",
            ""
        ])

    lines.append("\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    return "\n".join(lines)
# ============================================================
# NEW BUTTON HELPERS — VIP rebuild
# Append to telegram_cards.py (or wherever buttons_* helpers live)
# ============================================================

VIP_INVITE_URL  = "https://t.me/+rWBSn9kmj45iNTlk"
PUBLIC_URL      = "https://t.me/StatiqFCpicks"
SOFASCORE_URL   = "https://www.sofascore.com/football"

def buttons_public_welcome():
    """Buttons for the public welcome post."""
    return [[
        {"text": "\U0001f48e Join VIP",      "url": VIP_INVITE_URL},
        {"text": "\U0001f4c5 Live Fixtures", "url": SOFASCORE_URL},
    ]]

def buttons_public_monthly():
    """Buttons for the monthly milestone card."""
    return [[
        {"text": "\U0001f48e Join VIP",         "url": VIP_INVITE_URL},
        {"text": "\U0001f4ca Live Fixtures",    "url": SOFASCORE_URL},
    ]]
