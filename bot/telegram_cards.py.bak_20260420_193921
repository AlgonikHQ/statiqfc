# ============================================================
# telegram_cards.py — all message templates for the channel
# ============================================================

from datetime import datetime

def buttons_edge_alert(home, away):
    hs = home.replace(" ", "+")
    as_ = away.replace(" ", "+")
    query = f"{hs}+vs+{as_}+premier+league"
    return [
        [
            {"text": "📊 Sofascore",   "url": f"https://www.sofascore.com/search/{query}"},
            {"text": "🔢 Flashscore",  "url": f"https://www.flashscore.com/search/?q={hs}+{as_}"}
        ],
        [
            {"text": "📈 Whoscored",   "url": f"https://www.whoscored.com"},
            {"text": "🏆 PL Website",  "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "⚠️ Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]

def buttons_result():
    return [
        [
            {"text": "📊 Full ROI",     "url": "https://t.me/StatiqFC"},
            {"text": "📅 PL Fixtures",  "url": "https://www.premierleague.com/fixtures"}
        ],
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"}
        ]
    ]

def buttons_digest():
    return [
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"},
            {"text": "📈 Whoscored",   "url": "https://www.whoscored.com/Regions/252/Tournaments/2/Seasons/9618/Stages/22076/Show/England-Premier-League-2024-2025"}
        ],
        [
            {"text": "🔢 Flashscore",  "url": "https://www.flashscore.com/football/england/premier-league/"},
            {"text": "📊 Sofascore",   "url": "https://www.sofascore.com/tournament/football/england/premier-league/17"}
        ]
    ]

def buttons_weekly():
    return [
        [
            {"text": "🏆 PL Table",    "url": "https://www.premierleague.com/tables"},
            {"text": "📊 Sofascore",   "url": "https://www.sofascore.com/tournament/football/england/premier-league/17"}
        ],
        [
            {"text": "📈 Whoscored",   "url": "https://www.whoscored.com"},
            {"text": "🔢 Flashscore",  "url": "https://www.flashscore.com/football/england/premier-league/"}
        ]
    ]

def buttons_vip():
    return [
        [
            {"text": "📊 Our Record",  "url": "https://t.me/StatiqFC"},
            {"text": "⚠️ Bet Responsibly", "url": "https://www.begambleaware.org"}
        ]
    ]


DISCLAIMER = "\n\n⚠️ Paper portfolio only. No financial advice. 18+ Gamble responsibly."
FOOTER     = "\n\n⚙️ StatiqFC {version} | data: football-data.org"

