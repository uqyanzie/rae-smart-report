"""Runtime entrypoint for both development and packaged (PyInstaller) modes.

Starts uvicorn programmatically with frozen-safe loop/protocol choices, redirects
stdout/stderr to a writable log when no console is attached, and opens the default
browser once ``/api/health`` responds. In a frozen build it also shows a system
tray icon (Open Dashboard / Exit) and runs an idle watchdog that shuts the server
down once no browser client has been seen for ``RAE_IDLE_SHUTDOWN_SECONDS``.
This module is the PyInstaller entry script referenced by ``packaging.spec``.

Environment overrides (all optional): ``RAE_HOST``, ``RAE_PORT``,
``RAE_SKIP_BROWSER``, ``RAE_TRAY`` (auto/1/0; default: frozen builds only),
``RAE_IDLE_SHUTDOWN_SECONDS`` (default 180; 0 disables auto-exit).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from app.core import lifecycle
from app.core.config import Settings, get_settings, get_writable_app_dir
from app.main import app

_HEALTH_PATH = "/api/health"
_SERVER_START_TIMEOUT = 20.0
_IDLE_POLL_INTERVAL = 10.0


def _redirect_streams_to_log() -> None:
    """Points a windowed (no-console) process's missing stdout/stderr at a log file.

    PyInstaller ``--windowed`` builds run with ``sys.stdout``/``sys.stderr`` set
    to ``None``; libraries that write to them would otherwise raise. Logging
    itself is handled by :func:`_configure_logging`, which always writes to the
    log file so the tray/idle lifecycle stays observable even when this is a
    no-op (e.g. when only one of the streams is redirected).
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_file = get_writable_app_dir() / "rae_smart_report.log"
    stream = open(log_file, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _configure_logging() -> None:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    file_handler = logging.FileHandler(
        get_writable_app_dir() / "rae_smart_report.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


def _display_host(settings: Settings) -> str:
    return "127.0.0.1" if settings.host in ("0.0.0.0", "::") else settings.host


def _open_dashboard(base_url: str) -> None:
    webbrowser.open(base_url)


def _open_browser_when_ready(settings: Settings) -> None:
    """Polls the health endpoint until the server is alive, then opens the browser."""
    host = _display_host(settings)
    base_url = f"http://{host}:{settings.port}"
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}{_HEALTH_PATH}", timeout=1) as response:
                if response.status == 200:
                    _open_dashboard(base_url)
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.3)
    logging.getLogger(__name__).warning("Health probe timed out; opening browser anyway.")
    _open_dashboard(base_url)


def _watch_idle(server: uvicorn.Server, timeout_seconds: int) -> None:
    """Stops the server once no client activity has been seen for the timeout."""
    logger = logging.getLogger(__name__)
    while not server.should_exit:
        time.sleep(_IDLE_POLL_INTERVAL)
        if server.should_exit:
            return
        idle = lifecycle.idle_seconds()
        if idle >= timeout_seconds:
            logger.info("No client activity for %.0fs; auto-shutting down.", idle)
            server.should_exit = True
            return


def _build_server(settings: Settings) -> uvicorn.Server:
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,  # keep the root file/stream handlers configured above
        loop="asyncio",  # no uvloop dependency; deterministic when frozen
        http="h11",  # pure-python protocol; no httptools binary needed
        ws="none",  # the SPA is request/response only
        access_log=False,
    )
    return uvicorn.Server(config)


def _run_with_tray(settings: Settings, server: uvicorn.Server, base_url: str) -> None:
    """Serves on a worker thread while the tray owns the main thread."""
    logger = logging.getLogger(__name__)
    runner = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    runner.start()

    deadline = time.monotonic() + _SERVER_START_TIMEOUT
    while not server.started and runner.is_alive() and time.monotonic() < deadline:
        time.sleep(0.1)

    if not server.started:
        logger.error("Server failed to start; not showing the tray icon.")
        server.should_exit = True
        runner.join(timeout=5)
        return

    try:
        from app.core.tray import run_tray

        run_tray(server, base_url, _open_dashboard)
    except Exception:  # pragma: no cover - platform/dependency specific
        logger.exception("Tray unavailable; serving until the process is stopped.")
        try:
            runner.join()
        except KeyboardInterrupt:
            pass
    finally:
        server.should_exit = True
        runner.join(timeout=10)


def _run_headless(server: uvicorn.Server) -> None:
    try:
        server.run()
    except KeyboardInterrupt:
        server.should_exit = True


def main() -> None:
    _redirect_streams_to_log()
    _configure_logging()

    settings = get_settings()
    base_url = f"http://{_display_host(settings)}:{settings.port}"
    server = _build_server(settings)

    if settings.idle_shutdown_seconds > 0:
        threading.Thread(
            target=_watch_idle,
            args=(server, settings.idle_shutdown_seconds),
            name="idle-watchdog",
            daemon=True,
        ).start()

    if not settings.skip_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(settings,),
            name="browser-launcher",
            daemon=True,
        ).start()

    if settings.tray:
        _run_with_tray(settings, server, base_url)
    else:
        _run_headless(server)


if __name__ == "__main__":
    main()
