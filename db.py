from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def initialize_database(db_path: str | Path) -> None:
    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TEXT NOT NULL,
                source_input TEXT NOT NULL,
                strategy TEXT NOT NULL,
                benchmark TEXT NOT NULL,
                minimum_score INTEGER NOT NULL,
                stock_count INTEGER NOT NULL,
                run_status TEXT NOT NULL DEFAULT 'success',
                market_status_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS stock_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                rank_position INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT,
                price REAL,
                score INTEGER NOT NULL,
                signal TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                metrics_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                risk_flags_json TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_stock_rankings_run_id
                ON stock_rankings (run_id);

            CREATE INDEX IF NOT EXISTS idx_stock_rankings_ticker
                ON stock_rankings (ticker);
            """
        )
        _ensure_analysis_run_columns(connection)


def _ensure_analysis_run_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(analysis_runs)").fetchall()
    }

    if "run_status" not in columns:
        connection.execute(
            "ALTER TABLE analysis_runs ADD COLUMN run_status TEXT NOT NULL DEFAULT 'success'"
        )

    if "market_status_json" not in columns:
        connection.execute(
            "ALTER TABLE analysis_runs ADD COLUMN market_status_json TEXT NOT NULL DEFAULT '{}'"
        )


def save_analysis_result(db_path: str | Path, result: dict[str, Any], source_input: str) -> int:
    rankings = result.get("rankings", [])
    target = Path(db_path)

    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO analysis_runs (
                generated_at,
                source_input,
                strategy,
                benchmark,
                minimum_score,
                stock_count,
                run_status,
                market_status_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["generated_at"],
                source_input,
                result["strategy"],
                result["benchmark"],
                result["minimum_score"],
                len(rankings),
                result.get("run_status", "success"),
                json.dumps(result.get("market_status", {}), sort_keys=True),
            ),
        )
        run_id = int(cursor.lastrowid)

        for position, ranking in enumerate(rankings, start=1):
            cursor.execute(
                """
                INSERT INTO stock_rankings (
                    run_id,
                    rank_position,
                    ticker,
                    name,
                    price,
                    score,
                    signal,
                    status,
                    error,
                    metrics_json,
                    reasons_json,
                    risk_flags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    position,
                    ranking["ticker"],
                    ranking.get("name"),
                    ranking.get("price"),
                    ranking["score"],
                    ranking["signal"],
                    ranking["status"],
                    ranking.get("error"),
                    json.dumps(ranking.get("metrics", {}), sort_keys=True),
                    json.dumps(ranking.get("reasons", [])),
                    json.dumps(ranking.get("risk_flags", [])),
                ),
            )

        connection.commit()

    return run_id


def get_recent_runs(db_path: str | Path, limit: int = 5) -> list[dict[str, Any]]:
    target = Path(db_path)
    if not target.exists():
        return []

    with sqlite3.connect(target) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id,
                generated_at,
                source_input,
                strategy,
                benchmark,
                minimum_score,
                stock_count,
                run_status
            FROM analysis_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_latest_rankings(
    db_path: str | Path,
    top: int = 10,
    signal: str | None = None,
) -> list[dict[str, Any]]:
    target = Path(db_path)
    if not target.exists():
        return []

    with sqlite3.connect(target) as connection:
        connection.row_factory = sqlite3.Row
        latest = connection.execute("SELECT MAX(run_id) AS run_id FROM stock_rankings").fetchone()
        if latest is None or latest["run_id"] is None:
            return []

        if signal:
            rows = connection.execute(
                """
                SELECT
                    rank_position,
                    ticker,
                    name,
                    price,
                    score,
                    signal,
                    status,
                    error
                FROM stock_rankings
                WHERE run_id = ? AND signal = ?
                ORDER BY rank_position ASC
                LIMIT ?
                """,
                (latest["run_id"], signal.upper(), top),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    rank_position,
                    ticker,
                    name,
                    price,
                    score,
                    signal,
                    status,
                    error
                FROM stock_rankings
                WHERE run_id = ?
                ORDER BY rank_position ASC
                LIMIT ?
                """,
                (latest["run_id"], top),
            ).fetchall()

    return [dict(row) for row in rows]


def get_latest_run(db_path: str | Path) -> dict[str, Any] | None:
    target = Path(db_path)
    if not target.exists():
        return None

    with sqlite3.connect(target) as connection:
        connection.row_factory = sqlite3.Row
        run_row = connection.execute(
            """
            SELECT
                id,
                generated_at,
                source_input,
                strategy,
                benchmark,
                minimum_score,
                stock_count,
                run_status,
                market_status_json
            FROM analysis_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if run_row is None:
            return None

        ranking_rows = connection.execute(
            """
            SELECT
                rank_position,
                ticker,
                name,
                price,
                score,
                signal,
                status,
                error,
                metrics_json,
                reasons_json,
                risk_flags_json
            FROM stock_rankings
            WHERE run_id = ?
            ORDER BY rank_position ASC
            """,
            (run_row["id"],),
        ).fetchall()

    result = dict(run_row)
    result["market_status"] = json.loads(result.pop("market_status_json", "{}"))
    result["rankings"] = []

    for row in ranking_rows:
        ranking = dict(row)
        ranking["metrics"] = json.loads(ranking.pop("metrics_json", "{}"))
        ranking["reasons"] = json.loads(ranking.pop("reasons_json", "[]"))
        ranking["risk_flags"] = json.loads(ranking.pop("risk_flags_json", "[]"))
        result["rankings"].append(ranking)

    return result
