"""End-to-end API tests: upload -> profile -> transform -> query -> export.

Covers the complete Phase 6 flow with a shared in-memory database. Tests in
this module are order-dependent by design: the transform tests persist the
Shopee/TikTok batches that the later report/export/delete tests consume.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app

PERIOD_START = "2026-07-13"
PERIOD_END = "2026-07-19"

GOLDEN_SHOPEE_QTY = 6_910
GOLDEN_SHOPEE_REVENUE = 525_973_986
GOLDEN_TIKTOK_QTY = 11_575
GOLDEN_TIKTOK_REVENUE = 658_458_817

# Shopee skipped tally: 167 dash rows + 13 unresolved groups (qty 1, rev 4,950).
SHOPEE_SKIPPED_COUNT = 180
SHOPEE_SKIPPED_QTY = 1
SHOPEE_SKIPPED_REVENUE = 4_950

# Cross-family (Produk 2) emitted totals at the report boundary.
SHOPEE_CROSS_QTY = 7
TIKTOK_CROSS_QTY = 13

# Shared batch ids recorded by the transform tests for later report tests.
shopee_batch_id = ""
tiktok_batch_id = ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def client(engine):
    app = create_app(engine=engine)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_camel_case(obj: Any) -> None:
    """Recursively asserts that no mapping key contains an underscore."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert "_" not in key, f"non-camelCase key in API response: {key!r}"
            _assert_camel_case(value)
    elif isinstance(obj, list):
        for item in obj:
            _assert_camel_case(item)


