"""Locale-aware currency and numeric parsing utilities for RAE Smart Report.

Pins default formatting to Indonesian Locale (id-ID):
- Dot (.) is thousands separator (e.g., 'Rp 50.000' -> 50000.0, '261.911.314' -> 261911314.0)
- Comma (,) is decimal separator (e.g., '261.911.314,50' -> 261911314.50)
- Parenthetical negatives (e.g., '(1.000)' -> -1000.0, '(100.000)' -> -100000.0)
- Explicit override available via decimal_sep parameter.
"""

from __future__ import annotations

import math
import re
from typing import Any, Final

__all__ = [
    "detect_csv_delimiter",
    "is_blank_marker",
    "sanitize_currency",
    "sanitize_integer",
    "sanitize_percent",
]

_BLANK_MARKERS: Final[frozenset[str]] = frozenset(
    {"", "-", "--", "n/a", "na", "#n/a", "null", "none", "nan", "#div/0!", "#value!", "#ref!"}
)

_CURRENCY_NOISE: Final[re.Pattern[str]] = re.compile(r"(?:rp|idr|myr|rm|usd|sgd|\$|€|£)", re.IGNORECASE)

_NON_NUMERIC: Final[re.Pattern[str]] = re.compile(r"[^0-9,.\-+]")

_NBSP: Final[str] = "\u00a0"


def detect_csv_delimiter(content: bytes) -> str:
    """Detects comma, semicolon, or tab delimiter by inspecting the first 5 lines."""
    sample = content[:4096].decode("utf-8", errors="ignore")
    lines = [line for line in sample.splitlines() if line.strip()][:5]
    if not lines:
        return ","

    candidates = [",", ";", "\t"]
    counts = {delim: sum(line.count(delim) for line in lines) for delim in candidates}
    return max(counts, key=lambda delim: counts[delim]) if max(counts.values()) > 0 else ","


def is_blank_marker(value: Any) -> bool:
    """True when value represents an absent or placeholder cell."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _BLANK_MARKERS
    if isinstance(value, float):
        return math.isnan(value)
    return False


def sanitize_currency(
    val: Any,
    *,
    decimal_sep: str = ",",
    default: float = 0.0,
) -> float:
    """
    Parses currency and number strings into clean float values.
    By default parses Indonesian format (dot = thousands, comma = decimal):
    - 'Rp 50.000'        -> 50000.0
    - 'Rp 100.000'       -> 100000.0
    - '149.000'          -> 149000.0
    - 'Rp 261.911.314'   -> 261911314.0
    - '261.911.314,50'   -> 261911314.50
    - '-Rp 1.000'        -> -1000.0
    - '(1.000)'          -> -1000.0
    - None / '' / '-'    -> 0.0
    """
    if is_blank_marker(val):
        return default

    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).replace(_NBSP, " ").strip()
    if not text:
        return default

    # Check for parenthetical negative: (100.000) -> -100000
    negative_parens = text.startswith("(") and text.endswith(")")

    text = _CURRENCY_NOISE.sub("", text)
    text = _NON_NUMERIC.sub("", text)
    if not text or text in {"-", "+", ".", ","}:
        return default

    thousands_sep = "." if decimal_sep == "," else ","

    # Preserve leading sign
    sign = -1.0 if text.startswith("-") or negative_parens else 1.0
    text = text.lstrip("+-").replace("-", "").replace("+", "")

    # Strip thousands separators
    text = text.replace(thousands_sep, "")

    if decimal_sep != ".":
        # If there's a decimal separator (e.g. comma), normalize to standard dot decimal
        head, _, tail = text.rpartition(decimal_sep)
        text = f"{head.replace(decimal_sep, '')}.{tail}" if head else tail

    if not text or text == ".":
        return default

    try:
        return sign * float(text)
    except ValueError:
        return default


def sanitize_integer(
    val: Any,
    *,
    decimal_sep: str = ",",
    default: int = 0,
) -> int:
    """Converts mixed values into rounded integer quantities (half away from zero)."""
    if is_blank_marker(val):
        return default
    magnitude = sanitize_currency(val, decimal_sep=decimal_sep, default=float(default))
    if math.isnan(magnitude) or math.isinf(magnitude):
        return default
    return int(math.floor(magnitude + 0.5) if magnitude >= 0 else math.ceil(magnitude - 0.5))


def sanitize_percent(
    val: Any,
    *,
    decimal_sep: str = ",",
    default: float = 0.0,
) -> float:
    """Parses percentage string (e.g. '3,05%') into a 0-1 ratio (0.0305)."""
    if is_blank_marker(val):
        return default
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    text = str(val)
    magnitude = sanitize_currency(text, decimal_sep=decimal_sep, default=default)
    return magnitude / 100.0 if "%" in text else magnitude
