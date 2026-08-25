"""Structured exception classes for the transformer pipeline."""

from __future__ import annotations


class InvalidVariantError(Exception):
    """Raised when a raw variant violates a validated business rule.

    Guards the same-shade fold-back contract (N=2 only): a same-shade pack of
    N>2 cannot fold back and must surface as a 4xx per-file validation error
    instead of being silently mis-aggregated or crashing with a 500.
    """

    def __init__(
        self,
        shade: str,
        raw_variant: str,
        sku: str | None,
        multiplicity: int,
    ) -> None:
        self.shade = shade
        self.raw_variant = raw_variant
        self.sku = sku
        self.multiplicity = multiplicity
        sku_label = sku or "(no SKU)"
        super().__init__(
            f"Same-shade pack of N={multiplicity} for shade '{shade}' "
            f"(raw variant '{raw_variant}', SKU '{sku_label}') exceeds the "
            "fold-back limit of N=2"
        )
