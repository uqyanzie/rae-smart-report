"""Process-local client-activity tracking for the desktop idle-shutdown watchdog.

The launcher's watchdog reads :func:`idle_seconds` to decide when no browser
client has been seen for long enough that the app can exit. Every HTTP request
touches the clock through the activity middleware in ``app.main``; the SPA keeps
the clock fresh with a periodic ``/api/health`` heartbeat while a tab is open.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_last_activity = time.monotonic()


def touch() -> None:
    """Records a client activity timestamp."""
    global _last_activity
    with _lock:
        _last_activity = time.monotonic()


def idle_seconds() -> float:
    """Seconds elapsed since the most recent :func:`touch`."""
    with _lock:
        return time.monotonic() - _last_activity


def reset() -> None:
    """Restarts the idle clock (also used by tests)."""
    touch()
