from __future__ import annotations

import asyncio
import json

import grpc

from self_healing_observability.security_sidecar.inspector import SidecarPromptInspector
from self_healing_observability.security_sidecar.models import (
    SidecarInspectRequest,
    SidecarInspectResponse,
)


_METHOD = "/aegis.security.Sidecar/InspectPrompt"


def _deserialize_request(raw: bytes) -> dict:
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _serialize_response(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


async def _inspect_prompt(request: dict, inspector: SidecarPromptInspector) -> dict:
    validated = SidecarInspectRequest.model_validate(request)
    prompt = validated.prompt
    request_id = validated.request_id
    metadata = validated.metadata

    result = inspector.inspect(request_id=request_id, prompt=prompt, metadata=metadata if isinstance(metadata, dict) else {})
    response = SidecarInspectResponse(
        request_id=request_id,
        detected=result.detected,
        reason=result.reason,
        similarity=result.similarity,
        redacted_prompt=result.redacted_prompt,
        redaction_count=result.redaction_count,
    )
    return response.model_dump(mode="json")


async def serve(host: str = "0.0.0.0", port: int = 50051) -> None:
    inspector = SidecarPromptInspector()
    server = grpc.aio.server(
        options=(
            ("grpc.max_concurrent_streams", 2048),
            ("grpc.so_reuseport", 1),
        )
    )

    async def handler(request: dict, _context: grpc.aio.ServicerContext) -> dict:
        return await _inspect_prompt(request, inspector)

    method_handler = grpc.aio.unary_unary_rpc_method_handler(
        handler,
        request_deserializer=_deserialize_request,
        response_serializer=_serialize_response,
    )
    generic_handler = grpc.method_handlers_generic_handler(
        "aegis.security.Sidecar",
        {"InspectPrompt": method_handler},
    )
    server.add_generic_rpc_handlers((generic_handler,))

    bind_addr = f"{host}:{port}"
    server.add_insecure_port(bind_addr)
    await server.start()
    print(f"[security-sidecar] gRPC server listening on {bind_addr} method={_METHOD}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
