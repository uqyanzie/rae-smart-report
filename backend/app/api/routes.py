"""REST API routes for ingestion, profiling, transform, reports, and export."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dtos import (
    BatchSummaryDTO,
    CleaningRuleDTO,
    ColumnMappingDTO,
    DeleteBatchResponseDTO,
    IngestionResultDTO,
    ParentRowRuleDTO,
    ProductSummaryDTO,
    ProfileRequestDTO,
    ProfilerResponseDTO,
    TransformAndSaveRequestDTO,
    TransformResponseDTO,
    VariantPerformanceDTO,
)
from app.core.config import get_settings
from app.core.security import sanitize_upload_filename
from app.domain.catalog import PRODUK_GROUP_ORDER
from app.modules.exporter.report_builder import ReportSheet, generate_executive_workbook
from app.modules.ingestion.reader import extract_spreadsheet_rows, read_spreadsheet
from app.modules.profiler.adapters import RawRecord, get_adapter
from app.modules.profiler.fallback import (
    compute_header_signature,
    profile_spreadsheet_headers,
)
from app.modules.storage import AnalyticsRepository
from app.modules.storage.database import session_scope
from app.modules.transformer import (
    PRODUK2_GROUP_ORDER,
    generate_full_produk2_grid,
    generate_full_produk_grid,
    transform_records,
)

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["api"])

# ---------------------------------------------------------------------------
# In-memory upload store (single-process runtime harness)
# ---------------------------------------------------------------------------

_UPLOADS: dict[str, dict[str, Any]] = {}

_PLATFORM_SUFFIX: dict[str, str] = {"SHOPEE": "S", "TIKTOK_SHOP": "T"}


def _store_upload(filename: str, content: bytes) -> str:
    file_id = str(uuid4())
    _UPLOADS[file_id] = {"filename": filename, "bytes": content}
    return file_id


def _get_upload(file_id: str) -> dict[str, Any]:
    upload = _UPLOADS.get(file_id)
    if upload is None:
        raise HTTPException(status_code=404, detail=f"Upload not found for file id '{file_id}'")
    return upload


def _get_repository(request: Request) -> Iterator[AnalyticsRepository]:
    """Yields an AnalyticsRepository inside a session-scoped transaction."""
    session_factory = request.app.state.session_factory
    with session_scope(session_factory) as session:
        yield AnalyticsRepository(session)


def _build_batch_id(platform: str, start: datetime | None, end: datetime | None) -> str:
    if start is not None and end is not None:
        return f"{platform}-{start:%Y-%m-%d}-{end:%Y-%m-%d}-{uuid4().hex[:6]}"
    return f"{platform}-{uuid4().hex[:12]}"


def _apply_cleaning_rules(records: list[RawRecord], rules: list[CleaningRuleDTO]) -> list[RawRecord]:
    """Applies regex cleaning rules to ``raw_variant`` before transformation."""
    compiled: list[Any] = []
    for rule in rules:
        try:
            compiled.append((re.compile(rule.pattern), rule.replacement))
        except re.error as exc:
            raise HTTPException(
                status_code=400,
                detail=f"INVALID_CLEANING_RULE: invalid regex pattern '{rule.pattern}': {exc}",
            ) from exc
    if not compiled:
        return records

    cleaned: list[RawRecord] = []
    for rec in records:
        new_variant = rec.raw_variant
        for pattern, replacement in compiled:
            new_variant = pattern.sub(replacement, new_variant)
        cleaned.append(replace(rec, raw_variant=new_variant) if new_variant != rec.raw_variant else rec)
    return cleaned


def _reported_records(records: list[Any]) -> list[Any]:
    """Records that cross the report boundary of the standard sheets.

    Mirrors exactly what the Produk workbook emits via ``populate_grid``:
    non-cross rows, canonical catalog groups, non-dash/empty variants, and
    membership in the 181-row catalog grid. This keeps the batch summary
    grand totals consistent with the exported workbook (golden totals:
    Shopee 6,910 / 525,973,986; TikTok 11,575 / 658,458,817).
    """
    grid_keys = {
        (row.product_group.rstrip(), row.clean_variant.rstrip()) for row in generate_full_produk_grid()
    }
    return [
        rec
        for rec in records
        if not rec.is_cross_bundling
        and AnalyticsRepository.is_catalog_resolvable(rec.product_group)
        and rec.clean_variant.strip() not in ("-", "")
        and (rec.product_group.strip(), rec.clean_variant.strip()) in grid_keys
    ]


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@router.post("/ingest", response_model=IngestionResultDTO)
async def ingest_spreadsheet(file: UploadFile = File(...)) -> IngestionResultDTO:
    """Uploads a spreadsheet and returns structural metadata plus sample rows."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum upload size of {settings.max_upload_bytes} bytes",
        )

    filename = sanitize_upload_filename(file.filename or "")
    metadata = read_spreadsheet(content, filename=filename)
    file_id = _store_upload(filename, content)

    return IngestionResultDTO(
        file_id=file_id,
        file_name=metadata.file_name,
        file_size_bytes=metadata.file_size_bytes,
        detected_delimiter=metadata.detected_delimiter or "",
        available_sheets=metadata.available_sheets,
        active_sheet=metadata.active_sheet,
        total_rows=metadata.total_rows,
        raw_headers=metadata.raw_headers,
        sample_rows=metadata.sample_rows,
    )


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------


