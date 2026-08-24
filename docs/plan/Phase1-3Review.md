# Phase 1-3 Implementation Review

**Reviewed:** `backend/` as of end of Phase 3 (18 source files, 5 test files, 152 tests).
**Method:** Ran the suite, then independently re-derived results from
`sample_data/` rather than trusting the assertions.
**Verdict:** **Phase 1-3 is correct and can proceed to Phase 4.** Two data-quality
defects and three test-rigour gaps to address; none block Phase 4.

---

## 1. Verified Working

The suite passes 152/152. More importantly, I re-derived the numbers
independently and the transformation is genuinely exact:

| Check | Result |
| --- | --- |
| Shopee variants matched vs golden | **102 / 102 exact** (qty *and* revenue) |
| TikTok variants matched vs golden | **92 / 92 exact** |
| Golden non-zero rows not produced | **0** on both platforms |
| Fold-back `Dynamic` | qty `99`, rev `6,982,917` — **exact** |
| Fold-back `Energic` | qty `605`, rev `42,333,630` — **exact** |
| Revenue conservation (adapter -> transform) | **0 delta** on both platforms |
| Parent-row pruning | 295 of 1061 pruned, 766 retained — **exact** |

The plan's Phase 3 goal was 22/22. The actual result is **102/102 and 92/92**,
covering every non-zero row in the reference workbook, not just the Glow Up Tint
sample. That is a materially stronger result than the plan asked for.

**Revenue conservation is the headline.** Transform in/out revenue is
byte-identical on both platforms, while quantity rises by exactly 6 on Shopee
and 0 on TikTok — consistent with the fold-back `x2` rule firing on the three
non-zero same-shade 2-packs and nothing else. No revenue leaks anywhere in the
pipeline.

Architecture notes worth keeping: `domain/` cleanly separated from `modules/`,
`TransformationWarning` surfacing unmapped tokens instead of silently dropping
them, and `golden_totals.json` holding all 181 rows rather than only the 22
that were strictly required.

---

## 2. RESOLVED BY SCOPE — Dash Variants Are Out Of Reporting Scope

> **Scope decision (accepted):** Phase 1-5 transforms raws into the golden-file
> report only. Rows that the golden workbook does not report are ignored rather
> than reconciled. This section is retained because the *implementation* still
> needs an explicit exclusion, and because verification showed the exclusion is
> **required for correctness**, not merely permitted.

**180 records** exit the Shopee transformer with `clean_variant == '-'`
(TikTok: 0). They fall into two classes, both unreported in golden:

| Class | Records | Revenue |
| --- | --- | --- |
| In-catalog family, variant-less listing | 163 | Rp 4,950 |
| Out-of-catalog product (Body Toner, Face Toner, Lippie Serum, Blurring Powder, deleted listings) | 17 | Rp 0 |

### Excluding them is required, not optional

The single non-zero dash row is `Tinted Jelly Balm`, qty 1, Rp 4,950. Verified
against golden:

| | qty | revenue |
| --- | --- | --- |
| Golden TJB (`C110:C115`) | **24** | **2,234,703** |
| Our TJB shade rows | **24** | **2,234,703** |
| If dash row were included | 25 | 2,239,653 |

**Including it would break the golden match.** The analyst's `=SUM(C110:C115)`
covers exactly the six named shades, so a `'-'` row has no cell to occupy and its
value must not reach any total.

### Required implementation

Exclude at the adapter or transformer boundary:

- Drop records whose `clean_variant` is `'-'` or empty.
- Keep a counter (e.g. `skipped_unreported`) so the excluded row count and
  revenue remain auditable rather than vanishing silently. Rp 4,950 excluded on
  purpose is fine; Rp 4,950 excluded invisibly is not.
- Add a test asserting no output record has `clean_variant in ('-', '')`.

Out-of-catalog products (`Infused Body Toner with AHA`, `Strawflower Balancing
Face Toner`, `Lippie Serum 2.0`, `Instant Blurring Effect Powder`, and two
`Tidak dapat memperoleh informasi produk karena penghapusan` rows) are likewise
out of scope — the report is lip-category only. They carry zero revenue in this
period, but a future period may not, so the same counter should cover them.

---

## 3. RETRACTED — Case Colours Are Not A Reporting Dimension

> **This section originally flagged two unknown case colours as a defect with
> "Rp 5.4M at risk". That was wrong.** The correct domain rule, confirmed by
> the reviewer and then verified against the data: **Tinted Jelly Balm sums are
> aggregated by shade, ignoring case colour entirely.** Case colour is a SKU
> attribute, not a reporting axis. What follows is the verification, kept
> because it settles the question and has consequences for Phase 5.

### Verification

Golden `Produk S` single-shade rows equal the raw sums across **all five** case
colours — including the two the catalog does not know about:

