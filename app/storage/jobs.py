from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app import config


class JobStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path), timeout=30, check_same_thread=False)

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at)")
            conn.commit()

    def set(self, job_id: str, data: Dict[str, Any]) -> None:
        now = time.time()
        payload = json.dumps(data, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (job_id, payload, now, now),
            )
            conn.commit()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT data, updated_at FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        updated_at = float(row[1])
        if data.get("status") == "processing" and time.time() - updated_at > config.JOB_STALE_SECONDS:
            return {
                "status": "error",
                "error_message": "Proses AI terhenti atau terlalu lama. Server mungkin overload atau workflow eksternal timeout.",
            }
        return data

    def cleanup(self) -> int:
        threshold = time.time() - config.JOB_TTL_SECONDS
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM jobs WHERE updated_at < ?", (threshold,))
            conn.commit()
            return int(cur.rowcount or 0)


job_store = JobStore(config.JOB_DB_PATH)
