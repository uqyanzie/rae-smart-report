import re
from typing import Any
import pandas as pd

def detect_csv_delimiter(content: bytes) -> str:
    """Detects comma, semicolon, or tab delimiter by inspecting the first 5 lines."""
    sample = content[:4096].decode("utf-8", errors="ignore")
    lines = [line for line in sample.splitlines() if line.strip()][:5]
    if not lines:
        return ","
    
    candidates = [",", ";", "\t"]
    counts = {delim: sum(line.count(delim) for line in lines) for delim in candidates}
    return max(counts, key=counts.get) if max(counts.values()) > 0 else ","

def sanitize_currency(val: Any) -> float:
    """
    Parses currency and number strings into clean float values.
    Handles:
    - 'Rp 261.911.314' -> 261911314.0
    - '261.911.314,50' -> 261911314.50
    - '$1,250.00'      -> 1250.0
    - '1250'           -> 1250.0
    - None / '' / '-'  -> 0.0
    """
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    s = str(val).strip()
    if not s or s == "-":
        return 0.0

    # Remove currency prefixes, symbols, and whitespace
    s = re.sub(r'^[^\d\-+,.]+', '', s)
    s = re.sub(r'[^\d\-+,.]+$', '', s)
    s = s.replace("Rp", "").replace("IDR", "").replace("$", "").strip()

    # Determine thousand vs decimal separator
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            # Dot is thousand, comma is decimal: 1.250.000,50
            s = s.replace(".", "").replace(",", ".")
        else:
            # Comma is thousand, dot is decimal: 1,250,000.50
            s = s.replace(",", "")
    elif "." in s and "," not in s:
        # Check if dot is thousand separator (e.g. 261.911.314 or 1.500)
        parts = s.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and not parts[1].startswith("00")):
            s = s.replace(".", "")
    elif "," in s and "." not in s:
        # Check if comma is decimal (e.g. 1500,50) vs thousand (1,500,000)
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return 0.0

def sanitize_integer(val: Any) -> int:
    """Converts mixed values into rounded clean integer quantities."""
    return int(round(sanitize_currency(val)))
