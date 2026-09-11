"""System-tray control surface for the packaged desktop app (Windows-first).

Provides an icon whose default action reopens the dashboard in the browser and
whose ``Exit`` item triggers a graceful uvicorn shutdown. Imported lazily by
``backend/run.py`` so development runs and headless API-only deployments never
require ``pystray``/``Pillow``.

The tray message loop must own the calling (main) thread on some platforms, so
``run.py`` starts uvicorn on a worker thread and calls :func:`run_tray` here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def _build_icon_image() -> Any:
    """Draws the app mark at runtime (no bundled asset dependency)."""
    from PIL import Image, ImageDraw

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(79, 70, 229, 255))
    draw.ellipse((22, 22, size - 22, size - 22), fill=(255, 255, 255, 255))
    return image


def run_tray(
    server: Any,
    base_url: str,
    open_dashboard: Callable[[str], None],
) -> None:
    """Runs the tray icon loop on the calling thread until the user exits.

    ``server`` is the running ``uvicorn.Server``; setting ``should_exit`` lets
    its serve loop wind down gracefully (lifespan shutdown disposes the engine).
    """
    import pystray

    def on_open(icon: Any, item: Any) -> None:
        open_dashboard(base_url)

    def on_exit(icon: Any, item: Any) -> None:
        logger.info("Exit selected from tray; stopping server.")
        server.should_exit = True
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open, default=True),
        pystray.MenuItem("Exit", on_exit),
    )
    icon = pystray.Icon("RAESmartReport", _build_icon_image(), "RAE Smart Report", menu)
    logger.info("System tray ready.")
    icon.run()
