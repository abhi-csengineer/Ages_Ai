from __future__ import annotations

import argparse
import asyncio

from self_healing_observability.security_sidecar.grpc_service import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Aegis gRPC Security Sidecar.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=50051)
    args = parser.parse_args()

    asyncio.run(serve(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
