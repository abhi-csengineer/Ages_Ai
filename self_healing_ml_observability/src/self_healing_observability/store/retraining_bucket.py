from __future__ import annotations

import json
from datetime import datetime, timezone


class RetrainingBucketStore:
    def __init__(self, db_path: str) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb is required for retraining bucket storage.") from exc

        self._conn = duckdb.connect(database=db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retraining_bucket (
                request_id VARCHAR,
                collected_at TIMESTAMP,
                prompt TEXT,
                response_text TEXT,
                status VARCHAR,
                mmd_drift_score DOUBLE,
                accuracy DOUBLE,
                embedding DOUBLE[],
                metadata JSON
            )
            """
        )

    def insert_rows(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        payload = []
        for row in rows:
            payload.append(
                [
                    str(row.get("request_id", "")),
                    datetime.now(timezone.utc),
                    str(row.get("prompt", "")),
                    str(row.get("response_text", "")),
                    str(row.get("status", "OK")),
                    float(row.get("mmd_drift_score", 0.0)),
                    float(row.get("accuracy", 0.0)),
                    [float(v) for v in row.get("embedding", [])],
                    json.dumps(row.get("metadata", {})),
                ]
            )
        self._conn.executemany(
            """
            INSERT INTO retraining_bucket VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        return len(payload)