def _ko_time(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M UTC")
    except Exception:
        return utc_str

def _form_emoji(wdl_list):
    mapping = {"W": "🟢", "D": "🟡", "L": "🔴"}
    return " ".join(mapping.get(r, "⬜") for r in wdl_list)

# ── Daily digest ──────────────────────────────────────────────

def card_daily_digest(fixtures):
    """Morning fixture card — sent at 8am."""
    lines = ["📋 *Today's Premier League Fixtures*\n"]
    for f in fixtures:
        ko = _ko_time(f["kickoff_utc"])
        lines.append(f"⚽ {f['home']} vs {f['away']} — {ko}")
    lines.append("\nAll stats-based Edge Alerts drop 2hrs before kick-off.")
    return "\n".join(lines)

# ── Pre-match edge alert ──────────────────────────────────────

def card_edge_alert(edge, form_home, form_away, h2h_rows, odds, version):
    home      = edge["home"]
    away      = edge["away"]
    market    = edge["market"]
    stake     = edge["stake"]
    odds_val  = edge["odds"]
    potential = edge["potential"]
    ko        = _ko_time(edge["kickoff"])
    reasoning = edge.get("reasoning", "")

    market_labels = {
        "BTTS":    "Both Teams to Score",
        "CS_HOME": "Home Clean Sheet",
        "OVER25":  "Over 2.5 Goals"
    }
    market_label = market_labels.get(market, market)

    is_builder = edge.get("is_builder", False)
    sel_type   = "🔨 *Builder Single*" if is_builder else "⚡ *Edge Alert*"

    h_form = _form_emoji(form_home.get("last5_list", [])) if form_home else "N/A"
    a_form = _form_emoji(form_away.get("last5_list", [])) if form_away else "N/A"

    h2h_summary = ""
    if h2h_rows:
        last3 = h2h_rows[:3]
        h2h_lines = [f"  {r['home']} {r['home_score']}–{r['away_score']} {r['away']} ({r['date']})" for r in last3]
        h2h_summary = "\n\n*H2H (last 3)*\n" + "\n".join(h2h_lines)

    odds_line = ""
    if odds:
        odds_line = (
            f"\n\n*Reference odds (snapshot)*"
            f"\n  {home} win: {odds.get('home','N/A')}"
            f"\n  Draw: {odds.get('draw','N/A')}"
            f"\n  {away} win: {odds.get('away','N/A')}"
            f"\n  ⏱️ Odds correct at time of alert — verify before placing"
        )

    msg = (
        f"{sel_type}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏟️  *{home} vs {away}*\n"
        f"⏰  Kick-off: {ko}\n\n"
        f"📌  *Market:* {market_label}\n"
        f"💷  Stake: £{stake}  |  Odds: {odds_val}  |  Potential: £{potential}\n\n"
        f"📊  *Form (last 5)*\n"
        f"  {home}: {h_form}\n"
        f"  {away}: {a_form}\n\n"
        f"🔢  *Stat basis*\n"
        f"  {reasoning}"
        f"{h2h_summary}"
        f"{odds_line}"
        f"{DISCLAIMER}"
        f"{FOOTER.format(version=version)}"
    )
    return msg

# ── Result card ───────────────────────────────────────────────

def card_result(selection, roi):
    result   = selection["result"]
    profit   = selection["profit"]
    home     = selection["home"]
    away     = selection["away"]
    market   = selection["market"]
    odds_val = selection["odds"]
    stake    = selection["stake"]

    result_emoji = {"WIN": "✅", "LOSS": "❌", "VOID": "↩️"}.get(result, "❓")
    pl_sign      = "+" if profit >= 0 else ""

    roi_line = ""
    if roi:
        roi_line = (
            f"\n\n📈 *Running record*"
            f"\n  W{roi['wins']} L{roi['losses']} | "
            f"Staked: £{roi['total_staked']} | "
            f"P&L: {pl_sign}£{roi['net_pl']} | "
            f"ROI: {'+' if roi['roi_pct']>=0 else ''}{roi['roi_pct']}%"
        )

    msg = (
        f"{result_emoji} *Result — {home} vs {away}*\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Market: {market} | Odds: {odds_val} | Stake: £{stake}\n"
        f"*Profit: {pl_sign}£{profit}*"
        f"{roi_line}"
    )
    return msg

# ── No alert card (transparency) ─────────────────────────────

def card_no_alert():
    return (
        "🔍 *No edge alerts today*\n"
        "Scanned today's Premier League fixtures — "
        "no statistical conditions met our threshold.\n"
        "Quality over quantity. We wait for the right conditions."
    )

# ── Weekly digest ─────────────────────────────────────────────

def card_weekly_digest(stats, version):
    """Sunday evening weekly summary."""
    btts_leaders  = stats.get("btts_leaders", [])
    cs_leaders    = stats.get("cs_leaders", [])
    scoring_runs  = stats.get("scoring_streaks", [])

    btts_lines  = "\n".join(f"  {t['team']}: {int(t['btts_rate']*100)}%" for t in btts_leaders[:5])
    cs_lines    = "\n".join(f"  {t['team']}: {int(t['cs_rate']*100)}%" for t in cs_leaders[:5])
    streak_lines = "\n".join(f"  {t['team']}: scored in {t['streak']} straight" for t in scoring_runs[:3])

    msg = (
        "📊 *Weekly PL Stats Digest*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "⚽ *BTTS leaders (last 8 games)*\n"
        f"{btts_lines}\n\n"
        "🔒 *Clean sheet leaders (last 8 games)*\n"
        f"{cs_lines}\n\n"
        "🔥 *Current scoring streaks*\n"
        f"{streak_lines}"
        f"{FOOTER.format(version=version)}"
    )
    return msg

# ── VIP announcement ──────────────────────────────────────────

def card_vip_unlock(roi):
    return (
        "🏆 *VIP Tier Now Open*\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"We hit our target: *+{roi['roi_pct']}% ROI over {roi['selections']} selections*.\n\n"
        "The public record speaks for itself. No hype, just data.\n\n"
        "VIP members get:\n"
        "  → Alerts 1 hour earlier\n"
        "  → Full reasoning behind every selection\n"
        "  → Monthly performance reports\n\n"
        "Free channel stays live — always.\n"
        "Link to subscribe: [coming soon]"
    )
