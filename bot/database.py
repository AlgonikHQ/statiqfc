# ============================================================
# database.py — SQLite setup and all data helpers
# ============================================================

import sqlite3
import json
from datetime import datetime
from config import DB_PATH

# ── Schema ───────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id   TEXT PRIMARY KEY,
    home         TEXT NOT NULL,
    away         TEXT NOT NULL,
    kickoff_utc  TEXT NOT NULL,
    league       TEXT NOT NULL,
    status       TEXT DEFAULT 'SCHEDULED',
    home_score   INTEGER,
    away_score   INTEGER,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS form (
    team            TEXT PRIMARY KEY,
    last5           TEXT,     -- JSON array of W/D/L
    goals_for       REAL,     -- average last 8
    goals_ag        REAL,     -- average last 8
    cs_rate         REAL,     -- clean sheet rate last 8 (all games)
    btts_rate       REAL,     -- BTTS rate last 8 (all games)
    cs_rate_home    REAL,     -- CS rate in home fixtures only
    btts_rate_home  REAL,     -- BTTS rate in home fixtures only
    cs_rate_away    REAL,     -- CS rate in away fixtures only
    btts_rate_away  REAL,     -- BTTS rate in away fixtures only
    xg_for          REAL,     -- xG for last 5 (Understat)
    xg_ag           REAL,     -- xG against last 5
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS h2h (
    fixture_id   TEXT,
    home         TEXT,
    away         TEXT,
    date         TEXT,
    home_score   INTEGER,
    away_score   INTEGER,
    PRIMARY KEY (home, away, date)
);

CREATE TABLE IF NOT EXISTS odds (
    fixture_id   TEXT PRIMARY KEY,
    home_odds    REAL,
    draw_odds    REAL,
    away_odds    REAL,
    btts_yes     REAL,
    over25       REAL,
    pulled_at    TEXT
);

CREATE TABLE IF NOT EXISTS selections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id   TEXT,
    home         TEXT,
    away         TEXT,
    market       TEXT NOT NULL,     -- e.g. BTTS, CS_HOME, OVER25
    is_builder   INTEGER DEFAULT 0, -- 1 = builder single (0.5u), 0 = standard (1u)
    stake        REAL,
    odds         REAL,
    potential    REAL,
    result       TEXT,              -- WIN / LOSS / VOID / NULL=pending
    profit       REAL,
    created_at   TEXT,
    settled_at   TEXT,
    reasoning    TEXT               -- brief stat basis shown publicly
);

CREATE TABLE IF NOT EXISTS roi_snapshot (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    selections   INTEGER,
    wins         INTEGER,
    losses       INTEGER,
    voids        INTEGER,
    total_staked REAL,
    total_return REAL,
    net_pl       REAL,
    roi_pct      REAL,
    updated_at   TEXT
);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    migrate_db()

def migrate_db():
    """Add columns introduced after v1.0 — safe to run repeatedly."""
    conn = get_conn()
    new_cols = [
        ("form", "cs_rate_home",   "REAL"),
        ("form", "btts_rate_home", "REAL"),
        ("form", "cs_rate_away",   "REAL"),
        ("form", "btts_rate_away", "REAL"),
    ]
    for table, col, col_type in new_cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            print(f"  [DB MIGRATE] Added {table}.{col}")
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()


# ── Selections ───────────────────────────────────────────────