@router.post("/profile", response_model=ProfilerResponseDTO)
async def profile_spreadsheet(
    payload: ProfileRequestDTO,
    repo: AnalyticsRepository = Depends(_get_repository),
) -> ProfilerResponseDTO:
    """Detects the platform adapter or returns a cached mapping template."""
    upload = _get_upload(payload.file_id)
    headers, _ = extract_spreadsheet_rows(
        upload["bytes"], filename=upload["filename"], sheet_name=payload.active_sheet
    )

    signature = compute_header_signature(headers)
    cached = repo.get_mapping_template(signature)

    if cached is not None:
        column_mapping = ColumnMappingDTO(**json.loads(cached["column_mapping_json"]))
        cleaning_rules = [
            CleaningRuleDTO(**rule) for rule in json.loads(cached.get("cleaning_rules_json") or "[]")
        ]
        parent_row_rule = None
        if cached.get("parent_row_rule_json"):
            parent_row_rule = ParentRowRuleDTO(**json.loads(cached["parent_row_rule_json"]))
        return ProfilerResponseDTO(
            is_cached=True,
            platform=cached["platform_name"],
            confidence=1.0,
            column_mapping=column_mapping,
            parent_row_rule=parent_row_rule,
            suggested_cleaning_rules=cleaning_rules,
        )

    profiler_result = profile_spreadsheet_headers(headers, sheet_name=payload.active_sheet)
    return ProfilerResponseDTO(
        is_cached=False,
        platform=profiler_result.platform.value,
        confidence=profiler_result.confidence,
        column_mapping=ColumnMappingDTO(**profiler_result.column_mapping.model_dump()),
        parent_row_rule=(
            ParentRowRuleDTO(**profiler_result.parent_row_rule.model_dump())
            if profiler_result.parent_row_rule is not None
            else None
        ),
        suggested_cleaning_rules=[
            CleaningRuleDTO(**rule.model_dump()) for rule in profiler_result.suggested_cleaning_rules
        ],
    )


# ---------------------------------------------------------------------------
# Transform & save
# ---------------------------------------------------------------------------


