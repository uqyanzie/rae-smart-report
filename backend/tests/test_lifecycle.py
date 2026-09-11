"""Tests for the client-activity clock backing the desktop idle watchdog."""

from __future__ import annotations

import time

from app.core import lifecycle


def test_touch_resets_idle_clock():
    time.sleep(0.05)
    lifecycle.touch()
    assert lifecycle.idle_seconds() < 0.05


def test_idle_seconds_advances_without_activity():
    lifecycle.touch()
    time.sleep(0.05)
    assert lifecycle.idle_seconds() >= 0.04


def test_reset_restarts_the_clock():
    time.sleep(0.05)
    lifecycle.reset()
    assert lifecycle.idle_seconds() < 0.05


class _FakeServer:
    should_exit = False


def test_idle_watchdog_stops_server(monkeypatch):
    """The watchdog flips ``should_exit`` once the idle timeout elapses."""
    import run

    monkeypatch.setattr(run, "_IDLE_POLL_INTERVAL", 0.01)
    server = _FakeServer()
    run._watch_idle(server, timeout_seconds=0)
    assert server.should_exit is True


def test_tray_and_idle_settings_resolution(monkeypatch):
    from app.core import config

    monkeypatch.setenv("RAE_TRAY", "0")
    assert config._resolve_tray() is False
    monkeypatch.setenv("RAE_TRAY", "1")
    assert config._resolve_tray() is True

    monkeypatch.setenv("RAE_IDLE_SHUTDOWN_SECONDS", "0")
    assert config._resolve_idle_shutdown_seconds() == 0
    monkeypatch.setenv("RAE_IDLE_SHUTDOWN_SECONDS", "45")
    assert config._resolve_idle_shutdown_seconds() == 45
    monkeypatch.setenv("RAE_IDLE_SHUTDOWN_SECONDS", "not-a-number")
    assert config._resolve_idle_shutdown_seconds() == 180
