"""SQLAlchemy ORM models for transactional storage and mapping templates."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TransactionItem(Base):
    """Atomic labeled transaction record persisted after ELT normalization."""

    __tablename__ = "transaction_items"

    id = Column(String(36), primary_key=True)
    import_batch_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)  # SHOPEE / TIKTOK_SHOP / ...
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    # Future daily-series compatibility (Phase 2 daily schema); nullable until wired.
    transaction_date = Column(DateTime, nullable=True)

    # Labeled dimensions
    product_group = Column(String(255), nullable=False, index=True)
    raw_variant = Column(String(255), nullable=False)
    clean_variant = Column(String(255), nullable=False, index=True)
    is_bundling = Column(Boolean, default=False, nullable=False)
    is_cross_bundling = Column(Boolean, default=False, nullable=False, index=True)

    # SKU-level provenance ONLY -- never a reporting GROUP BY key. Tinted
    # Jelly Balm totals are aggregated by shade across all case colours
    # (verified: golden 'Bunny Pink' = 15 units spanning four case colours as
    # ONE row). Retained for traceability and future ad-hoc analysis.
    case_color = Column(String(32), nullable=True)
    sku = Column(String(100), nullable=True)

    # Quantitative metrics (integer IDR avoids floating-point drift)
    qty_sold = Column(Integer, nullable=False, default=0)
    revenue = Column(BigInteger, nullable=False, default=0)  # exact IDR integer

    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index(
            "ix_transaction_batch_prod_cross",
            "import_batch_id",
            "is_cross_bundling",
            "product_group",
        ),
        Index("ix_transaction_platform_period", "platform", "period_start", "period_end"),
        # Grid population joins on (product_group, clean_variant) within a batch.
        # case_color is deliberately absent: it is not part of the reporting key.
        Index("ix_transaction_grid_key", "import_batch_id", "product_group", "clean_variant"),
    )


class MappingTemplate(Base):
    """Cached column mapping and cleaning rules keyed by header signature."""

    __tablename__ = "mapping_templates"

    id = Column(String(36), primary_key=True)
    platform_name = Column(String(50), nullable=False)
    header_signature_hash = Column(String(64), unique=True, nullable=False, index=True)
    column_mapping_json = Column(Text, nullable=False)
    cleaning_rules_json = Column(Text, nullable=True)
    parent_row_rule_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
