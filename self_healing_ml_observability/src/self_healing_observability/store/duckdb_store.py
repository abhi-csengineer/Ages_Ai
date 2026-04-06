from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any
from typing import Any

from self_healing_observability.contracts.schemas import InferenceLog


class DuckDBFeatureStore:
    """In-memory DuckDB store with reference/detection sliding windows."""

    def __init__(self, db_path: str = ":memory:", detection_window_size: int = 2000) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError(
                "duckdb is required for DuckDBFeatureStore. Install dependencies with `pip install -r requirements.txt`."
            ) from exc

        self._conn = duckdb.connect(database=db_path)
        self._lock = threading.Lock()
        self.detection_window_size = detection_window_size
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_logs (
                    request_id VARCHAR,
                    event_ts TIMESTAMP,
                    window_type VARCHAR,
                    input_features JSON,
                    embeddings DOUBLE[],
                    softmax_probs DOUBLE[],
                    confidence DOUBLE,
                    uncertainty DOUBLE,
                    latency_ms DOUBLE,
                    demographic_group VARCHAR,
                    observed_label INTEGER
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_values (
                    request_id VARCHAR,
                    event_ts TIMESTAMP,
                    window_type VARCHAR,
                    feature_name VARCHAR,
                    feature_value DOUBLE
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_values (
                    request_id VARCHAR,
                    event_ts TIMESTAMP,
                    window_type VARCHAR,
                    embedding DOUBLE[]
                )
                """
            )

    def insert_log(
        self,
        log: InferenceLog,
        window_type: str,
        confidence: float,
        uncertainty: float,
        latency_ms: float,
    ) -> None:
        now = log.event_ts if log.event_ts else datetime.now(timezone.utc)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO inference_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    log.request_id,
                    now,
                    window_type,
                    log.input_features,
                    log.embeddings,
                    log.softmax_probs,
                    confidence,
                    uncertainty,
                    latency_ms,
                    log.demographic_group,
                    log.observed_label,
                ],
            )

            numeric_rows = []
            for key, value in log.input_features.items():
                if isinstance(value, (int, float)):
                    numeric_rows.append(
                        [
                            log.request_id,
                            now,
                            window_type,
                            key,
                            float(value),
                        ]
                    )

            if numeric_rows:
                self._conn.executemany(
                    """
                    INSERT INTO feature_values VALUES (?, ?, ?, ?, ?)
                    """,
                    numeric_rows,
                )

            if log.embeddings:
                self._conn.execute(
                    """
                    INSERT INTO embedding_values VALUES (?, ?, ?, ?)
                    """,
                    [log.request_id, now, window_type, log.embeddings],
                )

            if window_type == "detection":
                self._enforce_detection_window_cap()

    def _enforce_detection_window_cap(self) -> None:
        self._conn.execute(
            """
            DELETE FROM inference_logs
            WHERE window_type = 'detection'
              AND request_id IN (
                SELECT request_id
                FROM inference_logs
                WHERE window_type = 'detection'
                ORDER BY event_ts DESC
                OFFSET ?
              )
            """,
            [self.detection_window_size],
        )
        self._conn.execute(
            """
            DELETE FROM feature_values
            WHERE window_type = 'detection'
              AND request_id NOT IN (
                SELECT request_id FROM inference_logs WHERE window_type = 'detection'
              )
            """
        )
        self._conn.execute(
            """
            DELETE FROM embedding_values
            WHERE window_type = 'detection'
              AND request_id NOT IN (
                SELECT request_id FROM inference_logs WHERE window_type = 'detection'
              )
            """
        )

    def list_numeric_features(self, window_type: str) -> list[str]:
        with self._lock:
            result = self._conn.execute(
                """
                SELECT DISTINCT feature_name
                FROM feature_values
                WHERE window_type = ?
                ORDER BY feature_name
                """,
                [window_type],
            ).fetchall()
        return [row[0] for row in result]

    def feature_distribution(self, window_type: str, feature_name: str) -> list[float]:
        with self._lock:
            result = self._conn.execute(
                """
                SELECT feature_value
                FROM feature_values
                WHERE window_type = ? AND feature_name = ?
                ORDER BY event_ts ASC
                """,
                [window_type, feature_name],
            ).fetchall()
        return [float(row[0]) for row in result]

    def count_logs(self, window_type: str) -> int:
        with self._lock:
            result = self._conn.execute(
                """
                SELECT COUNT(*)
                FROM inference_logs
                WHERE window_type = ?
                """,
                [window_type],
            ).fetchone()
        return int(result[0]) if result else 0

    def detection_records(self, limit: int = 5000) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT request_id, softmax_probs, embeddings
                FROM inference_logs
                WHERE window_type = 'detection'
                ORDER BY event_ts DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [
            {
                "request_id": str(row[0]),
                "softmax_probs": list(row[1]) if row[1] is not None else [],
                "embeddings": list(row[2]) if row[2] is not None else [],
            }
            for row in rows
        ]

    def promote_detection_ids_to_reference(self, request_ids: list[str]) -> int:
        if not request_ids:
            return 0

        placeholders = ", ".join(["?"] * len(request_ids))
        with self._lock:
            self._conn.execute("DELETE FROM inference_logs WHERE window_type = 'reference'")
            self._conn.execute("DELETE FROM feature_values WHERE window_type = 'reference'")
            self._conn.execute("DELETE FROM embedding_values WHERE window_type = 'reference'")

            self._conn.execute(
                f"""
                INSERT INTO inference_logs
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    input_features,
                    embeddings,
                    softmax_probs,
                    confidence,
                    uncertainty,
                    latency_ms,
                    demographic_group,
                    observed_label
                FROM inference_logs
                WHERE window_type = 'detection'
                  AND request_id IN ({placeholders})
                """,
                request_ids,
            )

            self._conn.execute(
                """
                INSERT INTO feature_values
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    feature_name,
                    feature_value
                FROM feature_values
                WHERE window_type = 'detection'
                  AND request_id IN (
                    SELECT request_id FROM inference_logs WHERE window_type = 'reference'
                  )
                """
            )

            self._conn.execute(
                """
                INSERT INTO embedding_values
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    embedding
                FROM embedding_values
                WHERE window_type = 'detection'
                  AND request_id IN (
                    SELECT request_id FROM inference_logs WHERE window_type = 'reference'
                  )
                """
            )

            rows = self._conn.execute(
                """
                SELECT COUNT(*) FROM inference_logs WHERE window_type = 'reference'
                """
            ).fetchone()
            return int(rows[0]) if rows else 0

    def copy_detection_to_reference(self, max_rows: int = 1000) -> int:
        with self._lock:
            self._conn.execute("DELETE FROM inference_logs WHERE window_type = 'reference'")
            self._conn.execute("DELETE FROM feature_values WHERE window_type = 'reference'")
            self._conn.execute("DELETE FROM embedding_values WHERE window_type = 'reference'")

            self._conn.execute(
                """
                INSERT INTO inference_logs
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    input_features,
                    embeddings,
                    softmax_probs,
                    confidence,
                    uncertainty,
                    latency_ms,
                    demographic_group,
                    observed_label
                FROM (
                    SELECT *
                    FROM inference_logs
                    WHERE window_type = 'detection'
                    ORDER BY event_ts DESC
                    LIMIT ?
                ) t
                """,
                [max_rows],
            )

            self._conn.execute(
                """
                INSERT INTO feature_values
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    feature_name,
                    feature_value
                FROM feature_values
                WHERE window_type = 'detection'
                  AND request_id IN (
                    SELECT request_id
                    FROM inference_logs
                    WHERE window_type = 'reference'
                  )
                """
            )

            self._conn.execute(
                """
                INSERT INTO embedding_values
                SELECT
                    request_id,
                    event_ts,
                    'reference' AS window_type,
                    embedding
                FROM embedding_values
                WHERE window_type = 'detection'
                  AND request_id IN (
                    SELECT request_id
                    FROM inference_logs
                    WHERE window_type = 'reference'
                  )
                """
            )

            rows = self._conn.execute(
                """
                SELECT COUNT(*) FROM inference_logs WHERE window_type = 'reference'
                """
            ).fetchone()
            return int(rows[0]) if rows else 0

    def feature_mean_map(self, window_type: str) -> dict[str, float]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT feature_name, AVG(feature_value)
                FROM feature_values
                WHERE window_type = ?
                GROUP BY feature_name
                """,
                [window_type],
            ).fetchall()
        return {str(r[0]): float(r[1]) for r in rows}

    def embeddings_matrix(self, window_type: str, limit: int = 1024) -> list[list[float]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT embedding
                FROM embedding_values
                WHERE window_type = ?
                ORDER BY event_ts DESC
                LIMIT ?
                """,
                [window_type, limit],
            ).fetchall()
        return [list(r[0]) for r in rows if r[0] is not None]

    def embedding_points(self, window_type: str, limit: int = 300) -> list[dict[str, float | str]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT request_id, embedding
                FROM embedding_values
                WHERE window_type = ?
                ORDER BY event_ts DESC
                LIMIT ?
                """,
                [window_type, limit],
            ).fetchall()

        points: list[dict[str, float | str]] = []
        for request_id, embedding in rows:
            if embedding is None or len(embedding) == 0:
                continue
            x = float(embedding[0])
            y = float(embedding[1]) if len(embedding) > 1 else 0.0
            points.append({"request_id": str(request_id), "x": x, "y": y})
        return points

    def truncate_window(self, window_type: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM inference_logs WHERE window_type = ?", [window_type])
            self._conn.execute("DELETE FROM feature_values WHERE window_type = ?", [window_type])
            self._conn.execute("DELETE FROM embedding_values WHERE window_type = ?", [window_type])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
