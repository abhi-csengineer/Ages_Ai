from __future__ import annotations

import json
import math
import re
from typing import Any
from urllib import error, parse, request

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

try:
    import plotly.express as px
except ImportError:
    px = None

try:
    import umap  # type: ignore
except ImportError:
    umap = None


def _http_get_json(url: str) -> dict[str, Any]:
    with request.urlopen(url, timeout=4) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=6) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str) -> str:
    with request.urlopen(url, timeout=4) as resp:
        return resp.read().decode("utf-8")


def _extract_prometheus_value(metrics_text: str, metric_name: str, labels: dict[str, str] | None = None) -> float:
    labels = labels or {}
    label_expr = ""
    if labels:
        pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        label_expr = "\\{" + ",".join(re.escape(p) for p in pairs) + "\\}"

    pattern = rf"^{re.escape(metric_name)}{label_expr}\\s+([-+]?\\d*\\.?\\d+(?:[eE][-+]?\\d+)?)$"
    regex = re.compile(pattern, re.MULTILINE)
    match = regex.search(metrics_text)
    if not match:
        return 0.0
    try:
        return float(match.group(1))
    except ValueError:
        return 0.0


def _active_top_drift_feature(metrics_text: str) -> str | None:
    pattern = re.compile(r'^ml_top_drift_feature_score\\{feature="([^"]+)"\\}\\s+([-+]?\\d*\\.?\\d+)$', re.MULTILINE)
    active: str | None = None
    for feature, value in pattern.findall(metrics_text):
        if float(value) > 0.5:
            active = feature
            break
    return active


def _prepare_umap_projection(reference: list[list[float]], detection: list[list[float]]) -> pd.DataFrame:
    points = reference + detection
    labels = (["Reference"] * len(reference)) + (["Live"] * len(detection))

    if not points:
        return pd.DataFrame(columns=["x", "y", "window"])

    mat = np.asarray(points, dtype=float)
    if mat.ndim != 2 or mat.shape[1] == 0:
        return pd.DataFrame(columns=["x", "y", "window"])

    if umap is not None and mat.shape[0] >= 4:
        reducer = umap.UMAP(n_components=2, random_state=42)
        coords = reducer.fit_transform(mat)
    elif mat.shape[1] >= 2:
        coords = mat[:, :2]
    else:
        coords = np.column_stack([mat[:, 0], np.zeros(mat.shape[0])])

    return pd.DataFrame({"x": coords[:, 0], "y": coords[:, 1], "window": labels})


def _traffic_light_html(is_open: bool) -> str:
    color = "#e03131" if is_open else "#2f9e44"
    status = "Fallback Active" if is_open else "Model Active"
    return f"""
    <div style='display:flex;align-items:center;gap:12px;padding:10px;border:1px solid #ddd;border-radius:10px;'>
      <div style='width:20px;height:20px;border-radius:50%;background:{color};box-shadow:0 0 8px {color};'></div>
      <div style='font-weight:600;font-size:16px;'>{status}</div>
    </div>
    """


def render_dashboard() -> None:
    st.set_page_config(page_title="Self-Healing MLOps Control Center", layout="wide")
    st.title("Self-Healing MLOps Control Center")

    api_url = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
    auto_refresh = st.sidebar.slider("Auto-refresh (seconds)", min_value=0, max_value=60, value=10)
    manual_refresh = st.sidebar.button("Refresh now")

    if auto_refresh > 0:
        st.caption(f"Auto-refresh is active every {auto_refresh} seconds.")
        if st_autorefresh is not None:
            st_autorefresh(interval=auto_refresh * 1000, key="control_center_refresh")
        else:
            # Fallback: reload page without raising when streamlit-autorefresh is absent.
            html(
                f"""
                <script>
                  setTimeout(function() {{ window.location.reload(); }}, {auto_refresh * 1000});
                </script>
                """,
                height=0,
            )
    elif manual_refresh:
        st.rerun()

    try:
        metrics_text = _http_get_text(f"{api_url.rstrip('/')}/metrics")
        hui = _http_get_json(f"{api_url.rstrip('/')}/hui-walter")
        queue = _http_get_json(f"{api_url.rstrip('/')}/active-learning/queue?top_k=5&candidate_limit=600")
        emb = _http_get_json(f"{api_url.rstrip('/')}/embedding-snapshot?limit=300")
    except error.URLError as exc:
        st.error(f"Unable to reach API at {api_url}: {exc}")
        return

    estimated_accuracy = float(hui.get("estimated", {}).get("accuracy_model_a", 0.0))
    current_mmd = _extract_prometheus_value(metrics_text, "ml_drift_score", {"method": "mmd"})

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Hui-Walter Estimated Accuracy", f"{estimated_accuracy:.3f}")
    with col2:
        st.metric("Current Drift Magnitude (MMD)", f"{current_mmd:.4f}")

    st.subheader("Live Circuit Status")
    circuit_open = _extract_prometheus_value(metrics_text, "ml_circuit_breaker_open") > 0.5
    st.markdown(_traffic_light_html(circuit_open), unsafe_allow_html=True)

    if circuit_open:
        top_feature = _active_top_drift_feature(metrics_text)
        if top_feature:
            st.warning(
                f"Circuit is OPEN. Streaming SHAP proxy indicates drift pressure is dominated by feature: {top_feature}."
            )
        else:
            st.warning("Circuit is OPEN. No active SHAP feature marker is currently emitted.")

    st.subheader("Human-in-the-Loop: Active Learning Queue")
    items = queue.get("items", [])
    queue_df = pd.DataFrame(items)
    if queue_df.empty:
        st.info("No uncertain records currently available in Detection Window.")
    else:
        queue_df = queue_df.sort_values("uncertainty_score", ascending=False)
        st.dataframe(queue_df, use_container_width=True)

    if st.button("Label and Approve", type="primary"):
        payload = {
            "status": "firing",
            "alerts": [
                {"status": "firing", "labels": {"alertname": "DriftAlert", "severity": "critical"}}
            ],
        }
        try:
            retrain = _http_post_json(f"{api_url.rstrip('/')}/retrain", payload)
            selected = int(retrain.get("selected_rows", 0))
            candidates = int(retrain.get("candidate_rows", 0))
            ratio = float(retrain.get("data_efficiency_ratio", 0.0))
            st.success(
                f"Retraining approved. Promoted {selected}/{candidates} samples "
                f"(efficiency ratio={ratio:.3f})."
            )
        except error.URLError as exc:
            st.error(f"Retrain webhook request failed: {exc}")

    st.subheader("Embedding Space Drift (UMAP 2D)")
    reference = emb.get("reference", [])
    detection = emb.get("detection", [])

    if not reference and not detection:
        st.info("No embedding vectors available yet for projection.")
        return

    proj_df = _prepare_umap_projection(reference, detection)
    if proj_df.empty:
        st.info("Insufficient embedding dimensions for projection.")
        return

    if px is not None:
        fig = px.scatter(
            proj_df,
            x="x",
            y="y",
            color="window",
            title="Reference vs Live Embedding Projection",
            opacity=0.75,
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.scatter_chart(proj_df, x="x", y="y", color="window")

    if umap is None:
        st.caption("UMAP is not installed; showing fallback 2D projection.")


if __name__ == "__main__":
    render_dashboard()
