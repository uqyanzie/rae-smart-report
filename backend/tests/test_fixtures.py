from pathlib import Path
import json
import pytest

def test_golden_totals_structure(golden_totals):
    """Verify that golden_totals.json contains the expected structure and oracles."""
    assert "shopee_variants" in golden_totals
    assert "tiktok_variants" in golden_totals
    assert "active_contribution_ratio" in golden_totals
    assert "foldback_addends" in golden_totals
    
    # Active contribution ratio matches oracle
    assert abs(golden_totals["active_contribution_ratio"] - 0.05974791292) < 1e-10

    # Verify Glow Up Tint Active, Dynamic, Energic values in Shopee
    shopee_variants = {v["variant"]: v for v in golden_totals["shopee_variants"]}
    
    assert "Active" in shopee_variants
    assert shopee_variants["Active"]["qty"] == 365
    assert shopee_variants["Active"]["revenue"] == 25563604
    
    assert "Dynamic" in shopee_variants
    assert shopee_variants["Dynamic"]["qty"] == 99
    assert shopee_variants["Dynamic"]["revenue"] == 6982917

    assert "Energic" in shopee_variants
    assert shopee_variants["Energic"]["qty"] == 605
    assert shopee_variants["Energic"]["revenue"] == 42333630

    # Verify fold-back addends oracle
    addends = golden_totals["foldback_addends"]
    assert addends["Dynamic"]["revenue_addend"] == 139900
    assert addends["Energic"]["qty_addend"] == 10
    assert addends["Energic"]["revenue_addend"] == 654649

def test_directory_cleanliness(workspace_root):
    """Verify deprecated audit/review docs have been removed from docs/."""
    docs_dir = workspace_root / "docs"
    assert not (docs_dir / "SKILLS-REVIEW.md").exists()
    assert not (docs_dir / "SPEC-REVIEW.md").exists()
    assert not (docs_dir / "GRID-ALIGNMENT-GUIDE.md").exists()