def _ingest(client: TestClient, path: Path) -> str:
    content = path.read_bytes()
    resp = client.post(
        "/api/ingest",
        files={
            "file": (
                path.name,
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_camel_case(body)
    return body["fileId"]


def _profile(client: TestClient, file_id: str) -> dict[str, Any]:
    resp = client.post("/api/profile", json={"fileId": file_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_camel_case(body)
    return body


def _transform(
    client: TestClient, file_id: str, profile: dict[str, Any]
) -> dict[str, Any]:
    payload = {
        "fileId": file_id,
        "platform": profile["platform"],
        "periodStart": PERIOD_START,
        "periodEnd": PERIOD_END,
        "columnMapping": profile["columnMapping"],
        "parentRowRule": profile["parentRowRule"],
        "cleaningRules": profile["suggestedCleaningRules"],
        "saveAsTemplate": True,
    }
    resp = client.post("/api/transform", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_camel_case(body)
    return body


def _sheet_qty_sums(workbook_bytes: bytes) -> dict[str, int]:
    """Sums the left-table Produk Terjual (col C) per sheet."""
    wb = load_workbook(io.BytesIO(workbook_bytes))
    totals: dict[str, int] = {}
    for title in wb.sheetnames:
        total = 0
        for r in range(2, wb[title].max_row + 1):
            cell_value = wb[title].cell(row=r, column=3).value
            total += int(cell_value) if isinstance(cell_value, (int, float)) else 0
        totals[title] = total
    return totals


# ---------------------------------------------------------------------------
# Upload & profile
# ---------------------------------------------------------------------------


def test_ingest_returns_camelcase_metadata(client, raw_shopee_path):
    content = raw_shopee_path.read_bytes()
    resp = client.post(
        "/api/ingest",
        files={
            "file": (
                raw_shopee_path.name,
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_camel_case(body)

    assert body["fileId"]
    assert body["fileName"] == raw_shopee_path.name
    assert body["fileSizeBytes"] == len(content)
    assert body["detectedDelimiter"] == ""
    assert body["activeSheet"] == "Produk dengan Performa Terbaik"
    assert "Produk dengan Performa Terbaik" in body["availableSheets"]
    assert body["totalRows"] > 0
    assert "Produk" in body["rawHeaders"]
    assert "Nama Variasi" in body["rawHeaders"]
    assert len(body["sampleRows"]) > 0


def test_upload_unsupported_format_envelope(client):
    resp = client.post("/api/ingest", files={"file": ("report.txt", b"x", "text/plain")})
    assert resp.status_code == 415
    body = resp.json()
    assert body == {
        "status": "error",
        "code": "UNSUPPORTED_FORMAT",
        "message": "Unsupported file format for 'report.txt'. Only .xlsx, .csv are supported.",
    }


def test_profile_detects_shopee(client, raw_shopee_path):
    file_id = _ingest(client, raw_shopee_path)
    profile = _profile(client, file_id)

    assert profile["isCached"] is False
    assert profile["platform"] == "SHOPEE"
    assert profile["confidence"] == 1.0
    assert profile["columnMapping"]["productGroup"] == "Produk"
    assert profile["columnMapping"]["rawVariant"] == "Nama Variasi"
    assert profile["columnMapping"]["qtySold"] == "Produk (Pesanan Siap Dikirim)"
    assert profile["parentRowRule"] == {
        "targetColumn": "Nama Variasi",
        "ignoreCondition": "EQUALS_DASH",
    }
    assert len(profile["suggestedCleaningRules"]) == 2


def test_profile_detects_tiktok(client, raw_tts_path):
    file_id = _ingest(client, raw_tts_path)
    profile = _profile(client, file_id)

    assert profile["isCached"] is False
    assert profile["platform"] == "TIKTOK_SHOP"
    assert profile["confidence"] == 1.0
    assert profile["columnMapping"]["qtySold"] == "Produk terjual"
    assert profile["parentRowRule"] is None
    assert len(profile["suggestedCleaningRules"]) == 1


# ---------------------------------------------------------------------------
# Transform (persists the golden batches)
# ---------------------------------------------------------------------------


def test_transform_shopee_golden_totals(client, raw_shopee_path):
    global shopee_batch_id
    file_id = _ingest(client, raw_shopee_path)
    profile = _profile(client, file_id)
    resp = _transform(client, file_id, profile)

    assert resp["platform"] == "SHOPEE"
    # R5: transform reports the workbook (grid-intersected) boundary under
    # distinct names; the storage-level grandTotal* fields stay on batches.
    assert resp["reportedTotalQty"] == GOLDEN_SHOPEE_QTY
    assert resp["reportedTotalRevenue"] == GOLDEN_SHOPEE_REVENUE
    assert "grandTotalQty" not in resp
    assert "grandTotalRevenue" not in resp
    assert "totalProducts" not in resp
    assert isinstance(resp["reportedProductCount"], int)
    assert resp["skippedCount"] == SHOPEE_SKIPPED_COUNT
    assert resp["skippedQty"] == SHOPEE_SKIPPED_QTY
    assert resp["skippedRevenue"] == SHOPEE_SKIPPED_REVENUE
    assert resp["insertedCount"] > 0
    assert resp["warningCount"] >= 0
    assert resp["periodStart"] == f"{PERIOD_START}T00:00:00"
    assert resp["periodEnd"].startswith(f"{PERIOD_END}T23:59:59")
    shopee_batch_id = resp["importBatchId"]


def test_transform_tiktok_golden_totals(client, raw_tts_path):
    global tiktok_batch_id
    file_id = _ingest(client, raw_tts_path)
    profile = _profile(client, file_id)
    resp = _transform(client, file_id, profile)

    assert resp["platform"] == "TIKTOK_SHOP"
    assert resp["reportedTotalQty"] == GOLDEN_TIKTOK_QTY
    assert resp["reportedTotalRevenue"] == GOLDEN_TIKTOK_REVENUE
    assert "grandTotalQty" not in resp
    # R1: the Tinted Jelly Balm 'Default' orphan (qty 1, rev 22,637) is now
    # surfaced in the skipped tally instead of leaking past it.
    assert resp["skippedCount"] == 1
    assert resp["skippedQty"] == 1
    assert resp["skippedRevenue"] == 22_637
    tiktok_batch_id = resp["importBatchId"]


def test_profile_returns_cached_template(client, raw_shopee_path):
    """After transform saved a template, re-profiling the same headers is cached."""
    file_id = _ingest(client, raw_shopee_path)
    profile = _profile(client, file_id)

    assert profile["isCached"] is True
    assert profile["platform"] == "SHOPEE"
    assert profile["confidence"] == 1.0
    assert profile["columnMapping"]["productGroup"] == "Produk"
    assert len(profile["suggestedCleaningRules"]) == 2


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def test_batches_listing(client):
    resp = client.get("/api/reports/batches")
    assert resp.status_code == 200
    batches = resp.json()
    _assert_camel_case(batches)

    assert len(batches) == 2
    by_platform = {b["platform"]: b for b in batches}
    assert set(by_platform) == {"SHOPEE", "TIKTOK_SHOP"}

    shopee = by_platform["SHOPEE"]
    assert shopee["importBatchId"] == shopee_batch_id
    assert shopee["periodStart"].startswith(PERIOD_START)
    assert shopee["periodEnd"].startswith(PERIOD_END)
    assert isinstance(shopee["totalProducts"], int)
    assert isinstance(shopee["grandTotalQty"], int)


def test_variant_analytics(client):
    resp = client.get(f"/api/reports/batches/{shopee_batch_id}/variants")
    assert resp.status_code == 200
    rows = resp.json()
    _assert_camel_case(rows)
    assert rows  # non-empty

    by_key = {(r["productGroup"], r["cleanVariant"]): r for r in rows}
    active = by_key[("Glow Up Tint", "Active")]
    assert active["totalQty"] == 365
    assert active["totalRevenue"] > 0
    assert "caseColor" in active
    assert active["caseColor"] is None
    assert isinstance(active["isBundling"], bool)


def test_product_summary(client):
    resp = client.get(f"/api/reports/batches/{shopee_batch_id}/products")
    assert resp.status_code == 200
    rows = resp.json()
    _assert_camel_case(rows)

    by_group = {r["productGroup"]: r for r in rows}
    gut = by_group["Glow Up Tint"]
    assert gut["totalQty"] == 6_109
    assert gut["totalRevenue"] == 435_136_850


# ---------------------------------------------------------------------------
# Phase G: isBundling filter (Single / Bundling partition within non-cross)
# ---------------------------------------------------------------------------


def test_variants_is_bundling_partition(client):
    """isBundling=0/1 splits the non-cross variant set; the two partitions
    sum to the unfiltered golden total (6,910 for Shopee)."""
    resp = client.get(
        f"/api/reports/batches/{shopee_batch_id}/variants",
        params={"isBundling": 0, "isCrossBundling": 0},
    )
    assert resp.status_code == 200
    singles = resp.json()
    _assert_camel_case(singles)
    assert singles
    assert all(r["isBundling"] is False for r in singles)
    assert all(not r["productGroup"].startswith("Bundling") for r in singles)

    resp = client.get(
        f"/api/reports/batches/{shopee_batch_id}/variants",
        params={"isBundling": 1, "isCrossBundling": 0},
    )
    bundles = resp.json()
    assert bundles
    assert all(r["isBundling"] is True for r in bundles)
    assert all(r["productGroup"].startswith("Bundling") for r in bundles)

    resp = client.get(f"/api/reports/batches/{shopee_batch_id}/variants")
    full = resp.json()
    assert sum(r["totalQty"] for r in singles) + sum(r["totalQty"] for r in bundles) == sum(
        r["totalQty"] for r in full
    ) == GOLDEN_SHOPEE_QTY


def test_variants_is_bundling_tiktok(client):
    """The TikTok partition splits the golden 11,575 non-cross total."""
    resp = client.get(
        f"/api/reports/batches/{tiktok_batch_id}/variants",
        params={"isBundling": 0, "isCrossBundling": 0},
    )
    singles = resp.json()
    resp = client.get(
        f"/api/reports/batches/{tiktok_batch_id}/variants",
        params={"isBundling": 1, "isCrossBundling": 0},
    )
    bundles = resp.json()
    assert sum(r["totalQty"] for r in singles) + sum(r["totalQty"] for r in bundles) == (
        GOLDEN_TIKTOK_QTY
    )
    assert all(r["productGroup"].startswith("Bundling") for r in bundles)


def test_products_is_bundling_partition(client):
    """Product group summary splits identically via isBundling."""
    resp = client.get(
        f"/api/reports/batches/{shopee_batch_id}/products",
        params={"isBundling": 0, "isCrossBundling": 0},
    )
    singles = resp.json()
    _assert_camel_case(singles)
    assert singles
    assert all(not r["productGroup"].startswith("Bundling") for r in singles)

    resp = client.get(
        f"/api/reports/batches/{shopee_batch_id}/products",
        params={"isBundling": 1, "isCrossBundling": 0},
    )
    bundles = resp.json()
    assert bundles
    assert all(r["productGroup"].startswith("Bundling") for r in bundles)

    resp = client.get(f"/api/reports/batches/{shopee_batch_id}/products")
    full = resp.json()
    assert sum(r["totalQty"] for r in singles) + sum(r["totalQty"] for r in bundles) == sum(
        r["totalQty"] for r in full
    ) == GOLDEN_SHOPEE_QTY


# ---------------------------------------------------------------------------
# Query C: multi-platform aggregation
# ---------------------------------------------------------------------------


def test_aggregate_all_platforms(client):
    resp = client.get("/api/reports/aggregate")
    assert resp.status_code == 200
    rows = resp.json()
    _assert_camel_case(rows)
    assert rows
    assert {r["platform"] for r in rows} == {"SHOPEE", "TIKTOK_SHOP"}
    for row in rows:
        assert 0.0 <= row["contributionRatio"] <= 1.0
        assert isinstance(row["totalQty"], int)


def test_aggregate_platform_filter_sums(client):
    """A3: platform filter narrows to one platform and the non-cross quantity
    sums match the golden totals (persisted non-cross rows == report boundary)."""
    resp = client.get("/api/reports/aggregate", params={"platform": "SHOPEE", "isCrossBundling": 0})
    assert resp.status_code == 200
    rows = resp.json()
    _assert_camel_case(rows)
    assert rows
    assert all(r["platform"] == "SHOPEE" for r in rows)
    assert sum(r["totalQty"] for r in rows) == GOLDEN_SHOPEE_QTY

    resp = client.get(
        "/api/reports/aggregate", params={"platform": "TIKTOK_SHOP", "isCrossBundling": 0}
    )
    rows = resp.json()
    assert rows
    assert all(r["platform"] == "TIKTOK_SHOP" for r in rows)
    assert sum(r["totalQty"] for r in rows) == GOLDEN_TIKTOK_QTY


def test_aggregate_cross_bundling_toggle(client):
    """A3: the isCrossBundling toggle swaps the data set to cross rows."""
    resp = client.get("/api/reports/aggregate", params={"platform": "SHOPEE", "isCrossBundling": 1})
    assert resp.status_code == 200
    rows = resp.json()
    _assert_camel_case(rows)
    assert rows
    assert all(r["platform"] == "SHOPEE" for r in rows)
    assert sum(r["totalQty"] for r in rows) == SHOPEE_CROSS_QTY

    resp = client.get(
        "/api/reports/aggregate", params={"platform": "TIKTOK_SHOP", "isCrossBundling": 1}
    )
    rows = resp.json()
    assert rows
    assert sum(r["totalQty"] for r in rows) == TIKTOK_CROSS_QTY


def test_aggregate_date_range_inclusion(client):
    """A3: periodStart/periodEnd include both persisted batches; a disjoint
    range returns an empty list."""
    resp = client.get(
        "/api/reports/aggregate",
        params={"periodStart": "2026-07-13", "periodEnd": "2026-07-19"},
    )
    rows = resp.json()
    assert rows
    assert {r["platform"] for r in rows} == {"SHOPEE", "TIKTOK_SHOP"}

    resp = client.get(
        "/api/reports/aggregate",
        params={"periodStart": "2025-01-01", "periodEnd": "2025-01-31"},
    )
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_excel_streams_workbook(client):
    resp = client.get(
        "/api/export/excel",
        params=[("batchIds", shopee_batch_id), ("batchIds", tiktok_batch_id)],
    )
    assert resp.status_code == 200, resp.text
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "rae_smart_report_20260713_20260719.xlsx" in resp.headers[
        "content-disposition"
    ]

    sums = _sheet_qty_sums(resp.content)
    assert list(sums) == ["Produk S", "Produk T", "Produk 2 S", "Produk 2 T"]
    assert sums["Produk S"] == GOLDEN_SHOPEE_QTY
    assert sums["Produk T"] == GOLDEN_TIKTOK_QTY
    assert sums["Produk 2 S"] == SHOPEE_CROSS_QTY
    assert sums["Produk 2 T"] == TIKTOK_CROSS_QTY


def test_export_unknown_batch_404(client):
    resp = client.get("/api/export/excel", params=[("batchIds", "no-such-batch")])
    assert resp.status_code == 404
    body = resp.json()
    assert body["status"] == "error"
    assert body["code"] == "HTTP_ERROR"


# ---------------------------------------------------------------------------
# Deletion & error envelopes
# ---------------------------------------------------------------------------


def test_delete_batch_idempotent(client):
    resp = client.delete(f"/api/reports/batches/{shopee_batch_id}")
    assert resp.status_code == 200
    body = resp.json()
    _assert_camel_case(body)
    assert body["success"] is True
    assert body["deletedCount"] > 0

    # Deleting again is a no-op.
    resp = client.delete(f"/api/reports/batches/{shopee_batch_id}")
    assert resp.status_code == 200
    assert resp.json()["deletedCount"] == 0

    # Variants for the deleted batch are empty.
    resp = client.get(f"/api/reports/batches/{shopee_batch_id}/variants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_transform_missing_required_columns_422(client):
    """R4: a platform-mismatched file fails loudly instead of persisting an
    empty batch (422 MISSING_REQUIRED_COLUMN) and the batch count is stable."""
    content = b"ColA,ColB,ColC\n1,2,3\n"
    resp = client.post(
        "/api/ingest",
        files={"file": ("mismatch.csv", content, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    file_id = resp.json()["fileId"]

    before = len(client.get("/api/reports/batches").json())

    payload = {
        "fileId": file_id,
        "platform": "SHOPEE",
        "columnMapping": {
            "productGroup": "Produk",
            "rawVariant": "Nama Variasi",
            "qtySold": "Produk (Pesanan Siap Dikirim)",
            "revenue": "Penjualan (Pesanan Siap Dikirim) (IDR)",
        },
    }
    resp = client.post("/api/transform", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "error"
    assert body["code"] == "MISSING_REQUIRED_COLUMN"
    assert len(client.get("/api/reports/batches").json()) == before


def test_transform_same_shade_triple_422(client):
    """A2: a same-shade N>2 pack surfaces as 422 INVALID_VARIANT (never 500),
    naming the offending shade/raw variant, and no partial batch persists."""
    content = (
        "Produk,Nama Variasi,Produk (Pesanan Siap Dikirim),"
        "Penjualan (Pesanan Siap Dikirim) (IDR)\n"
        '"Raecca Bundling Glow Up Tint","Dynamic, 05. Dynamic, Dynamic",1,139900\n'
    )
    resp = client.post(
        "/api/ingest",
        files={"file": ("triple.csv", content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    file_id = resp.json()["fileId"]

    before = len(client.get("/api/reports/batches").json())

    payload = {
        "fileId": file_id,
        "platform": "SHOPEE",
        "columnMapping": {
            "productGroup": "Produk",
            "rawVariant": "Nama Variasi",
            "qtySold": "Produk (Pesanan Siap Dikirim)",
            "revenue": "Penjualan (Pesanan Siap Dikirim) (IDR)",
        },
    }
    resp = client.post("/api/transform", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "error"
    assert body["code"] == "INVALID_VARIANT"
    assert "Dynamic" in body["message"]
    assert "Dynamic, 05. Dynamic, Dynamic" in body["message"]
    assert "(no SKU)" in body["message"]
    assert len(client.get("/api/reports/batches").json()) == before


def test_transform_unknown_file_id_404(client):
    payload = {
        "fileId": "no-such-upload",
        "platform": "SHOPEE",
        "columnMapping": {
            "productGroup": "Produk",
            "rawVariant": "Nama Variasi",
            "qtySold": "Produk (Pesanan Siap Dikirim)",
            "revenue": "Penjualan (Pesanan Siap Dikirim) (IDR)",
        },
    }
    resp = client.post("/api/transform", json=payload)
    assert resp.status_code == 404
    body = resp.json()
    assert body["status"] == "error"
    assert body["code"] == "HTTP_ERROR"
    assert "no-such-upload" in body["message"]


def test_api_only_mode_root_404(tmp_path, monkeypatch):
    """Without frontend/dist, the root path returns the error envelope."""
    import app.core.config as config

    monkeypatch.setenv("RAE_FRONTEND_DIST", str(tmp_path / "nonexistent-dist"))
    config._settings = None
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    try:
        app = create_app(engine=engine)
        with TestClient(app) as c:
            resp = c.get("/")
            assert resp.status_code == 404
            body = resp.json()
            assert body["status"] == "error"
            assert body["code"] == "HTTP_ERROR"
            assert "Not Found" in body["message"]
    finally:
        engine.dispose()
        config._settings = None
        monkeypatch.delenv("RAE_FRONTEND_DIST", raising=False)


# ---------------------------------------------------------------------------
# Phase A4: OpenAPI contract checks
# ---------------------------------------------------------------------------


def test_openapi_response_schemas_camelcase(client):
    """A4: every response schema field serializes camelCase (no underscores),
    so a generated TypeScript client never needs manual field renames."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()

    checked: set[str] = set()

    def check(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            return
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            key = ref.rsplit("/", 1)[-1]
            if key in checked:
                return
            checked.add(key)
            node = spec["components"]["schemas"][key]
        props = node.get("properties")
        if isinstance(props, dict):
            for name in props:
                assert "_" not in name, f"snake_case response field '{name}' at {path}"
                check(props[name], f"{path}.{name}")
        for child_key in ("items", "additionalProperties"):
            child = node.get(child_key)
            if isinstance(child, dict):
                check(child, f"{path}.{child_key}")

    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            for status_code, response in op.get("responses", {}).items():
                for media, media_obj in response.get("content", {}).items():
                    check(media_obj.get("schema", {}), f"{path} {method} {status_code} {media}")


def test_openapi_contract_matches_bridge_dtos(client):
    """A4: the wire contract matches frontend_dtos.ts (R5 reported* fields,
    the aggregate endpoint, and camelCase aggregate query parameters)."""
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]

    # R5: transform response reports grid-intersected workbook totals under
    # distinct reported* names; storage-level grandTotal* stays on batches.
    transform = schemas["TransformResponseDTO"]["properties"]
    for field in ("reportedProductCount", "reportedTotalQty", "reportedTotalRevenue"):
        assert field in transform, f"missing reported field {field}"
    assert "grandTotalQty" not in transform
    assert "grandTotalRevenue" not in transform
    assert "totalProducts" not in transform

    agg = schemas["AggregateRowDTO"]["properties"]
    assert set(agg) == {
        "platform",
        "productGroup",
        "cleanVariant",
        "totalQty",
        "totalRevenue",
        "contributionRatio",
    }

    assert "/api/reports/aggregate" in spec["paths"]
    aggregate_params = {
        p["name"] for p in spec["paths"]["/api/reports/aggregate"]["get"]["parameters"]
    }
    assert aggregate_params == {"platform", "periodStart", "periodEnd", "isCrossBundling"}


# ---------------------------------------------------------------------------
# Phase B: SPA static mount
# ---------------------------------------------------------------------------


def test_spa_mount_serves_index_and_blocks_api(tmp_path, monkeypatch):
    """Phase B: when ``frontend/dist`` exists, the root serves ``index.html``,
    built assets are served, unknown SPA routes fall back to the index, and API
    and schema paths never fall through."""
    import app.core.config as config

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>RAE SPA</html>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")

    monkeypatch.setenv("RAE_FRONTEND_DIST", str(dist))
    config._settings = None
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    try:
        app = create_app(engine=engine)
        with TestClient(app) as c:
            root = c.get("/")
            assert root.status_code == 200
            assert "RAE SPA" in root.text

            assert c.get("/assets/app.js").status_code == 200

            fallback = c.get("/batches")
            assert fallback.status_code == 200
            assert "RAE SPA" in fallback.text

            assert c.get("/api/reports/batches").status_code == 200
            assert c.get("/openapi.json").status_code == 200
            assert c.get("/docs").status_code == 200
    finally:
        engine.dispose()
        config._settings = None
        monkeypatch.delenv("RAE_FRONTEND_DIST", raising=False)
