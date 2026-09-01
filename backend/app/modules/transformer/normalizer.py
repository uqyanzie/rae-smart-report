"""Variant normalization and token resolution engine for RAE Smart Report."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain.catalog import (
    CASE_COLORS,
    FAMILIES,
    FAMILY_BY_NAME,
    LIPCARE_INTRA_BUNDLE_LABELS,
    OTG_INTRA_BUNDLE_LABELS,
    PACKAGING_TOKENS,
    PRODUK_GROUP_ORDER,
    Family,
    resolve_shade,
)
from app.domain.models import VariantRecord
from app.modules.profiler.adapters import RawRecord
from app.modules.transformer.errors import InvalidVariantError

__all__ = [
    "InvalidVariantError",
    "TransformationResult",
    "TransformationWarning",
    "VariantNormalizer",
    "extract_case_color",
    "extract_shades_from_title",
    "strip_ordinal_prefix",
    "strip_packaging_noise",
]


@dataclass(frozen=True, slots=True)
class TransformationWarning:
    """Warning for unmapped tokens or anomalous rows during transformation."""

    platform: str
    product_title: str
    raw_variant: str
    reason: str
    unmapped_tokens: tuple[str, ...] = ()
    sku: str | None = None


@dataclass
class TransformationResult:
    """Output of batch transformation containing atomic records and warnings."""

    records: list[VariantRecord] = field(default_factory=list)
    warnings: list[TransformationWarning] = field(default_factory=list)
    total_qty: int = 0
    total_revenue: int = 0


_ORDINAL_REGEX = re.compile(r"^\s*\d+[\.\s\-_/:]+\s*")
_PACKAGING_REGEX = re.compile(
    r"[/,]\s*(random keychain|tanpa keychain|free keychain|free gift|free pouch|aplikator|keychain|gift|tidak boleh ecer|default).*$",
    re.IGNORECASE,
)
_BRACKET_PREFIX_REGEX = re.compile(r"^\s*\[[^\]]+\]\s*", re.IGNORECASE)
_BRAND_REGEX = re.compile(r"\braecca\b", re.IGNORECASE)


def strip_packaging_noise(text: str) -> str:
    """Strips packaging and marketing suffixes from variant strings."""
    if not text:
        return ""
    cleaned = _PACKAGING_REGEX.sub("", text).strip()
    return cleaned


def strip_ordinal_prefix(token: str) -> str:
    """Strips leading ordinal indicators (e.g. '05. Dynamic' -> 'Dynamic', '01 Peony' -> 'Peony')."""
    if not token:
        return ""
    return _ORDINAL_REGEX.sub("", token.strip()).strip()


def extract_case_color(text: str) -> tuple[str, str | None]:
    """Extracts 3D case color (Fizzy Pop, Sweetie Pop, Cherry Pop) if present in variant string.

    Returns:
        Tuple of (cleaned_text_without_case_color, case_color_or_None)
    """
    if not text:
        return "", None

    for cc in CASE_COLORS:
        pattern = re.compile(rf"(?:,\s*|\+\s*|\(\s*|\b){re.escape(cc)}(?:\s*\)|\b)", re.IGNORECASE)
        if pattern.search(text):
            cleaned = pattern.sub("", text).strip()
            cleaned = re.sub(r"^[,\+\s]+|[,\+\s]+$", "", cleaned).strip()
            return cleaned, cc

    return text.strip(), None


def extract_shades_from_title(title: str, family: Family | None = None) -> list[tuple[str, str]]:
    """Extracts known shades mentioned within a product title string."""
    if not title:
        return []

    found: list[tuple[int, str, str]] = []  # (start_pos, family_name, canonical_shade)
    target_families = [family] if family else FAMILIES

    for fam in target_families:
        for shade in fam.shades:
            # Word boundary search
            pattern = re.compile(rf"\b{re.escape(shade)}\b", re.IGNORECASE)
            for m in pattern.finditer(title):
                found.append((m.start(), fam.name, shade))
        for alias, canon in fam.shade_aliases.items():
            pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
            for m in pattern.finditer(title):
                found.append((m.start(), fam.name, canon))

    found.sort(key=lambda x: x[0])
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for _, fam_name, shade in found:
        if shade not in seen:
            seen.add(shade)
            results.append((fam_name, shade))
    return results


# Standard canonical mapping for report group names in PRODUK_GROUP_ORDER
_CANONICAL_GROUP_MAP: dict[str, str] = {}
for group in PRODUK_GROUP_ORDER:
    _CANONICAL_GROUP_MAP[group.strip().casefold()] = group


def _canonicalize_otg_label(label: str, otg_family: Family) -> str | None:
    """Canonicalizes a bundle label to 'shade + shade' in resolved form.

    Splits on ' + ' and runs each token through ``resolve_shade`` so the
    asymmetric grid label ('Over Cute + Lovie') and raw spellings
    ('Ov Cute + Ov Lovie') collapse onto the same canonical pair (R7).
    Returns None when any token is not an OTG shade.
    """
    resolved: list[str] = []
    for part in label.split(" + "):
        match = resolve_shade(part, family=otg_family)
        if match is None:
            return None
        resolved.append(match[1])
    return " + ".join(resolved).casefold()


class VariantNormalizer:
    """Normalizes raw extracted e-commerce records into canonical domain records."""

    def __init__(self) -> None:
        self._families = FAMILIES
        self._family_by_name = FAMILY_BY_NAME

    def normalize_product_group(self, raw_title: str) -> tuple[str, Family | None, bool, bool]:
        """Resolves the canonical report product group, family, is_bundling, is_cross_bundling.

        Returns:
            Tuple of (canonical_product_group, detected_family, is_bundling, is_cross_bundling)
        """
        # Clean bracket tags and brand noise for matching
        title_no_brackets = _BRACKET_PREFIX_REGEX.sub("", raw_title.strip()).strip()
        title_clean = _BRAND_REGEX.sub("", title_no_brackets).strip()
        title_lower = title_clean.casefold()

        # 1. Check for cross-family bundling (e.g. contains '&' or ' x ' joining 2 families)
        if (
            "&" in title_clean
            or re.search(r"\bsilang\b", title_clean, re.IGNORECASE)
            or ("bundling" in title_lower and re.search(r"\bx\b", title_clean, re.IGNORECASE))
        ):
            detected: list[Family] = []
            for fam in self._families:
                if fam.name.casefold() in title_lower or any(
                    alias.casefold() in title_lower for alias in fam.aliases
                ):
                    detected.append(fam)

            if len(detected) >= 2:
                f1, f2 = detected[0], detected[1]
                idx1 = self._families.index(f1)
                idx2 = self._families.index(f2)
                f_first, f_second = (f1, f2) if idx1 <= idx2 else (f2, f1)
                group_name = f"Bundling {f_first.name} & {f_second.name}"
                return group_name, None, True, True

        # 2. Check for Lipcare multi-group singles vs bundle
        if any(
            k in title_lower
            for k in [
                "lipcare",
                "lip care",
                "lip moist",
                "pdrn glow",
                "lip exfoliant",
                "pha glow",
                "lip sunscreen",
                "sun glow protect",
            ]
        ):
            if "bundling" in title_lower or "bundle" in title_lower:
                return "Bundling Lipcare", self._family_by_name.get("Lipcare"), True, False
            if "exfoliant" in title_lower or "pha glow" in title_lower:
                return "Lip Exfoliant", self._family_by_name.get("Lipcare"), False, False
            if "sunscreen" in title_lower or "sun glow" in title_lower:
                return "Lip Sunscreen", self._family_by_name.get("Lipcare"), False, False
            if "moist" in title_lower or "pdrn glow" in title_lower:
                return "Lip Moist", self._family_by_name.get("Lipcare"), False, False
            return "Lipcare", self._family_by_name.get("Lipcare"), False, False

        # 3. Check for specific family mentions
        is_bundle = "bundling" in title_lower or "bundle" in title_lower

        for fam in self._families:
            if fam.name == "Lipcare":
                continue
            fam_matched = fam.name.casefold() in title_lower or any(
                alias.casefold() in title_lower for alias in fam.aliases
            )
            if fam_matched:
                if is_bundle:
                    bundle_group = _CANONICAL_GROUP_MAP.get(
                        f"Bundling {fam.name}".casefold(), f"Bundling {fam.name}"
                    )
                    return bundle_group, fam, True, False
                else:
                    canonical = _CANONICAL_GROUP_MAP.get(fam.name.casefold(), fam.name)
                    return canonical, fam, False, False

        # Fallback
        return raw_title.strip(), None, is_bundle, False

    def tokenize_variant(self, raw_variant: str) -> list[str]:
        """Splits raw variant string on delimiters (,, +, /, &) and cleans each token."""
        if not raw_variant:
            return []

        # Remove packaging suffix first
        cleaned = strip_packaging_noise(raw_variant)

        # Split on delimiters
        parts = re.split(r"[,+/&]+", cleaned)
        tokens: list[str] = []
        for p in parts:
            t = strip_ordinal_prefix(p)
            t_clean = t.strip()
            if not t_clean:
                continue
            # Check if token is purely packaging noise
            if t_clean.casefold() in PACKAGING_TOKENS or _ORDINAL_REGEX.match(t_clean):
                continue
            tokens.append(t_clean)

        return tokens

    def resolve_tokens(
        self, tokens: list[str], family: Family | None = None
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Resolves list of tokens into (family_name, canonical_shade) pairs and unmapped tokens.

        A token that does not resolve as a whole is retried as a whitespace
        split of short-form shades (e.g. 'Honest Smart' -> Honest Power +
        Smart Power). The split is only accepted when BOTH parts resolve to
        distinct shades of the SAME family, so multi-word shades that resolve
        whole ('Over Cute', 'Kind Power'), non-shade tokens ('HANYA KACA'),
        and mixed-family space pairs ('Active Party') are unaffected.
        """
        resolved: list[tuple[str, str]] = []
        unmapped: list[str] = []

        for token in tokens:
            match = resolve_shade(token, family=family)
            if match:
                resolved.append(match)
                continue
            compound = self._resolve_compound_token(token, family=family)
            if compound:
                resolved.extend(compound)
            else:
                unmapped.append(token)

        return resolved, unmapped

    def _resolve_compound_token(
        self, token: str, family: Family | None = None
    ) -> list[tuple[str, str]]:
        """Attempts to resolve a space-concatenated short-shade pair as one token.

        Handles marketplace variants that join two short-form shades without a
        delimiter, e.g. Power Frosted's 'Honest Smart' -> ('Honest Power',
        'Smart Power'). Returns the two resolved entries only when BOTH parts
        resolve to distinct shades of the same family; otherwise empty.
        """
        parts = [part for part in token.split() if part]
        if len(parts) != 2:
            return []

        first = resolve_shade(parts[0], family=family)
        second = resolve_shade(parts[1], family=family)
        if first is None or second is None:
            return []
        if first[0] != second[0]:
            return []
        if first[1] == second[1]:
            return []
        return [first, second]

    def normalize_single(
        self, raw_record: RawRecord
    ) -> tuple[VariantRecord | None, TransformationWarning | None, bool]:
        """Normalizes a single RawRecord into a VariantRecord.

        Returns:
            Tuple of (VariantRecord or None, TransformationWarning or None, is_same_shade_foldback)
        """
        group_name, family, is_bundling, is_cross = self.normalize_product_group(raw_record.product_title)

        # Extract 3D case color
        var_text, case_color = extract_case_color(raw_record.raw_variant)
        cleaned_var = strip_packaging_noise(var_text).strip()

        # Handle Lipcare explicit bundle labels
        if group_name == "Bundling Lipcare" or (family and family.name == "Lipcare" and is_bundling):
            for label in LIPCARE_INTRA_BUNDLE_LABELS:
                if label.casefold() == cleaned_var.casefold():
                    record = VariantRecord(
                        platform=raw_record.platform,
                        product_group="Bundling Lipcare",
                        raw_variant=raw_record.raw_variant,
                        clean_variant=label,
                        is_bundling=True,
                        is_cross_bundling=False,
                        qty_sold=raw_record.qty_sold,
                        revenue=raw_record.revenue,
                        sku=raw_record.sku,
                        case_color=case_color,
                        raw_product=raw_record.raw_product,
                    )
                    return record, None, False

        # Handle Lipcare singles with "-" or empty variant
        if family and family.name == "Lipcare" and not is_bundling:
            if group_name in ("Lip Moist", "Lip Exfoliant", "Lip Sunscreen"):
                record = VariantRecord(
                    platform=raw_record.platform,
                    product_group=group_name,
                    raw_variant=raw_record.raw_variant,
                    clean_variant=group_name,
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=raw_record.qty_sold,
                    revenue=raw_record.revenue,
                    sku=raw_record.sku,
                    case_color=case_color,
                    raw_product=raw_record.raw_product,
                )
                return record, None, False

        # Handle Over The Glaze explicit bundle labels
        if group_name.startswith("Bundling Over The Glaze") or (
            family and family.name == "Over The Glaze" and is_bundling and not is_cross
        ):
            for label in OTG_INTRA_BUNDLE_LABELS:
                if label.casefold() == cleaned_var.casefold():
                    canonical_group = _CANONICAL_GROUP_MAP.get(
                        "Bundling Over The Glaze".casefold(), "Bundling Over The Glaze"
                    )
                    record = VariantRecord(
                        platform=raw_record.platform,
                        product_group=canonical_group,
                        raw_variant=raw_record.raw_variant,
                        clean_variant=label,
                        is_bundling=True,
                        is_cross_bundling=False,
                        qty_sold=raw_record.qty_sold,
                        revenue=raw_record.revenue,
                        sku=raw_record.sku,
                        case_color=case_color,
                        raw_product=raw_record.raw_product,
                    )
                    return record, None, False

        # Tokenize variant string
        tokens = self.tokenize_variant(var_text)

        # If raw_variant is 'Default' or empty or '-', check if shades are in the product title (e.g. Cimoy picks)
        if (
            not tokens or cleaned_var.casefold() in ("default", "none", "", "-")
        ) and raw_record.product_title:
            title_shades = extract_shades_from_title(raw_record.product_title, family=family)
            if title_shades:
                resolved_shades = title_shades
                unmapped = []
            else:
                resolved_shades, unmapped = self.resolve_tokens(tokens, family=family)
        else:
            resolved_shades, unmapped = self.resolve_tokens(tokens, family=family)

        if unmapped:
            warning = TransformationWarning(
                platform=raw_record.platform,
                product_title=raw_record.product_title,
                raw_variant=raw_record.raw_variant,
                reason=f"Unmapped shade token(s): {unmapped}",
                unmapped_tokens=tuple(unmapped),
                sku=raw_record.sku,
            )
        else:
            warning = None

        # If no tokens resolved, fallback to raw cleaned variant
        if not resolved_shades:
            fallback_label = cleaned_var or raw_record.raw_variant
            record = VariantRecord(
                platform=raw_record.platform,
                product_group=group_name,
                raw_variant=raw_record.raw_variant,
                clean_variant=fallback_label,
                is_bundling=is_bundling,
                is_cross_bundling=is_cross,
                qty_sold=raw_record.qty_sold,
                revenue=raw_record.revenue,
                sku=raw_record.sku,
                case_color=case_color,
                raw_product=raw_record.raw_product,
            )
            return record, warning, False

        # Case 1: Single shade resolved
        if len(resolved_shades) == 1:
            shade_fam_name, shade = resolved_shades[0]

            # Special case for Lipcare singles: map to distinct report group (Lip Moist, Lip Exfoliant, Lip Sunscreen)
            if shade_fam_name == "Lipcare":
                target_group = shade  # 'Lip Moist', 'Lip Exfoliant', 'Lip Sunscreen'
                target_variant = shade
                is_b = False
            else:
                target_group = group_name
                # If product group was generic or single shade in non-bundle, ensure canonical family name
                if not is_bundling:
                    target_group = _CANONICAL_GROUP_MAP.get(shade_fam_name.casefold(), shade_fam_name)
                target_variant = shade
                is_b = is_bundling

            record = VariantRecord(
                platform=raw_record.platform,
                product_group=target_group,
                raw_variant=raw_record.raw_variant,
                clean_variant=target_variant,
                is_bundling=is_b,
                is_cross_bundling=is_cross,
                qty_sold=raw_record.qty_sold,
                revenue=raw_record.revenue,
                sku=raw_record.sku,
                case_color=case_color,
                raw_product=raw_record.raw_product,
            )
            return record, warning, False

        # Case 2: Two shades resolved
        if len(resolved_shades) == 2:
            fam1_name, shade1 = resolved_shades[0]
            fam2_name, shade2 = resolved_shades[1]

            # 2a. Same-shade pair (e.g. Dynamic + Dynamic)
            if fam1_name == fam2_name and shade1 == shade2:
                # Same-shade 2-pack!
                record = VariantRecord(
                    platform=raw_record.platform,
                    product_group=fam1_name,
                    raw_variant=raw_record.raw_variant,
                    clean_variant=shade1,
                    is_bundling=True,  # Initially marked as bundling; foldback will convert
                    is_cross_bundling=False,
                    qty_sold=raw_record.qty_sold,
                    revenue=raw_record.revenue,
                    sku=raw_record.sku,
                    case_color=case_color,
                    raw_product=raw_record.raw_product,
                )
                return record, warning, True

            # 2b. Intra-family distinct shades
            if fam1_name == fam2_name and not is_cross:
                fam = self._family_by_name.get(fam1_name)
                canonical_bundle_group = _CANONICAL_GROUP_MAP.get(
                    f"Bundling {fam1_name}".casefold(), f"Bundling {fam1_name}"
                )

                if fam and fam.name == "Over The Glaze":
                    pair_str1 = f"{shade1} + {shade2}".casefold()
                    pair_str2 = f"{shade2} + {shade1}".casefold()
                    matched_label = None
                    for otg_label in OTG_INTRA_BUNDLE_LABELS:
                        canonical_candidate = _canonicalize_otg_label(otg_label, fam)
                        if canonical_candidate is not None and canonical_candidate in (
                            pair_str1,
                            pair_str2,
                        ):
                            matched_label = otg_label
                            break
                    clean_label = matched_label or f"{shade1} + {shade2}"
                elif fam and fam.name == "Lipcare":
                    shades_set = {shade1, shade2}
                    if shades_set == {"Lip Moist", "Lip Exfoliant"}:
                        clean_label = "Lip Moist + Exfoliant"
                    elif shades_set == {"Lip Moist", "Lip Sunscreen"}:
                        clean_label = "Lip Moist + Sunscreen"
                    elif shades_set == {"Lip Exfoliant", "Lip Sunscreen"}:
                        clean_label = "Lip Exfoliant + Sunscreen"
                    else:
                        clean_label = f"{shade1} + {shade2}"
                    canonical_bundle_group = "Bundling Lipcare"
                else:
                    pairs_order = fam.order_for_pairs() if fam else ()
                    try:
                        idx1 = pairs_order.index(shade1)
                        idx2 = pairs_order.index(shade2)
                        s_first, s_second = (shade1, shade2) if idx1 < idx2 else (shade2, shade1)
                    except ValueError:
                        s_first, s_second = shade1, shade2

                    clean_label = fam.bundle_label(s_first, s_second) if fam else f"{s_first} + {s_second}"

                record = VariantRecord(
                    platform=raw_record.platform,
                    product_group=canonical_bundle_group,
                    raw_variant=raw_record.raw_variant,
                    clean_variant=clean_label,
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=raw_record.qty_sold,
                    revenue=raw_record.revenue,
                    sku=raw_record.sku,
                    case_color=case_color,
                    raw_product=raw_record.raw_product,
                )
                return record, warning, False

            # 2c. Cross-family bundling (Bundling Silang)
            fam_order = [f.name for f in FAMILIES]
            idx_fam1 = fam_order.index(fam1_name) if fam1_name in fam_order else 999
            idx_fam2 = fam_order.index(fam2_name) if fam2_name in fam_order else 999

            if idx_fam1 <= idx_fam2:
                f_first_name, s_first = fam1_name, shade1
                f_second_name, s_second = fam2_name, shade2
            else:
                f_first_name, s_first = fam2_name, shade2
                f_second_name, s_second = fam1_name, shade1

            cross_group_name = f"Bundling {f_first_name} & {f_second_name}"

            # Execution Rule 3: case colour is SKU metadata, never a report
            # grid dimension. The Produk 2 grid (generate_full_produk2_grid)
            # emits case-colour-free labels, so the cross label is always
            # '{s_first}, {s_second}'; case_color is retained on the record
            # for traceability only.
            clean_label = f"{s_first}, {s_second}"

            record = VariantRecord(
                platform=raw_record.platform,
                product_group=cross_group_name,
                raw_variant=raw_record.raw_variant,
                clean_variant=clean_label,
                is_bundling=True,
                is_cross_bundling=True,
                qty_sold=raw_record.qty_sold,
                revenue=raw_record.revenue,
                sku=raw_record.sku,
                case_color=case_color,
                raw_product=raw_record.raw_product,
            )
            return record, warning, False

        # Multiplicity guard (R2): a same-shade pack of N>2 violates the
        # fold-back contract (N=2 only, plan line 181). The engine never sees
        # these rows, so the guard lives here where multiplicity is known.
        if len(resolved_shades) >= 3 and len({(f, s) for f, s in resolved_shades}) == 1:
            raise InvalidVariantError(
                shade=resolved_shades[0][1],
                raw_variant=raw_record.raw_variant,
                sku=raw_record.sku,
                multiplicity=len(resolved_shades),
            )

        # Case 3: 3+ shades resolved (e.g. Lip Moist + Exfoliant + Sunscreen or Mamari's picks)
        if len(resolved_shades) == 3:
            if all(f == "Lipcare" for f, _ in resolved_shades):
                record = VariantRecord(
                    platform=raw_record.platform,
                    product_group="Bundling Lipcare",
                    raw_variant=raw_record.raw_variant,
                    clean_variant="Lip Moist + Exfoliant+ Sunscreen",
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=raw_record.qty_sold,
                    revenue=raw_record.revenue,
                    sku=raw_record.sku,
                    case_color=case_color,
                    raw_product=raw_record.raw_product,
                )
                return record, warning, False
            if all(f == "Glow Up Tint" for f, _ in resolved_shades):
                shades_names = {s for _, s in resolved_shades}
                if "Dynamic" in shades_names and "Energic" in shades_names:
                    pair_label = "Dynamic + Energic"
                else:
                    pair_label = " + ".join(sorted(shades_names))
                record = VariantRecord(
                    platform=raw_record.platform,
                    product_group="Bundling Glow Up Tint",
                    raw_variant=raw_record.raw_variant,
                    clean_variant=pair_label,
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=raw_record.qty_sold,
                    revenue=raw_record.revenue,
                    sku=raw_record.sku,
                    case_color=case_color,
                    raw_product=raw_record.raw_product,
                )
                return record, warning, False

        # Fallback for complex multi-token
        label_parts = [s for _, s in resolved_shades]
        clean_label = " + ".join(label_parts)
        record = VariantRecord(
            platform=raw_record.platform,
            product_group=group_name,
            raw_variant=raw_record.raw_variant,
            clean_variant=clean_label,
            is_bundling=is_bundling,
            is_cross_bundling=is_cross,
            qty_sold=raw_record.qty_sold,
            revenue=raw_record.revenue,
            sku=raw_record.sku,
            case_color=case_color,
            raw_product=raw_record.raw_product,
        )
        return record, warning, False
