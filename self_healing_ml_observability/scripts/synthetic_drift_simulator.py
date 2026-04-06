from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def generate_payload(idx: int, drift: bool, adversarial: bool) -> dict:
    base_a = random.gauss(0.0, 1.0)
    base_b = random.gauss(0.0, 1.0)
    risk = max(0.0, min(1.0, random.random()))

    if drift:
        base_a += random.gauss(2.5, 0.6)
        base_b += random.gauss(-1.8, 0.6)
        risk = min(1.0, risk + 0.35)

    if adversarial:
        base_a = base_a + (3.0 if idx % 2 == 0 else -3.0)

    demographic = "group_a" if idx % 2 == 0 else "group_b"
    observed_label = 1 if risk > 0.55 else 0

    return {
        "request_id": f"sim-{idx}",
        "input_features": {
            "feature_a": base_a,
            "feature_b": base_b,
            "risk_score": risk,
            "latency_ms": random.uniform(5.0, 60.0),
        },
        "embeddings": [random.gauss(0.0, 1.0) + (1.5 if drift else 0.0) for _ in range(24)],
        "demographic_group": demographic,
        "population_id": idx % 2,
        "observed_label": observed_label,
    }


def run(base_url: str, total: int, drift_after: int, adversarial: bool) -> None:
    endpoint = f"{base_url.rstrip('/')}/predict"
    retrain_endpoint = f"{base_url.rstrip('/')}/retrain"

    for i in range(total):
        drift = i >= drift_after
        payload = generate_payload(i, drift=drift, adversarial=adversarial)
        try:
            response = _post_json(endpoint, payload)
            print(
                f"{i:04d} source={response['source']} circuit={response['circuit_state']} "
                f"psi={response['psi_drift_score']:.4f} mmd={response['mmd_drift_score']:.4f} "
                f"bias={response['bias_score']:.4f} top_feature={response.get('top_drift_feature')}"
            )

            if response["circuit_state"] == "open" and i % 20 == 0:
                alert_payload = {
                    "status": "firing",
                    "alerts": [
                        {
                            "status": "firing",
                            "labels": {"alertname": "DriftAlert", "severity": "critical"}
                        }
                    ]
                }
                retrain_resp = _post_json(retrain_endpoint, alert_payload)
                print(f"retrain={retrain_resp}")
        except urllib.error.URLError as exc:
            print(f"request_failed at idx={i}: {exc}")

        time.sleep(0.08)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic drift and perturbation simulator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--total", type=int, default=400)
    parser.add_argument("--drift-after", type=int, default=140)
    parser.add_argument("--adversarial", action="store_true")
    args = parser.parse_args()

    run(base_url=args.base_url, total=args.total, drift_after=args.drift_after, adversarial=args.adversarial)
