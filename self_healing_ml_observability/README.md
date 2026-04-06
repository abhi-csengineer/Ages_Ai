# Self-Healing ML Observability System

Production-grade modular framework for real-time ML observability, drift/bias mitigation, and closed-loop retraining.

## Implemented Components

1. High-performance ingestion layer with Bytewax dataflow and DuckDB in-memory feature store.
2. Advanced detection layer with PSI for tabular drift and MMD for embedding drift.
3. Streaming explainability module with FastSHAP-style approximation to identify top drift feature.
4. Real-time fairness monitoring (Disparate Impact + Equalized Odds) with bias alerting.
5. Numerically stable streaming metrics via Welford's algorithm for latency and monitoring signals.
6. No-label performance estimation with Hui-Walter 2x2x2 contingency tracking.
7. FastAPI circuit breaker that trips on drift or bias and routes traffic to rule-based fallback.
8. Retraining webhook endpoint for Alertmanager-triggered reference-window refresh.
9. Prometheus and Grafana stack for Four Golden Signals plus Drift, Bias, and SHAP panels.
10. Synthetic drift simulator with Gaussian/adversarial perturbation injection.

## Project Structure

```
self_healing_ml_observability/
  requirements.txt
  src/
    main.py
    self_healing_observability/
      api/
      contracts/
      core/
      ingestion/
      monitoring/
      store/
```

## Run API

```bash
pip install -r requirements.txt
uvicorn main:app --app-dir src --reload
```

Optional Bytewax setup for ingestion workers:

```bash
pip install -r requirements-bytewax.txt
```

If Bytewax installation fails in your environment (Rust toolchain requirement), the API remains fully runnable. Bytewax imports are lazy and only required for running ingestion dataflows.

## Example Request

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-001",
    "input_features": {
      "risk_score": 0.72,
      "feature_a": 1.3,
      "feature_b": -0.2,
      "latency_ms": 12.0
    },
    "embeddings": [0.1, -0.2, 0.3, 0.4],
    "demographic_group": "group_a",
    "population_id": 0,
    "observed_label": 1
  }'
```

## Bytewax Ingestion Example

Create a `JsonLogSource` with serialized log records and build flow:

```python
from self_healing_observability.ingestion.bytewax_flow import JsonLogSource, build_dataflow
from self_healing_observability.monitoring.streaming_stats import StreamingStats
from self_healing_observability.store.duckdb_store import DuckDBFeatureStore

source = JsonLogSource(records=["{...json log...}"])
store = DuckDBFeatureStore()
latency_stats = StreamingStats()
flow = build_dataflow(source, store, latency_stats)
```

## Retraining Webhook

```bash
curl -X POST "http://127.0.0.1:8000/retrain" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "alerts": [
      {
        "status": "firing",
        "labels": {"alertname": "DriftAlert", "severity": "critical"}
      }
    ]
  }'
```

## Full Stack (Docker Compose)

```bash
docker compose up --build
```

Services:

- API: http://127.0.0.1:8000
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000 (admin/admin)

## Synthetic Drift Demo

```bash
python scripts/synthetic_drift_simulator.py --total 500 --drift-after 160 --adversarial
```

## Streamlit Control Center

```bash
streamlit run scripts/control_center.py
```

The Control Center includes:

- Executive metrics (Hui-Walter estimated accuracy, current MMD drift)
- Circuit breaker traffic light + SHAP drift reason when tripped
- Active learning queue (top uncertain records) with manual "Label and Approve"
- Embedding drift scatter (UMAP 2D when available)

## Security Sidecar

Prompt-injection defense is implemented as a FastAPI middleware with:

- Tier 1 regex jailbreak detection
- Tier 2 semantic similarity against adversarial templates (lightweight vector encoder)

On detection, the circuit breaker opens immediately with status `SECURITY_ATTACK` and inference traffic is routed to fallback.

## Chaos Engineering Suite

```bash
python scripts/chaos_monkey.py --per-phase 250
```

Phases:

- NORMAL
- DRIFT
- ADVERSARIAL

The script reports breaker trip latency (ms) and retrain webhook firing latency (ms).

## RAG Faithfulness Monitoring

Endpoint:

```bash
curl -X POST "http://127.0.0.1:8000/faithfulness/score" \
  -H "Content-Type: application/json" \
  -d '{"context":"...","answer":"..."}'
```

Prometheus metric: `model_faithfulness_score`

Optional full-model dependencies for HHEM-2.1-Open:

```bash
pip install -r requirements-faithfulness.txt
```

## Grafana Embedding Scatter (Business Charts)

The Prometheus exporter now emits:

- `embedding_x{source=\"reference|live\",request_id=\"...\"}`
- `embedding_y{source=\"reference|live\",request_id=\"...\"}`

Business Charts (ECharts) panel JSON:

- `infra/grafana/dashboards/embedding-scatter-business-charts-panel.json`

Panel behavior:

- Reference points are gray/static.
- Live points are colored and update in real time.
- When `ml_drift_score{method=\"mmd\"} > 0.25`, live points transition to red.

## CI Regression Gate

Quality gate script:

```bash
python scripts/ci_quality_gate.py --metrics-url http://127.0.0.1:8000/metrics
```

Gate policy:

- Fail if `ml_hui_walter_estimated_accuracy < 0.90`
- Fail if `ml_bias_score > 0.10`

GitHub Actions workflow for pull requests:

- `.github/workflows/ml_governance.yml`
