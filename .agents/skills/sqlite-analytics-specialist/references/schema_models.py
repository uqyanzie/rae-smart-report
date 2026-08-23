from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, event, Column, String, Integer, BigInteger, Boolean, DateTime, Index, Text
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Applies high-performance PRAGMAs specifically to SQLite connections."""
    module_name = getattr(dbapi_connection.__class__, "__module__", "")
    if "sqlite" in module_name.lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.close()

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(String(36), primary_key=True)
    import_batch_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True) # TIKTOK_SHOP, SHOPEE, etc.
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Labeled Dimensions
    product_group = Column(String(255), nullable=False, index=True)
    raw_variant = Column(String(255), nullable=False)
    clean_variant = Column(String(255), nullable=False, index=True)
    is_bundling = Column(Boolean, default=False, nullable=False)
    is_cross_bundling = Column(Boolean, default=False, nullable=False, index=True) # Bundling Silang
    # SKU-level provenance ONLY: Tinted Jelly Balm ships in a coloured case
    # ("Fizzy Pop", "Sweetie Pop", "Cherry Pop", "Buttered Yellow",
    # "Matcha Strawberry", plus any future colour). NULL for every other family.
    #
    # NOT A REPORTING DIMENSION. TJB totals are aggregated by shade across all
    # case colours. Verified: reference workbook reports "Bunny Pink" = 15 units
    # spanning four distinct case colours as a SINGLE row. Never place this
    # column in a reporting GROUP BY; doing so splits one expected row into
    # several. Retained for traceability and future ad-hoc analysis.
    case_color = Column(String(32), nullable=True)
    sku = Column(String(100), nullable=True)

    # Quantitative Metrics (Integer Rupiah avoids floating-point drift)
    qty_sold = Column(Integer, nullable=False, default=0)
    revenue = Column(BigInteger, nullable=False, default=0) # Stored in exact IDR integer

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_transaction_batch_prod_cross", "import_batch_id", "is_cross_bundling", "product_group"),
        Index("ix_transaction_platform_period", "platform", "period_start", "period_end"),
        # Grid population joins on (product_group, clean_variant) within a batch.
        # case_color is excluded: it is not part of the reporting key.
        Index("ix_transaction_grid_key", "import_batch_id", "product_group", "clean_variant"),
    )

class MappingTemplate(Base):
    __tablename__ = "mapping_templates"

    id = Column(String(36), primary_key=True)
    platform_name = Column(String(50), nullable=False)
    header_signature_hash = Column(String(64), unique=True, nullable=False, index=True)
    column_mapping_json = Column(Text, nullable=False)
    cleaning_rules_json = Column(Text, nullable=True)
    parent_row_rule_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
