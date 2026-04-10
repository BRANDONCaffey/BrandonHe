from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from ai_info_collection.storage import SQLiteStore
from ai_info_collection.ui import create_ui_server


@dataclass(slots=True)
class LaunchConfig:
    db_path: str = "data.db"
    host: str = "127.0.0.1"
    port: int = 8765
    offline_mode: bool = False
    startup_timeout_seconds: float = 5.0


@dataclass(slots=True)
class LaunchResult:
    url: str
    status: str


class FrontendLauncher:
    def __init__(self, config: LaunchConfig) -> None:
        self.config = config
        self.server = None
        self.server_thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def is_running(self) -> bool:
        return self.server is not None and self.server_thread is not None and self.server_thread.is_alive()

    def _wait_until_ready(self) -> None:
        deadline = time.time() + self.config.startup_timeout_seconds
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urlopen(self.url, timeout=0.5) as response:  # nosec B310
                    if response.status == 200:
                        return
            except (URLError, OSError) as exc:
                last_error = exc
                time.sleep(0.1)
        raise RuntimeError(f"Frontend server health check failed for {self.url}") from last_error

    def start(self) -> LaunchResult:
        if self.server is not None:
            return LaunchResult(url=self.url, status="already_running")
        store = SQLiteStore(Path(self.config.db_path))
        store.initialize()
        try:
            self.server = create_ui_server(
                store=store,
                host=self.config.host,
                port=self.config.port,
                offline_mode=self.config.offline_mode,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Cannot start frontend server on {self.config.host}:{self.config.port}. "
                "The port may already be in use."
            ) from exc
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self._wait_until_ready()
        return LaunchResult(url=self.url, status="started")

    def stop(self) -> None:
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        if self.server_thread is not None:
            self.server_thread.join(timeout=2)
        self.server = None
        self.server_thread = None


def run_embedded_frontend_app(config: LaunchConfig | None = None) -> None:
    cfg = config or LaunchConfig()
    try:
        import webview
    except Exception as exc:  # pragma: no cover - depends on host system
        raise RuntimeError(
            "pywebview is required for macOS embedded app launch. "
            "Install with: python -m pip install -e '.[app]'"
        ) from exc

    launcher = FrontendLauncher(cfg)
    started = launcher.start()
    window = webview.create_window(
        title="AI Info Collection",
        url=started.url,
        width=1280,
        height=900,
        min_size=(1000, 680),
        resizable=True,
    )

    def on_window_closed() -> None:
        launcher.stop()

    window.events.closed += on_window_closed
    try:
        webview.start(gui="cocoa")
    finally:
        launcher.stop()


def run_desktop_launcher(config: LaunchConfig | None = None) -> None:
    run_embedded_frontend_app(config=config)