| Shade | Golden (qty, rev) | Raw summed over all cases | Match |
| --- | --- | --- | --- |
| Bunny Pink | 15, 1,370,596 | 15, 1,370,596 | **exact** |
| Wild Mauve | 3, 277,674 | 3, 277,674 | **exact** |
| Nudy Caramel | 0, 0 | 0, 0 | **exact** |
| Spill Nude | 0, 0 | 0, 0 | **exact** |
| Red Babe | 4, 375,056 | 4, 375,056 | **exact** |
| Hippie Rose | 2, 211,377 | 2, 211,377 | **exact** |

`Bunny Pink` is decisive: its 15 units span `Sweetie Pop` (7), `Cherry Pop` (4),
`Fizzy Pop` (2) **and `Buttered Yellow` (2)** — an unmapped colour. Golden
reports 15. So the analyst aggregated across every case colour without
distinguishing them, and unknown colours cost nothing.

**No revenue is at risk.** Our pipeline already produces all six TJB shade
totals exactly (verified). The unmapped-token warnings are cosmetic noise, not
lost money.

### Consequence: the `n x m x 3` grid expansion is dead code

Since case colour is not a reporting dimension, the case-colour grid produces
only rows that can never carry data. Verified in the reference workbook:

| Group (`Produk 2 T`) | Rows | Non-zero |
| --- | --- | --- |
| Bundling Over The Glaze & Tinted Jelly Balm | 108 | **0** |
| Bundling Power Frosted & Tinted Jelly Balm | 108 | **0** |
| Bundling Swipe To Glow & Tinted Jelly Balm | 108 | **0** |

**324 rows of scaffolding, none populated.** And in the raw exports there are
**zero** cross-family TJB bundle rows on either platform — the product simply is
not sold that way.

### Revised recommendation

1. **Do not extend `CASE_COLORS`.** Leave it as-is or delete it; either way it
   must not drive grid expansion.
2. **`generate_cross_family_grid(..., include_case_colors=True)` can be dropped
   or left unused.** Under the agreed sparse-output rule it emits nothing anyway,
   so this is already harmless — but carrying an unused `x3` code path invites a
   future contributor to "fix" it back on.
3. **Keep `case_color` on `TransactionItem`.** It is accurate SKU-level
   provenance and costs one nullable column. It simply must never appear in a
   `GROUP BY` for report output.
4. **Reverse the Phase 4 storage note:** the earlier guidance to group by
   `(product_group, clean_variant, case_color)` is **wrong for reporting**.
   Variant-level analytics should group by `(product_group, clean_variant)`
   only. Grouping by case colour would split `Bunny Pink` into four rows where
   golden expects one.
5. **Silence the token warnings** by registering `Buttered Yellow`,
   `Matcha Strawberry`, and the truncated forms (`Fizzy`, `Sweetie`, `Cherry`,
   `Matcha`, `But Yellow`) as *recognised, ignorable* packaging-style tokens —
   the same treatment as `Random Keychain`. That drops Shopee warnings from 220
   to ~180 (all `'-'`, see §2) and TikTok from 15 to 0, restoring the warning
   channel as a real signal.

### Why this matters beyond TJB

This is worth flagging clearly for Phase 4: **`case_color` in a reporting
`GROUP BY` is now a known-wrong pattern.** It was recorded as a requirement in
`sqlite-analytics-specialist/SKILL.md` and `docs/specs/storage-analytics-engine.md`
based on my earlier inference from the 108-row block. Both need correcting
before the repository work begins, or Phase 4 will implement the split.

---

## 4. Test Rigour — Three Gaps

The tests are real, not stubs — I confirmed
`test_shopee_transformation_against_golden_totals` genuinely loads the raw file,
runs the adapter and transformer, and asserts qty *and* revenue per variant. But
three things weaken the guarantees.

### 4.1 The assertion floor is far below actual performance

```python
assert matched_count >= 22, f"Matched {matched_count} Shopee variants"
```

Actual matched count is **102** (Shopee) and **92** (TikTok). A regression that
silently dropped 79 Shopee variants would still pass.

**Fix:** assert the exact expected count, or `== len(non_zero_golden_rows)`.
Cheap change, large increase in protection.

### 4.2 Zero-value golden rows are never asserted

```python
if expected_qty > 0 or expected_rev > 0:
    ...assert...
```

Rows that golden reports as zero are skipped entirely. Since ~44% of golden rows
are zero, a bug that **fabricated** revenue on a should-be-zero variant would
not be caught.

**Fix:** assert those rows are absent from output, or present with zero. This is
the reverse-direction check that catches over-production.

### 4.3 `conftest.py` skips instead of failing

```python
if not fixtures_path.exists():
    pytest.skip("golden_totals.json fixture not generated yet")
```

