from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from self_healing_observability.core.metrics import INCIDENT_ALERT_COUNTER


class IncidentContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    psi_score: float = Field(ge=0.0)
    mmd_score: float = Field(ge=0.0)
    bias_score: float = Field(ge=0.0)
    critical_streak: int = Field(ge=0)
    status: str


class IncidentEvent(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: Literal["ml_circuit_breaker", "auto_heal"]
    severity: Literal["warning", "critical"]
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    context: IncidentContext
    event_ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _post_json(url: str, payload: dict) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5):
        return


def _notify_slack(event: IncidentEvent, webhook_url: str) -> None:
    text = (
        f"[{event.severity.upper()}] {event.title}\n"
        f"{event.message}\n"
        f"status={event.context.status} psi={event.context.psi_score:.4f} "
        f"mmd={event.context.mmd_score:.4f} bias={event.context.bias_score:.4f} "
        f"critical_streak={event.context.critical_streak}"
    )
    _post_json(webhook_url, {"text": text})


def _notify_pagerduty(event: IncidentEvent, routing_key: str, events_url: str) -> None:
    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": event.title,
            "severity": event.severity,
            "source": event.source,
            "timestamp": event.event_ts.isoformat(),
            "custom_details": event.model_dump(mode="json"),
        },
    }
    _post_json(events_url, payload)


def notify_incident(event: IncidentEvent) -> None:
    slack_url = os.getenv("AEGIS_SLACK_WEBHOOK_URL", "").strip()
    pagerduty_key = os.getenv("AEGIS_PAGERDUTY_ROUTING_KEY", "").strip()
    pagerduty_url = os.getenv("AEGIS_PAGERDUTY_EVENTS_URL", "https://events.pagerduty.com/v2/enqueue").strip()

    if slack_url:
        try:
            _notify_slack(event, slack_url)
            INCIDENT_ALERT_COUNTER.labels(channel="slack", result="sent").inc()
        except urllib.error.URLError:
            INCIDENT_ALERT_COUNTER.labels(channel="slack", result="failed").inc()

    if pagerduty_key:
        try:
            _notify_pagerduty(event, pagerduty_key, pagerduty_url)
            INCIDENT_ALERT_COUNTER.labels(channel="pagerduty", result="sent").inc()
        except urllib.error.URLError:
            INCIDENT_ALERT_COUNTER.labels(channel="pagerduty", result="failed").inc()