@router.post("/transform", response_model=TransformResponseDTO)
async def transform_and_save(
    payload: TransformAndSaveRequestDTO,
    repo: AnalyticsRepository = Depends(_get_repository),
) -> TransformResponseDTO:
    """Runs the ELT pipeline, persists the batch, and returns its summary.

    ``parent_row_rule`` is advisory metadata stored in the mapping template;
    parent-row elimination is performed by the platform adapter and the
    ``persist_batch`` scope boundary (never a raw pre-filter).
    """
    upload = _get_upload(payload.file_id)
    headers, raw_rows = extract_spreadsheet_rows(
        upload["bytes"], filename=upload["filename"], sheet_name=payload.active_sheet
    )

    platform = payload.platform.strip().upper()
    try:
        adapter = get_adapter(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Fail loudly before adapting when the platform's required columns are
    # missing; adapter.adapt() degrades absent columns to zeros and would
    # otherwise persist a silent empty batch (R4).
    adapter.validate_headers(headers)

    raw_records = adapter.adapt(raw_rows)
    raw_records = _apply_cleaning_rules(raw_records, payload.cleaning_rules)
    result = transform_records(raw_records)

    start_dt = datetime.combine(payload.period_start, time.min) if payload.period_start is not None else None
    end_dt = (
        datetime.combine(payload.period_end, time(23, 59, 59)) if payload.period_end is not None else None
    )

    batch_id = _build_batch_id(platform, start_dt, end_dt)
    persist = repo.persist_batch(batch_id, platform, start_dt, end_dt, result.records)

    if payload.save_as_template:
        repo.save_mapping_template(
            platform_name=platform,
            header_signature_hash=compute_header_signature(headers),
            column_mapping_json=json.dumps(payload.column_mapping.model_dump()),
            cleaning_rules_json=json.dumps([rule.model_dump() for rule in payload.cleaning_rules]),
            parent_row_rule_json=(
                json.dumps(payload.parent_row_rule.model_dump())
                if payload.parent_row_rule is not None
                else None
            ),
        )

    reported = _reported_records(result.records)
    total_products = len({rec.product_group.strip() for rec in reported})

    return TransformResponseDTO(
        import_batch_id=persist.import_batch_id,
        platform=platform,
        period_start=start_dt,
        period_end=end_dt,
        reported_product_count=total_products,
        reported_total_qty=sum(rec.qty_sold for rec in reported),
        reported_total_revenue=sum(rec.revenue for rec in reported),
        created_at=datetime.now(UTC),
        inserted_count=persist.inserted_count,
        skipped_count=persist.skipped_unreported.count,
        skipped_qty=persist.skipped_unreported.qty,
        skipped_revenue=persist.skipped_unreported.revenue,
        warning_count=len(result.warnings),
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.get("/reports/batches", response_model=list[BatchSummaryDTO])
async def list_batches(
    repo: AnalyticsRepository = Depends(_get_repository),
) -> list[BatchSummaryDTO]:
    """Lists all persisted batches, newest first."""
    return [BatchSummaryDTO(**item) for item in repo.batch_history()]


@router.get("/reports/batches/{batch_id}/variants", response_model=list[VariantPerformanceDTO])
async def batch_variants(
    batch_id: str,
    is_cross_bundling: int = Query(default=0),
    repo: AnalyticsRepository = Depends(_get_repository),
) -> list[VariantPerformanceDTO]:
    """Returns variant-level performance breakdown for a batch."""
    rows = repo.variant_analytics(batch_id, is_cross_bundling=is_cross_bundling)
    return [VariantPerformanceDTO(**row) for row in rows]


@router.get("/reports/batches/{batch_id}/products", response_model=list[ProductSummaryDTO])
async def batch_products(
    batch_id: str,
    is_cross_bundling: int = Query(default=0),
    repo: AnalyticsRepository = Depends(_get_repository),
) -> list[ProductSummaryDTO]:
    """Returns master product group rollups for a batch."""
    rows = repo.product_group_summary(batch_id, is_cross_bundling=is_cross_bundling)
    return [ProductSummaryDTO(**row) for row in rows]


@router.delete("/reports/batches/{batch_id}", response_model=DeleteBatchResponseDTO)
async def delete_batch(
    batch_id: str,
    repo: AnalyticsRepository = Depends(_get_repository),
) -> DeleteBatchResponseDTO:
    """Deletes a batch (idempotent: missing batches delete zero rows)."""
    deleted_count = repo.delete_batch(batch_id)
    return DeleteBatchResponseDTO(success=True, deleted_count=deleted_count)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get("/export/excel")
async def export_excel(
    batch_ids: list[str] = Query(default=[], alias="batchIds"),
    repo: AnalyticsRepository = Depends(_get_repository),
) -> StreamingResponse:
    """Streams a 4-sheet executive workbook for the selected batches.

    Exactly one batch per platform is required; sheets are emitted in
    canonical order ``Produk S, Produk T, Produk 2 S, Produk 2 T``.
    """
    history = repo.batch_history()
    by_id = {item["import_batch_id"]: item for item in history}

    resolved: dict[str, dict[str, Any]] = {}
    for batch_id in batch_ids:
        item = by_id.get(batch_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
        platform = item["platform"]
        if platform in resolved:
            raise HTTPException(
                status_code=400,
                detail=f"DUPLICATE_PLATFORM_BATCH: multiple batches selected for "
                f"platform '{platform}'; export exactly one batch per platform",
            )
        resolved[platform] = item

    sheets: list[ReportSheet] = []
    for suffix, is_cross in (("S", 0), ("T", 0), ("S", 1), ("T", 1)):
        platform = next((p for p, s in _PLATFORM_SUFFIX.items() if s == suffix), None)
        if platform not in resolved:
            continue
        batch_id = resolved[platform]["import_batch_id"]
        if is_cross == 0:
            grid = generate_full_produk_grid()
            group_order = PRODUK_GROUP_ORDER
            title = f"Produk {suffix}"
        else:
            grid = generate_full_produk2_grid()
            group_order = PRODUK2_GROUP_ORDER
            title = f"Produk 2 {suffix}"
        sheets.append(
            ReportSheet(
                title=title,
                populated=repo.populate_grid(batch_id, is_cross_bundling=is_cross, grid=grid),
                grid=grid,
                group_order=group_order,
            )
        )

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No exportable platform selected; supported platforms: SHOPEE, TIKTOK_SHOP",
        )

    starts = [item["period_start"] for item in resolved.values() if item["period_start"]]
    ends = [item["period_end"] for item in resolved.values() if item["period_end"]]
    if starts and ends:
        name = f"rae_smart_report_{min(starts).date():%Y%m%d}_{max(ends).date():%Y%m%d}"
    else:
        name = "rae_smart_report"

    buffer = generate_executive_workbook(sheets)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
    )