If the fixture is ever deleted or a path changes, the two most important tests in
the suite report **skipped** — which reads as green in CI summaries.

**Fix:** `pytest.fail()`, or let the `open()` raise. The fixture is committed and
is a hard dependency, not an optional one.

### 4.4 Missing conservation assertion

The strongest property I checked is not tested at all: **revenue in == revenue
out** across the transform. It is a one-line invariant that would catch an entire
class of future bug.

**Fix:** add to `test_transformer.py`:

```python
def test_revenue_is_conserved_through_transform(raw_shopee_path):
    raw = ShopeeAdapter().adapt(extract_spreadsheet_rows(raw_shopee_path)[1])
    out = transform_records(raw)
    assert sum(r.revenue for r in out.records) == sum(r.revenue for r in raw)
```

---

## 5. Smaller Notes

| # | Note |
| --- | --- |
| 1 | Adapter output is 951 rows from 1061 total with 295 pruned — meaning 185 rows are dropped somewhere besides parent pruning. Worth a one-line comment or counter explaining where, so it is auditable rather than mysterious. |
| 2 | 220 warnings on a clean run is high enough that real signal will be missed. Once §2 and §3 are fixed the count should fall to near zero; consider asserting a maximum in the test suite. |
| 3 | `TransformationWarning` carries `product_title` and `unmapped_tokens` but not `qty_sold` / `revenue`. Adding them would let a caller quantify at-risk money directly instead of re-joining. |
| 4 | `test_fixtures.py` (41 lines) validates the fixture itself — good practice, worth keeping. |
| 5 | `normalizer.py` is 575 lines, the largest module by a wide margin. Not a problem now; if it grows further, the token-splitting and alias-resolution concerns are the natural seam. |
| 6 | No `.venv` in `backend/`; tests run against system Python 3.13. Fine locally, but pin an environment before packaging so PyInstaller resolves the same interpreter. |
| 7 | **Post-review finding (2026-08-25):** `PRODUK_GROUP_ORDER` carries workbook-leftover trailing spaces on `Swipe To Glow ` / `Bundling Swipe To Glow `, which propagate into 109 records' `product_group` via `_CANONICAL_GROUP_MAP` while `grid.py` and the golden oracle use clean names — the grid left-join will orphan these unless rstripped on both sides. Now a **required** Phase 4 item in [ImplementationPlan.md](ImplementationPlan.md). |

---

## 6. Readiness For Phase 4

**Proceed.** Both original defect findings are now closed: §2 resolved by an
explicit scope rule, §3 retracted as a wrong inference.

Suggested ordering:

1. **Before writing the repository:** correct the `case_color` grouping guidance
   in `.agents/skills/sqlite-analytics-specialist/SKILL.md` and
   `docs/specs/storage-analytics-engine.md` (§3, revised recommendation 4).
   *(Already applied during this review — verify before relying on it.)*
2. **In Phase 4:** implement the §2 exclusion with an auditable counter, and
   register case-colour tokens as ignorable so the warning channel goes quiet.
3. **Before Phase 5:** tighten the four test gaps in §4. The exporter will be
   built against these tests; weak assertions now become weak guarantees later.

### Scope rule for Phases 1-5

**Target: reproduce the golden report. Anything the golden workbook does not
report is out of scope and excluded, not reconciled.**

Concretely this means: dash-variant rows, non-lip-category products, and case
colour as a dimension are all excluded. Excluded volume must still be *counted*
so it can be reviewed, but it never reaches a report figure. Broader
reconciliation — accounting for every rupiah in the raw export — is a separate
concern for a later phase, if wanted at all.

---

## 7. Reviewer Note

Two findings in the first draft of this document were wrong, in different ways.

**§3 was a factual error.** I inferred from the golden workbook's 108-row block
that case colour was a third reporting dimension, and flagged two unknown
colours as a defect with "Rp 5.4M at risk". The data says otherwise: golden
single-shade totals equal raw sums across *all* case colours, and all 324
case-colour grid rows are empty scaffolding that has never carried data. The
108-row block looked like a specification; it was an unused template artifact.

That error had already propagated into six files (`analytics_queries.sql`,
two `SKILL.md` files, `schema_models.py`, and three specs), all of which
mandated grouping by `case_color`. Had Phase 4 been built to that spec,
`Bunny Pink` would have split into four rows where the report expects one.
All six are now corrected.

**§2 was correct as an observation but wrong in framing.** I called it a defect
requiring a decision; it is really a consequence of report scope. Verification
made this sharper than the original framing: excluding the dash row is not just
acceptable, it is **necessary** — including it would push golden's TJB total
from 24 to 25 units.

The general lesson for the remaining phases: structure present in a
hand-maintained workbook is not evidence that the structure is used, and a row
present in the raw export is not evidence that it belongs in the report.
