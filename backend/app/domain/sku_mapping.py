"""Lazada Seller SKU -> (product title, variant label) mapping loader.

Runtime artifact: ``backend/app/data/sku_mapping.json`` (256 entries) derived
from the authoritative ``sku_mapping.csv`` (Produk, Nama Variasi, Kode
Variasi). Duplicate codes resolve first-row-wins; the ``-`` parent/SKU-INDUK
marker code is excluded. Path resolution follows the pyinstaller-packaging-
guardian pattern: repo-root ``data/`` in development, ``sys._MEIPASS/data`` or
the executable directory for packaged builds.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import resolve_sku_mapping_path

__all__ = [
    "SkuMapping",
    "SkuMappingEntry",
]

# Bundle codes that carry a reverse-order variant on Lazada, e.g.
# 'RAEGLT-008-006' -> 'RAEGLT-006-008' -> 'Energic + Gorgeous'.
_REVERSE_CODE_RE: re.Pattern[str] = re.compile(r"^(RAEGLT)-(\d{3})-(\d{3})$")


@dataclass(frozen=True)
class SkuMappingEntry:
    """One code's resolved (product title, variant label) pair."""

    product: str
    variant: str


class SkuMapping:
    """Deterministic code -> (product, variant) lookup for Lazada Seller SKUs.

    The authoritative source is ``sku_mapping.csv``; the JSON runtime artifact
    is loaded once per adapter instance. ``lookup_reverse`` resolves the
    reverse-order bundle spelling observed on Lazada (``RAEGLT-008-006`` ->
    ``RAEGLT-006-008``) when the reversed code is itself present.
    """

    def __init__(self, entries: dict[str, dict[str, str]]) -> None:
        self._by_code: dict[str, SkuMappingEntry] = {
            code: SkuMappingEntry(product=entry["produk"], variant=entry["nama_variasi"])
            for code, entry in entries.items()
        }

    @classmethod
    def load(cls, path: str | Path | None = None) -> SkuMapping:
        """Loads the mapping artifact from ``path`` or the config-resolved path."""
        resolved = Path(path) if path is not None else resolve_sku_mapping_path()
        with open(resolved, encoding="utf-8") as handle:
            return cls(json.load(handle))

    def __contains__(self, code: str) -> bool:
        return code in self._by_code

    def __len__(self) -> int:
        return len(self._by_code)

    def lookup(self, code: str) -> SkuMappingEntry | None:
        """Exact code lookup; returns None when the code is unknown."""
        return self._by_code.get(code)

    def lookup_reverse(self, code: str) -> SkuMappingEntry | None:
        """Reverse-order bundle lookup (``RAEGLT-008-006`` -> ``RAEGLT-006-008``)."""
        match = _REVERSE_CODE_RE.match(code)
        if match is None:
            return None
        reversed_code = f"{match.group(1)}-{match.group(3)}-{match.group(2)}"
        return self._by_code.get(reversed_code)
