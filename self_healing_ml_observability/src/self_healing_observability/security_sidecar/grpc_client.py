from __future__ import annotations

import json
from typing import Any

import grpc


_METHOD = "/aegis.security.Sidecar/InspectPrompt"


def _serialize_request(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _deserialize_response(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


class GrpcSecuritySidecarClient:
    def __init__(self, target: str) -> None:
        self.target = target
        self._channel = grpc.aio.insecure_channel(target)
        self._inspect_call = self._channel.unary_unary(
            _METHOD,
            request_serializer=_serialize_request,
            response_deserializer=_deserialize_response,
        )

    async def inspect_prompt(
        self,
        request_id: str,
        prompt: str,
        metadata: dict[str, Any] | None = None,
        timeout_s: float = 0.02,
    ) -> dict[str, Any]:
        request = {
            "request_id": request_id,
            "prompt": prompt,
            "metadata": metadata or {},
        }
        return await self._inspect_call(request, timeout=timeout_s)

    async def close(self) -> None:
        await self._channel.close()
