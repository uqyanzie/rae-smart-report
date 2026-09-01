"""Canonical product catalog and shade resolution specification.

Single source of truth for:
1. Master Product Families and ordered shades.
2. Shade aliases and misspellings observed across marketplaces.
3. Packaging noise tokens to strip.
4. Tinted Jelly Balm case colors (SKU metadata; NOT a reporting dimension).
5. The THREE distinct orderings each family carries (see below).
6. Per-family short shade forms used only in intra-family bundle labels.

THE THREE ORDERINGS
-------------------
Each family needs up to three different sequences. They are NOT interchangeable
and using the wrong one silently misplaces rows in the report:

``singles_order``
    Drives single-shade rows in the left table. Largely alphabetical.
``display_order``
    Drives intra-family bundle pair generation. Follows the marketplace's own
    shade ordinals, so e.g. Glow Up Tint places ``Strong`` (ordinal 09) BEFORE
    ``Happy`` (ordinal 10) even though S > H alphabetically.
``cross_order``
    Drives cross-family (``Produk 2``) grids. Differs again from both above.

Pair generation is a strict upper triangle over ``display_order`` -- i.e.
``itertools.combinations(display_order, 2)`` -- verified to match the reference
workbook exactly for 5 of the 6 pairable families. ``Over The Glaze`` is the
exception and is supplied as a literal list (see ``OTG_INTRA_BUNDLE_LABELS``).

All sequences below were validated by direct comparison against the reference
workbook. Do not re-derive or "tidy" them into a single alphabetical tuple.

LABEL CONVENTIONS
-----------------
- Intra-family pair:            ``" + "``   e.g. ``Active + Brave``
- Cross-family pair:            ``", "``    e.g. ``Active, Over Cute``
- Cross-family + case colour:   ``" + "`` between shades then ``", "`` before
  the colour, e.g. ``Over Cute + Bunny Pink, Fizzy Pop``
- Compare and join labels after ``.rstrip()`` on BOTH sides. The reference
  workbook contains 57 labels with trailing spaces from manual entry; they are
  not reproduced here deliberately.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Mapping, Optional, Tuple, List

@dataclass(frozen=True, slots=True)
class Family:
    """A master product family and its ordering/labelling rules.

    Attributes:
        name: Canonical family name.
        shades: Canonical shade vocabulary (alphabetical; the resolution set).
        aliases: Family-name spellings seen in raw product titles.
        shade_aliases: Raw shade spelling -> canonical shade.
        singles_order: Row order for single-shade rows. Falls back to ``shades``.
        display_order: Row order for intra-family bundle pairs. Falls back to
            ``shades``. **This is the one that is easy to get wrong.**
        cross_order: Token order for cross-family grids. Falls back to
            ``display_order``.
        short_shade: Canonical shade -> short form, used ONLY in intra-family
            bundle labels (``Power Frosted Velvet Matte`` drops ``" Power"``).
    """

    name: str
    shades: Tuple[str, ...]
    aliases: Tuple[str, ...] = ()
    shade_aliases: Mapping[str, str] = field(default_factory=dict)
    singles_order: Tuple[str, ...] = ()
    display_order: Tuple[str, ...] = ()
    cross_order: Tuple[str, ...] = ()
    short_shade: Mapping[str, str] = field(default_factory=dict)

    def order_for_singles(self) -> Tuple[str, ...]:
        """Row order for single-shade rows."""
        return self.singles_order or self.shades

    def order_for_pairs(self) -> Tuple[str, ...]:
        """Row order for intra-family bundle pair generation."""
        return self.display_order or self.shades

    def order_for_cross(self) -> Tuple[str, ...]:
        """Token order for cross-family grid generation."""
        return self.cross_order or self.order_for_pairs()

    def bundle_label(self, shade_a: str, shade_b: str) -> str:
        """Intra-family bundle label, applying any short-form substitution."""
        left = self.short_shade.get(shade_a, shade_a)
        right = self.short_shade.get(shade_b, shade_b)
        return f"{left} + {right}"

# Observed shade aliases across Shopee and TikTok exports
_GUT_ALIASES: Final[Mapping[str, str]] = MappingProxyType({
    "cheerfull": "Cheerful",
    "joyfull": "Joyful",
    "energetic": "Energic",
    "gorgeus": "Gorgeous",
    "confidence": "Confident",
})

_OTG_ALIASES: Final[Mapping[str, str]] = MappingProxyType({
    "ov cute": "Over Cute",
    "ov drama": "Over Drama",
    "ov hype": "Over Hype",
    "ov lovie": "Over Lovie",
    "ov react": "Over React",
    "ov slay": "Over Slay",
    "cute": "Over Cute",
    "drama": "Over Drama",
    "hype": "Over Hype",
    "lovie": "Over Lovie",
    "react": "Over React",
    "slay": "Over Slay",
})

_PFVM_ALIASES: Final[Mapping[str, str]] = MappingProxyType({
    "ambition": "Ambition Power",
    "classy": "Classy Power",
    "heart": "Heart Power",
    "honest": "Honest Power",
    "kind": "Kind Power",
    "smart": "Smart Power",
})

_TJB_ALIASES: Final[Mapping[str, str]] = MappingProxyType({
    "bunpink": "Bunny Pink",
    "bun pink": "Bunny Pink",
    "wildmauv": "Wild Mauve",
    "wild mauv": "Wild Mauve",
    "wildmauve": "Wild Mauve",
    "hiprose": "Hippie Rose",
    "hip rose": "Hippie Rose",
    "nudycaramel": "Nudy Caramel",
    "nudcaramel": "Nudy Caramel",
    "nudcara": "Nudy Caramel",
    "nudy": "Nudy Caramel",
    "spillnude": "Spill Nude",
    "spill": "Spill Nude",
    "redbabe": "Red Babe",
    "red": "Red Babe",
})

_LIPCARE_ALIASES: Final[Mapping[str, str]] = MappingProxyType({
    "moist": "Lip Moist",
    "lip moist": "Lip Moist",
    "pdrn glow lip moist": "Lip Moist",
    "exfo": "Lip Exfoliant",
    "lip exfo": "Lip Exfoliant",
    "exfoliant": "Lip Exfoliant",
    "pha glow lip exfoliant": "Lip Exfoliant",
    "suns": "Lip Sunscreen",
    "sunscreen": "Lip Sunscreen",
    "sun glow protect": "Lip Sunscreen",
    "sun glow protect lip sunscreen": "Lip Sunscreen",
})

_PFVM_SHORT: Final[Mapping[str, str]] = MappingProxyType({
    "Ambition Power": "Ambition",
    "Classy Power": "Classy",
    "Heart Power": "Heart",
    "Honest Power": "Honest",
    "Kind Power": "Kind",
    "Smart Power": "Smart",
})

FAMILIES: Final[Tuple[Family, ...]] = (
    Family(
        name="Glow Up Tint",
        shades=(
            "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
            "Gorgeous", "Happy", "Incredible", "Joyful", "Strong",
        ),
        aliases=("glow up tint", "liptint", "lip tint", "gut"),
        shade_aliases=_GUT_ALIASES,
        singles_order=(
            "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
            "Gorgeous", "Happy", "Incredible", "Joyful", "Strong",
        ),
        # Marketplace ordinal order: Strong (09) precedes Happy (10).
        display_order=(
            "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
            "Gorgeous", "Strong", "Happy", "Incredible", "Joyful",
        ),
        cross_order=(
            "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
            "Gorgeous", "Strong", "Happy", "Incredible", "Joyful",
        ),
    ),
    Family(
        name="Swipe To Glow",
        shades=("Brunch", "Date", "Holiday", "Party", "School", "Work"),
        aliases=("swipe to glow", "lipgloss", "lip gloss", "stg"),
        singles_order=("Brunch", "Date", "Holiday", "Party", "School", "Work"),
        display_order=("Date", "Work", "School", "Brunch", "Holiday", "Party"),
        cross_order=("Date", "Work", "School", "Brunch", "Holiday", "Party"),
    ),
    Family(
        name="Power Frosted Velvet Matte",
        shades=(
            "Ambition Power", "Classy Power", "Heart Power",
            "Honest Power", "Kind Power", "Smart Power",
        ),
        aliases=("power frosted velvet matte", "power frosted", "pfvm"),
        shade_aliases=_PFVM_ALIASES,
        singles_order=(
            "Ambition Power", "Classy Power", "Heart Power",
            "Honest Power", "Kind Power", "Smart Power",
        ),
        display_order=(
            "Kind Power", "Honest Power", "Classy Power",
            "Smart Power", "Heart Power", "Ambition Power",
        ),
        cross_order=(
            "Kind Power", "Honest Power", "Classy Power",
            "Smart Power", "Heart Power", "Ambition Power",
        ),
        # Intra-family bundles drop the " Power" suffix: 'Kind + Honest'.
        short_shade=_PFVM_SHORT,
    ),
    Family(
        name="Tinted Jelly Balm",
        shades=(
            "Bunny Pink", "Wild Mauve", "Nudy Caramel",
            "Spill Nude", "Red Babe", "Hippie Rose",
        ),
        aliases=("tinted jelly balm", "jelly balm", "tjb"),
        shade_aliases=_TJB_ALIASES,
        singles_order=(
            "Bunny Pink", "Wild Mauve", "Nudy Caramel",
            "Spill Nude", "Red Babe", "Hippie Rose",
        ),
        display_order=(
            "Bunny Pink", "Wild Mauve", "Nudy Caramel",
            "Spill Nude", "Red Babe", "Hippie Rose",
        ),
        cross_order=(
            "Bunny Pink", "Wild Mauve", "Nudy Caramel",
            "Spill Nude", "Red Babe", "Hippie Rose",
        ),
    ),
    Family(
        name="The Bloom Perfect Matte Lipstick",
        shades=("Peony", "Gerbera", "Daisy", "Tulip", "Orchid", "Dahlia"),
        aliases=("the bloom perfect matte lipstick", "the bloom", "bloom", "tb"),
        singles_order=("Peony", "Gerbera", "Daisy", "Tulip", "Orchid", "Dahlia"),
        display_order=("Peony", "Gerbera", "Daisy", "Tulip", "Orchid", "Dahlia"),
        cross_order=("Peony", "Gerbera", "Daisy", "Tulip", "Orchid", "Dahlia"),
    ),
    Family(
        name="Over The Glaze",
        shades=(
            "Over Cute", "Over Drama", "Over Hype",
            "Over Lovie", "Over React", "Over Slay",
        ),
        aliases=("over the glaze", "lip vinyl", "otg"),
        shade_aliases=_OTG_ALIASES,
        singles_order=(
            "Over Cute", "Over Drama", "Over Hype",
            "Over Lovie", "Over React", "Over Slay",
        ),
        # NOTE: intra-family pairs for this family are NOT a clean upper
        # triangle -- use OTG_INTRA_BUNDLE_LABELS instead of generating them.
        display_order=(
            "Over Cute", "Over Lovie", "Over Slay",
            "Over Hype", "Over React", "Over Drama",
        ),
        cross_order=(
            "Over Cute", "Over Slay", "Over Lovie",
            "Over Hype", "Over React", "Over Drama",
        ),
    ),
    Family(
        name="Lipcare",
        shades=("Lip Moist", "Lip Exfoliant", "Lip Sunscreen"),
        aliases=("lip care", "lipcare"),
        shade_aliases=_LIPCARE_ALIASES,
        singles_order=("Lip Moist", "Lip Exfoliant", "Lip Sunscreen"),
        display_order=("Lip Moist", "Lip Exfoliant", "Lip Sunscreen"),
    ),
)

# 'Bundling Over The Glaze' is hand-ordered in the reference workbook and does
# not follow the upper-triangle rule. One label also drops the 'Over ' prefix
# ('Over Cute + Lovie'). Supplied verbatim rather than generated.
OTG_INTRA_BUNDLE_LABELS: Final[Tuple[str, ...]] = (
    "Over Cute + Lovie",
    "Over Cute + Over Drama",
    "Over Cute + Over Hype",
    "Over Cute + Over React",
    "Over Cute + Over Slay",
    "Over Lovie + Over Slay",
    "Over Lovie + Over Drama",
    "Over Lovie + Over Hype",
    "Over Lovie + Over React",
    "Over Slay + Over Hype",
    "Over Slay + Over React",
    "Over Slay + Over Drama",
    "Over Hype + Over Drama",
    "Over Hype + Over React",
    "Over React + Over Drama",
)

# Report group names in emission order, exactly as the reference workbook
# writes them. Two carry trailing spaces from manual entry; retained here
# because these are matched as group keys, not generated labels.
PRODUK_GROUP_ORDER: Final[Tuple[str, ...]] = (
    "Glow Up Tint",
    "Bundling Glow Up Tint",
    "Swipe To Glow ",
    "Bundling Swipe To Glow ",
    "Power Frosted Velvet Matte",
    "Bundling Power Frosted Velvet Matte",
    "Tinted Jelly Balm",
    "Bundling Tinted Jelly Balm",
    "The Bloom Perfect Matte Lipstick",
    "Bundling The Bloom Perfect Matte Lipstick",
    "Over The Glaze",
    "Bundling Over The Glaze",
    "Lip Moist",
    "Lip Exfoliant",
    "Lip Sunscreen",
    "Bundling Lipcare",
)

FAMILY_BY_NAME: Final[Mapping[str, Family]] = MappingProxyType(
    {family.name: family for family in FAMILIES}
)

# Tinted Jelly Balm ships in a coloured case. This is SKU metadata for
# traceability, NOT a reporting dimension: TJB report totals aggregate by shade
# across every case colour. Verified against the reference workbook -- shade
# "Bunny Pink" = 15 units spanning four distinct case colours, reported as ONE
# row -- and its three n x m x 3 case grids (324 rows) are empty scaffolding
# that has never carried data.
#
# The list is therefore NOT exhaustive and does not need to be: new colours
# (e.g. "Buttered Yellow", "Matcha Strawberry") are safe to leave out because
# the shade total already includes their sales. Never use this to expand a grid.
CASE_COLORS: Final[Tuple[str, ...]] = (
    "Fizzy Pop", "Sweetie Pop", "Cherry Pop", "Buttered Yellow", "Matcha Strawberry",
)

PACKAGING_TOKENS: Final[Tuple[str, ...]] = (
    "random keychain",
    "tanpa keychain",
    "free keychain",
    "keychain",
    "aplikator",
    "default",
    "tidak boleh ecer",
)

def _build_shade_lookup() -> Mapping[str, Tuple[str, str]]:
    lookup: Dict[str, Tuple[str, str]] = {}
    ambiguous: set[str] = set()

    for family in FAMILIES:
        for shade in family.shades:
            lookup[shade.casefold()] = (family.name, shade)

    for family in FAMILIES:
        for raw, canonical in family.shade_aliases.items():
            key = raw.casefold()
            if key in lookup or key in ambiguous:
                continue
            lookup[key] = (family.name, canonical)

    return MappingProxyType(lookup)

SHADE_LOOKUP: Final[Mapping[str, Tuple[str, str]]] = _build_shade_lookup()

def resolve_shade(token: str, *, family: Optional[Family] = None) -> Optional[Tuple[str, str]]:
    """Resolves a cleaned raw shade token to (family_name, canonical_shade)."""
    key = token.casefold().strip()
    if not key:
        return None

    if family is not None:
        for shade in family.shades:
            if shade.casefold() == key:
                return (family.name, shade)
        alias = family.shade_aliases.get(key)
        if alias is not None:
            return (family.name, alias)

    return SHADE_LOOKUP.get(key)
