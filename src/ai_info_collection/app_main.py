from __future__ import annotations

import argparse

from ai_info_collection.frontend_launch import LaunchConfig, run_embedded_frontend_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch embedded AI Info Collection frontend app")
    parser.add_argument("--db-path", default="data.db", help="SQLite database path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--offline", action="store_true", help="Render UI with offline-first hints")
    parser.add_argument("--startup-timeout", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = LaunchConfig(
        db_path=args.db_path,
        host=args.host,
        port=args.port,
        offline_mode=args.offline,
        startup_timeout_seconds=args.startup_timeout,
    )
    run_embedded_frontend_app(config=config)
    return 0
