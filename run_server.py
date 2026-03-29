from __future__ import annotations

import argparse

import uvicorn

from app.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audio Journal FastAPI server")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=arguments.reload or settings.server_reload,
        ws_ping_interval=60.0,
        ws_ping_timeout=300.0,
    )
