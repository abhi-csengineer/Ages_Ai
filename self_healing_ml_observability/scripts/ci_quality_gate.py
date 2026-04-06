from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request


def _read_metrics(url: str) -> str:
    with urllib.request.urlopen(url, timeout=8) as resp:
        return resp.read().decode("utf-8")


def _extract_scalar(metrics_text: str, metric_name: str) -> float:
    pattern = re.compile(
        rf"^{re.escape(metric_name)}\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)$",
        flags=re.MULTILINE,
    )
    match = pattern.search(metrics_text)
    if not match:
        raise ValueError(f"metric_not_found:{metric_name}")
    return float(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description="CI quality gate based on observability metrics.")
    parser.add_argument(
        "--metrics-url",
        default="http://127.0.0.1:8000/metrics",
        help="Prometheus metrics endpoint URL",
    )
    parser.add_argument("--min-accuracy", type=float, default=0.90)
    parser.add_argument("--max-bias", type=float, default=0.10)
    args = parser.parse_args()

    try:
        metrics_text = _read_metrics(args.metrics_url)
        accuracy = _extract_scalar(metrics_text, "ml_hui_walter_estimated_accuracy")
        bias = _extract_scalar(metrics_text, "ml_bias_score")
    except (urllib.error.URLError, ValueError) as exc:
        print(f"[ml-governance] failed_to_read_metrics: {exc}")
        return 2

    print(f"[ml-governance] estimated_accuracy={accuracy:.4f} bias_score={bias:.4f}")

    if accuracy < args.min_accuracy:
        print(
            f"[ml-governance] FAIL: accuracy {accuracy:.4f} below threshold {args.min_accuracy:.4f}"
        )
        return 1

    if bias > args.max_bias:
        print(f"[ml-governance] FAIL: bias {bias:.4f} above threshold {args.max_bias:.4f}")
        return 1

    print("[ml-governance] PASS: quality gate satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
