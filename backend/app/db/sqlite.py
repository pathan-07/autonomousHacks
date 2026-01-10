import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.core.settings import settings


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                redacted_text TEXT,
                links_json TEXT,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                confidence TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT,
                created_at INTEGER NOT NULL,
                user_verdict TEXT NOT NULL,
                notes TEXT
            )
            """
        )

        # Exact-match cache for repeated inputs.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_cache (
                input_hash TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                response_json TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_analysis(*, input_hash: str, max_age_seconds: int | None = None) -> dict[str, Any] | None:
    if not input_hash:
        return None

    conn = _connect()
    try:
        row = conn.execute(
            "SELECT created_at, response_json FROM analysis_cache WHERE input_hash = ?",
            (input_hash,),
        ).fetchone()
        if not row:
            return None

        created_at = int(row["created_at"])
        if max_age_seconds is not None:
            if int(time.time()) - created_at > int(max_age_seconds):
                return None

        try:
            data = json.loads(row["response_json"])
        except Exception:
            return None
        return data if isinstance(data, dict) else None
    finally:
        conn.close()


def upsert_cached_analysis(*, input_hash: str, response: dict[str, Any]) -> None:
    if not input_hash:
        return

    payload = json.dumps(response, ensure_ascii=False)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO analysis_cache (input_hash, created_at, response_json)
            VALUES (?, ?, ?)
            ON CONFLICT(input_hash) DO UPDATE SET
                created_at=excluded.created_at,
                response_json=excluded.response_json
            """,
            (input_hash, int(time.time()), payload),
        )
        conn.commit()
    finally:
        conn.close()


def insert_interaction(
    *,
    interaction_id: str,
    redacted_text: str | None,
    links_json: str,
    risk_score: int,
    risk_level: str,
    confidence: str,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO interactions (id, created_at, redacted_text, links_json, risk_score, risk_level, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction_id,
                int(time.time()),
                redacted_text,
                links_json,
                risk_score,
                risk_level,
                confidence,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_feedback(*, interaction_id: str | None, user_verdict: str, notes: str | None) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO feedback (interaction_id, created_at, user_verdict, notes)
            VALUES (?, ?, ?, ?)
            """,
            (interaction_id, int(time.time()), user_verdict, notes),
        )
        conn.commit()
    finally:
        conn.close()


def cleanup_old_interactions() -> None:
    ttl = settings.retention_ttl_seconds
    if ttl <= 0:
        return

    cutoff = int(time.time()) - ttl
    conn = _connect()
    try:
        conn.execute("DELETE FROM interactions WHERE created_at < ?", (cutoff,))
        conn.execute("DELETE FROM analysis_cache WHERE created_at < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()
