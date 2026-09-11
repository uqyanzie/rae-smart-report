"""Packaged end-to-end smoke test for the RAESmartReport desktop executable.

Launches ``dist/RAE-Smart-Report.exe``, waits for ``/api/health``, then runs the
full pipeline against the bundled SPA/API with the two golden sample files:

    ingest -> profile -> transform -> unreported -> export

It asserts the frozen app resolves ``frontend/dist`` and ``data/sku_mapping.json``
from ``sys._MEIPASS``, persists to the writable app dir
(``%LOCALAPPDATA%/RAESmartReport``), reproduces the golden Shopee/TikTok totals,
and emits the ``Produk`` + ``Tidak Terlaporkan`` sheets.

Usage:
    python scripts/smoke_test.py [--exe PATH] [--port 8123] [--keep-db] [--tray] [--idle-exit]

``--tray`` runs the packaged app through the system-tray startup path instead of
headless; ``--idle-exit`` verifies only the idle watchdog auto-shutdown.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import httpx
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXE = ROOT / "dist" / "RAE-Smart-Report.exe"

GOLDEN_SHOPEE = {"qty": 6_910, "revenue": 525_973_986}
GOLDEN_TIKTOK = {"qty": 11_575, "revenue": 658_458_817}
# Proves the Lazada adapter resolves its SKUs from the bundled
# data/sku_mapping.json inside sys._MEIPASS.
GOLDEN_LAZADA = {"qty": 49, "revenue": 4_533_088}
EXPECTED_SHEETS = {
    "Produk S",
    "Produk T",
    "Produk Laz",
    "Produk 2 S",
    "Produk 2 T",
    "Tidak Terlaporkan S",
    "Tidak Terlaporkan T",
    "Tidak Terlaporkan Laz",
}


def _log(message: str) -> None:
    print(f"[smoke] {message}", flush=True)


def _fail(message: str) -> None:
    raise SystemExit(f"[smoke] FAIL: {message}")


def _health_ok(base_url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _wait_for_health(base_url: str, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _health_ok(base_url):
            return
        time.sleep(0.5)
    _fail(f"server did not answer {base_url}/api/health within {timeout:.0f}s")


def _build_env(port: int, *, tray: bool, idle_seconds: int = 0) -> dict:
    env = dict(os.environ)
    env["RAE_SKIP_BROWSER"] = "1"
    env["RAE_PORT"] = str(port)
    env["RAE_TRAY"] = "1" if tray else "0"
    env["RAE_IDLE_SHUTDOWN_SECONDS"] = str(idle_seconds)
    env.pop("RAE_DATABASE_URL", None)
    env.pop("RAE_FRONTEND_DIST", None)
    return env


def _launch(exe: Path, env: dict) -> subprocess.Popen:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        [str(exe)],
        env=env,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _check_idle_exit(exe: Path, port: int) -> None:
    """Proves the watchdog auto-shuts the packaged app down once idle."""
    base_url = f"http://127.0.0.1:{port}"
    proc = _launch(exe, _build_env(port, tray=False, idle_seconds=3))
    try:
        _wait_for_health(base_url)
        _log("idle check: server up; waiting for auto-exit")
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                _log("idle check: server auto-exited as expected")
                return
            time.sleep(0.5)
        _fail("server did not auto-exit after the idle grace period")
    finally:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _ingest(client: httpx.Client, path: Path) -> dict:
    with path.open("rb") as handle:
        response = client.post(
            "/api/ingest",
            files={
                "file": (
                    path.name,
                    handle.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    response.raise_for_status()
    return response.json()


def _run_platform(
    client: httpx.Client, path: Path, period: tuple[str, str], expected: dict
) -> str:
    ingested = _ingest(client, path)
    profile = client.post(
        "/api/profile", json={"fileId": ingested["fileId"], "activeSheet": ingested["activeSheet"]}
    )
    profile.raise_for_status()
    profiled = profile.json()
    if profiled["platform"] == "UNKNOWN":
        _fail(f"{path.name}: platform profiled as UNKNOWN")

    transform = client.post(
        "/api/transform",
        json={
            "fileId": ingested["fileId"],
            "activeSheet": ingested["activeSheet"],
            "platform": profiled["platform"],
            "periodStart": period[0],
            "periodEnd": period[1],
            "columnMapping": profiled["columnMapping"],
            "parentRowRule": profiled["parentRowRule"],
            "cleaningRules": profiled["suggestedCleaningRules"],
            "saveAsTemplate": True,
        },
    )
    transform.raise_for_status()
    result = transform.json()

    if result["reportedTotalQty"] != expected["qty"]:
        _fail(
            f"{path.name}: reportedTotalQty {result['reportedTotalQty']} != golden {expected['qty']}"
        )
    if result["reportedTotalRevenue"] != expected["revenue"]:
        _fail(
            f"{path.name}: reportedTotalRevenue {result['reportedTotalRevenue']} "
            f"!= golden {expected['revenue']}"
        )
    _log(
        f"{path.name}: {profiled['platform']} reported {result['reportedTotalQty']} units / "
        f"Rp {result['reportedTotalRevenue']:,} | unreported {result['unreportedCount']}"
    )
    return result["importBatchId"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--keep-db", action="store_true", help="do not reset the writable DB")
    parser.add_argument(
        "--tray",
        action="store_true",
        help="exercise the system-tray startup path (default: headless)",
    )
    parser.add_argument(
        "--idle-exit",
        action="store_true",
        help="only verify the idle watchdog auto-shuts the app down",
    )
    args = parser.parse_args()

    exe: Path = args.exe.resolve()
    if not exe.is_file():
        _fail(f"executable not found: {exe} (run scripts/build.ps1 first)")

    if args.idle_exit:
        _check_idle_exit(exe, args.port)
        return 0

    app_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RAESmartReport"
    if not args.keep_db:
        for stale in app_dir.glob("app_data.db*"):
            stale.unlink()
            _log(f"removed stale {stale}")
    app_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"http://127.0.0.1:{args.port}"
    # The idle watchdog is disabled during the pipeline run so a long export
    # does not trip the auto-exit; `--idle-exit` verifies it separately.
    env = _build_env(args.port, tray=args.tray, idle_seconds=0)

    proc = _launch(exe, env)
    _log(f"launched PID {proc.pid}: {exe.name}")

    try:
        _wait_for_health(base_url)
        _log("health OK")

        db_file = app_dir / "app_data.db"
        if not db_file.is_file():
            _fail(f"frozen writable DB not created at {db_file}")
        _log(f"writable DB resolved to {db_file}")

        with httpx.Client(base_url=base_url, timeout=120.0) as client:
            index = client.get("/")
            index.raise_for_status()
            if '<div id="root">' not in index.text:
                _fail("SPA index.html not served at /")
            asset_match = re.search(r'src="(/assets/[^"]+\.js)"', index.text)
            if asset_match is None:
                _fail("SPA index.html references no built JS asset")
            asset = client.get(asset_match.group(1))
            if asset.status_code != 200:
                _fail(f"bundled SPA asset {asset_match.group(1)} not served")
            _log(f"SPA index + bundled asset {asset_match.group(1)} served")

            spec = client.get("/openapi.json").json()
            for route in ("/api/health", "/api/reports/batches/{batch_id}/unreported"):
                if route not in spec["paths"]:
                    _fail(f"openapi missing {route}")
            _log("openapi exposes health + unreported")

            shopee = _run_platform(
                client,
                ROOT / "sample_data" / "raw" / "raw_shopee_13_19_Jul26.xlsx",
                ("2026-07-13", "2026-07-19"),
                GOLDEN_SHOPEE,
            )
            tiktok = _run_platform(
                client,
                ROOT / "sample_data" / "raw" / "raw_tts_13_19_Jul26.xlsx",
                ("2026-07-13", "2026-07-19"),
                GOLDEN_TIKTOK,
            )
            lazada = _run_platform(
                client,
                ROOT / "sample_data" / "raw" / "raw_laz_1_31_Aug26.xlsx",
                ("2026-08-01", "2026-08-31"),
                GOLDEN_LAZADA,
            )

            shopee_unreported = client.get(f"/api/reports/batches/{shopee}/unreported").json()
            tiktok_unreported = client.get(f"/api/reports/batches/{tiktok}/unreported").json()
            if not shopee_unreported or not tiktok_unreported:
                _fail("unreported endpoint returned no rows")
            _log(
                f"unreported rows: Shopee {len(shopee_unreported)}, TikTok {len(tiktok_unreported)}"
            )

            export = client.get(
                "/api/export/excel",
                params=[
                    ("batchIds", shopee),
                    ("batchIds", tiktok),
                    ("batchIds", lazada),
                ],
            )
            export.raise_for_status()
            out = ROOT / "build" / "smoke_export.xlsx"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(export.content)
            workbook = load_workbook(out, read_only=True)
            missing = EXPECTED_SHEETS - set(workbook.sheetnames)
            if missing:
                _fail(f"exported workbook missing sheets: {sorted(missing)}")
            if "Produk 2 Laz" in workbook.sheetnames:
                _fail("Lazada must not emit a Produk 2 sheet")
            _log(f"export OK: {workbook.sheetnames}")

        _log("PASS: packaged executable end-to-end")
        return 0
    finally:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


if __name__ == "__main__":
    sys.exit(main())