def log_selection(fixture_id, home, away, market, odds, is_builder=False, reasoning=""):
    from config import STAKE_STANDARD, STAKE_BUILDER
    stake     = STAKE_BUILDER if is_builder else STAKE_STANDARD
    potential = round(stake * odds, 2)
    conn = get_conn()
    conn.execute("""
        INSERT INTO selections
        (fixture_id, home, away, market, is_builder, stake, odds, potential, created_at, reasoning)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (fixture_id, home, away, market, int(is_builder),
          stake, odds, potential, datetime.utcnow().isoformat(), reasoning))
    conn.commit()
    conn.close()

def settle_selection(selection_id, result, final_home, final_away):
    conn  = get_conn()
    row   = conn.execute("SELECT * FROM selections WHERE id=?", (selection_id,)).fetchone()
    if not row:
        conn.close()
        return
    stake = row["stake"]
    odds  = row["odds"]
    if result == "WIN":
        profit = round(stake * odds - stake, 2)
    elif result == "LOSS":
        profit = -stake
    else:
        profit = 0.0
    conn.execute("""
        UPDATE selections
        SET result=?, profit=?, settled_at=?
        WHERE id=?
    """, (result, profit, datetime.utcnow().isoformat(), selection_id))
    conn.commit()
    conn.close()
    refresh_roi()

def get_pending_selections():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM selections WHERE result IS NULL ORDER BY created_at"
    ).fetchall()
    conn.close()
    return rows

def count_today_alerts():
    today = datetime.utcnow().date().isoformat()
    conn  = get_conn()
    n     = conn.execute(
        "SELECT COUNT(*) FROM selections WHERE created_at LIKE ?", (today + "%",)
    ).fetchone()[0]
    conn.close()
    return n

# ── ROI ──────────────────────────────────────────────────────

def refresh_roi():
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT * FROM selections WHERE result IN ('WIN','LOSS','VOID')"
    ).fetchall()
    wins    = sum(1 for r in rows if r["result"] == "WIN")
    losses  = sum(1 for r in rows if r["result"] == "LOSS")
    voids   = sum(1 for r in rows if r["result"] == "VOID")
    staked  = sum(r["stake"]  for r in rows if r["result"] != "VOID")
    returned = sum(r["stake"] * r["odds"] for r in rows if r["result"] == "WIN")
    net_pl  = round(returned - staked, 2)
    roi_pct = round((net_pl / staked * 100), 2) if staked > 0 else 0.0
    conn.execute("""
        INSERT INTO roi_snapshot
        (selections, wins, losses, voids, total_staked, total_return, net_pl, roi_pct, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (len(rows), wins, losses, voids, round(staked,2),
          round(returned,2), net_pl, roi_pct, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return roi_pct

def get_latest_roi():
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM roi_snapshot ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def export_roi_json(path="/root/statiq/dashboard/roi.json"):
    """Write latest ROI to JSON — dashboard reads this file."""
    roi = get_latest_roi()
    if not roi:
        return
    # add all selections history for the dashboard table
    conn = get_conn()
    sels = conn.execute(
        "SELECT * FROM selections ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    roi["selections_log"] = [dict(s) for s in sels]
    with open(path, "w") as f:
        json.dump(roi, f, indent=2)

# ── Daily P&L ────────────────────────────────────────────────

def refresh_daily_pnl(date_iso=None):
    """Compute and store today's P&L into daily_pnl table."""
    if date_iso is None:
        date_iso = datetime.utcnow().date().isoformat()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT result, stake, odds, profit
        FROM selections
        WHERE substr(created_at, 1, 10) = ?
    """, (date_iso,))
    rows = cur.fetchall()

    edges    = len(rows)
    wins     = sum(1 for r in rows if r["result"] == "WIN")
    losses   = sum(1 for r in rows if r["result"] == "LOSS")
    pushes   = sum(1 for r in rows if r["result"] == "PUSH")
    voids    = sum(1 for r in rows if r["result"] == "VOID")
    staked   = round(sum(r["stake"] for r in rows if r["result"] not in ("VOID", None)), 2)
    returned = round(sum(r["stake"] * r["odds"] for r in rows if r["result"] == "WIN"), 2)
    pnl      = round(returned - staked, 2)
    roi_pct  = round((pnl / staked * 100), 2) if staked > 0 else 0.0

    conn.execute("""
        INSERT OR REPLACE INTO daily_pnl
        (date, edges_placed, wins, losses, pushes, voids,
         stake_units, return_units, pnl_units, daily_roi_pct, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date_iso, edges, wins, losses, pushes, voids,
          staked, returned, pnl, roi_pct,
          datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {
        "date": date_iso, "edges": edges, "wins": wins, "losses": losses,
        "pushes": pushes, "voids": voids, "staked": staked,
        "returned": returned, "pnl": pnl, "roi_pct": roi_pct
    }


def get_daily_pnl(date_iso=None):
    """Get today's (or specified date's) P&L snapshot."""
    if date_iso is None:
        date_iso = datetime.utcnow().date().isoformat()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM daily_pnl WHERE date = ?", (date_iso,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_alltime_stats():
    """Aggregate all-time stats from daily_pnl."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            SUM(edges_placed) AS total_edges,
            SUM(wins) AS total_wins,
            SUM(losses) AS total_losses,
            SUM(pushes) AS total_pushes,
            SUM(voids) AS total_voids,
            SUM(stake_units) AS total_staked,
            SUM(return_units) AS total_returned,
            SUM(pnl_units) AS total_pnl,
            COUNT(*) AS active_days
        FROM daily_pnl
    """)
    row = dict(cur.fetchone())
    conn.close()
    if row["total_staked"] and row["total_staked"] > 0:
        row["roi_pct"] = round((row["total_pnl"] / row["total_staked"] * 100), 2)
    else:
        row["roi_pct"] = 0.0
    # Replace None with 0 for safe display
    for k in ("total_edges","total_wins","total_losses","total_pushes","total_voids","total_staked","total_returned","total_pnl","active_days"):
        if row.get(k) is None:
            row[k] = 0
    return row

