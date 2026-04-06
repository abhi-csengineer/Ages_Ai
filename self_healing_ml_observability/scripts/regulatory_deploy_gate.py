from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def _read_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _extract_metric(payload: dict[str, Any], candidates: list[str]) -> tuple[str, float] | None:
    for path in candidates:
        value = _coerce_float(_get_nested(payload, path))
        if value is not None:
            return path, value
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Regulatory deployment gate using model metadata.")
    parser.add_argument(
        "--metadata-url",
        required=True,
        help="HTTP URL returning latest model metadata JSON",
    )
    parser.add_argument("--min-accuracy", type=float, default=0.90)
    parser.add_argument("--max-bias", type=float, default=0.10)
    parser.add_argument(
        "--accuracy-path",
        default="",
        help="Optional explicit dot path for accuracy in metadata JSON",
    )
    parser.add_argument(
        "--bias-path",
        default="",
        help="Optional explicit dot path for bias in metadata JSON",
    )
    args = parser.parse_args()

    try:
        metadata = _read_json(args.metadata_url)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"[regulatory-gate] FAIL: unable_to_fetch_metadata: {exc}")
        return 2

    accuracy_candidates = [
        args.accuracy_path,
        "model_metrics.accuracy",
        "metrics.accuracy",
        "governance.accuracy",
        "accuracy",
        "ml_hui_walter_estimated_accuracy",
    ]
    bias_candidates = [
        args.bias_path,
        "model_metrics.bias",
        "metrics.bias",
        "governance.bias",
        "bias",
        "ml_bias_score",
    ]
    accuracy_candidates = [c for c in accuracy_candidates if c]
    bias_candidates = [c for c in bias_candidates if c]

    acc = _extract_metric(metadata, accuracy_candidates)
    bias = _extract_metric(metadata, bias_candidates)

    if acc is None or bias is None:
        print(
            "[regulatory-gate] FAIL: metric_not_found "
            f"accuracy_paths={accuracy_candidates} bias_paths={bias_candidates}"
        )
        return 2

    acc_path, accuracy = acc
    bias_path, bias_score = bias
    print(
        "[regulatory-gate] metadata_ok "
        f"accuracy={accuracy:.4f} (path={acc_path}) "
        f"bias={bias_score:.4f} (path={bias_path})"
    )

    failures: list[str] = []
    if accuracy < args.min_accuracy:
        failures.append(f"accuracy {accuracy:.4f} < {args.min_accuracy:.4f}")
    if bias_score > args.max_bias:
        failures.append(f"bias {bias_score:.4f} > {args.max_bias:.4f}")

    if failures:
        print(f"[regulatory-gate] FAIL: {'; '.join(failures)}")
        return 1

    print("[regulatory-gate] PASS: deployment policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
