# Backend Remediation Brief: Pre-Frontend Hardening

**Scope:** Findings from the Phase 0–6 review of `docs/plan/BackendImplementationPlan.md`.
**Baseline at time of review:** 193/193 tests green, `ruff` clean, `Produk S` / `Produk T` golden-file match reproduced.
**Status of this brief:** open. Every item below was reproduced by execution against `sample_data/`, not inferred from reading code.

**Why now:** three of these items change numbers the frontend will bind to (`grandTotalQty`, `contributionRatio`, `totalProducts`). Fixing them after the SPA reads those fields means changing the wire contract twice. Items R1–R5 should land before frontend work starts.

---

## Contents

| ID | Severity | Item | Primary file |
| --- | --- | --- | --- |
| R1 | High | Off-grid variants leak revenue past the audit tally | `backend/app/modules/storage/repository.py` |
| R2 | High | Fold-back accepts N>2 instead of raising | `backend/app/modules/transformer/foldback.py` |
| R3 | Medium | `variant_analytics` fan-out on untrimmed group keys | `backend/app/modules/storage/repository.py` |
| R4 | Medium | `/api/transform` returns 200 on platform mismatch | `backend/app/api/routes.py` |
| R5 | Medium | `/api/transform` and `/api/reports/batches` disagree | `backend/app/api/routes.py` |
| R6 | Medium | CSV delimiter sniffer is quote-blind | `backend/app/core/numeric.py` |
| R7 | Low | Asymmetric OTG catalog label is unreachable | `backend/app/domain/catalog.py` |
| R8 | Low | `FoldBackEngine(allowed_families=set())` reverts to default | `backend/app/modules/transformer/foldback.py` |
| R9 | Low | Query C end-date bound excludes the intended day | `backend/app/modules/storage/repository.py` |
| R10 | Low | `populate_grid` breaks past ~6,500 grid rows | `backend/app/modules/storage/repository.py` |
| R11 | Doc | Plan line 157 pruning counts are stale | `docs/plan/BackendImplementationPlan.md` |

---

## R1 — High: off-grid variants leak revenue past the audit tally

**Where:** `backend/app/modules/storage/repository.py:165` (`_GRID_LEFT_JOIN_TEMPLATE`), `repository.py:253-270` (`persist_batch` filters).

**Problem.** The grid population query is a `LEFT JOIN` from grid → transactions. Any persisted row whose `(product_group, clean_variant)` pair is absent from the catalog grid contributes to nothing — not the workbook, not the `skipped_unreported` tally. `persist_batch` only tallies two exclusion reasons: dash/empty variants and non-catalog groups. A record with a **catalog group** but an **off-grid variant label** passes both filters, gets inserted, and then silently fails to join.

This is the exact failure mode Execution Rule 2 exists to prevent: *"Excluded volume MUST be counted in an auditable tally so it is reviewable."*

**Reproduction** (`sample_data/raw/raw_tts_13_19_Jul26.xlsx`):

```
persisted        qty=11589  rev=660,533,024
grid Produk      qty=11575  rev=658,458,817
grid Produk 2    qty=   13  rev=  2,051,570
unaccounted      qty=    1  rev=     22,637   <- reaches no sheet, no tally
```

The orphan is `('Tinted Jelly Balm', 'Default')`, from the listing
`[Tidak Boleh Ecer] Brush Aplikator Raecca Tinted Jelly Balm [Aplikator Saja]`.
`tokenize_variant` drops `default` as packaging noise, `resolved_shades` comes back empty, and the fallback at `normalizer.py:359` uses `cleaned_var` = `"Default"` — a label the grid does not contain.

Shopee has an equivalent orphan at zero volume: `('Bundling Over The Glaze', 'Over Cute + Over Lovie')` (see R7).

**Severity rationale.** Rp 22,637 this period, but the magnitude is unbounded: any new listing whose variant string fails to resolve leaks by the same path, and the leak is invisible. A silent Rp 0 tally alongside a real discrepancy is worse than a loud failure.

**Secondary effect.** Query B (`product_group_summary`) and the workbook disagree for the same batch — Tinted Jelly Balm reports 42 units / Rp 3,247,402 from Query B versus 41 / Rp 3,224,765 in the sheet.

**Suggested fix.** Add a third exclusion bucket at the persistence boundary rather than letting the join swallow the row. Either:
- reject off-grid `(group, variant)` pairs in `persist_batch` into a new `skipped_off_grid: SkippedTally`, membership tested against `generate_full_produk_grid()`; or
- after `populate_grid`, diff persisted totals against grid totals and surface the residual as an explicit reconciliation figure.

The first is preferable — it keeps the "excluded volume is tallied at one boundary" invariant that `persist_batch` already establishes, instead of adding a second place where exclusion happens.

**Acceptance.** A test asserting that for both sample files, `sum(grid qty) + sum(all skipped tallies) == sum(persisted qty)` exactly, and the same for revenue. This invariant is what makes R1 non-recurring.

---

## R2 — High: fold-back accepts N>2 instead of raising

**Where:** `backend/app/modules/transformer/foldback.py:51-61`, and the 3-shade branch at `backend/app/modules/transformer/normalizer.py:532`.

**Problem.** Plan line 181 and the `FoldBackEngine` docstring (`foldback.py:18`) both require `ValueError` on multiplicity > 2. No such check exists — `foldback.py:52` carries a comment describing the intent, but no code implements it. A 3-pack same-shade row never reaches the fold-back path at all: it is captured by the `len(resolved_shades) == 3` branch in the normalizer, which never sets the fold-back flag.

**Reproduction:**

```
raw_variant='Dynamic, 05. Dynamic, Dynamic'  qty=3
-> product_group='Bundling Glow Up Tint'  clean_variant='Dynamic'
   qty_sold=3 (unchanged, no x2)  is_bundling=True  is_foldback=False
   in_grid=False
```

**Two consequences.** The plan's guardrail is absent, and the row lands on label `Dynamic` under group `Bundling Glow Up Tint`, which is not a grid key — so it also triggers R1 and disappears entirely.

**Severity rationale.** Latent, not active: the sample period contains no 3-pack. It becomes live the first period a 3-pack SKU ships, and the failure is silent rather than loud — the opposite of what the plan specified.

**Test gap.** `backend/tests/test_transformer.py:292` covers the *family scope* error only (`match="unverified family"`). No test covers multiplicity.

**Suggested fix.** Decide the intended behaviour first — the plan says raise, but a silently-wrong-label-then-vanish outcome suggests the normalizer branch was written without reference to the fold-back contract. Raising is the plan-conformant choice and surfaces the SKU for a verified rule. Implement the check where multiplicity is actually known (the normalizer, before the 3-shade branch), not only in `FoldBackEngine`, since the engine never sees these rows.

**Acceptance.** A test asserting `ValueError` on a same-shade N=3 input, plus confirmation that the resulting error message names the SKU and raw variant so the operator can act on it.

---

## R3 — Medium: `variant_analytics` fan-out on untrimmed group keys

**Where:** `backend/app/modules/storage/repository.py:68` (join), `:71-72` (`GROUP BY`).

**Problem.** The `rtrim()` normalizes only the join predicate. The `GROUP BY` still uses the raw `t.product_group` column plus the untrimmed `pt.total_product_qty`. When two spellings of the same group coexist, every variant fans out across every matching group total.

**Reproduction** (rows inserted directly, bypassing `persist_batch`):

```
input: ('Swipe To Glow', 'Date', qty 10), ('Swipe To Glow ', 'Work', qty 5)

Query A returns 4 rows instead of 2:
  group='Swipe To Glow'   var='Date'  qty=10  ratio=2.0000   <- ratio > 1, invalid
  group='Swipe To Glow'   var='Date'  qty=10  ratio=1.0000
  group='Swipe To Glow '  var='Work'  qty= 5  ratio=1.0000
  group='Swipe To Glow '  var='Work'  qty= 5  ratio=0.5000
expected: Date 10/15=0.6667, Work 5/15=0.3333
```

A `contribution_ratio` of 2.0 violates the 0–1 unit-share invariant that Phase 4's success criteria assert.

**Severity rationale.** Not reachable today — `persist_batch` strips keys on write. It becomes reachable via any write path that bypasses `persist_batch`: a direct ORM insert, a future importer, or a pre-existing database file created before the strip was added. The DB file is not versioned or migrated, so the last case is a real deployment scenario rather than a hypothetical.

Plan line 217 describes the `rtrim()` treatment as "defense-in-depth." As written it is the opposite: it converts a whitespace mismatch from a *missing row* (loud, obvious) into a *silently wrong ratio* (quiet, plausible-looking). Half-applied defense-in-depth is worse than none.

**Suggested fix.** Apply `rtrim()` consistently inside the CTE and the `GROUP BY`, or project `rtrim(product_group) AS product_group` in both the CTE and the outer select so the grouping key and the join key are the same expression. Audit Queries B, C and D for the same half-normalization while in the file.

**Acceptance.** A test inserting the two-spelling fixture directly via the ORM and asserting Query A returns exactly 2 rows with ratios summing to 1.0.

---

## R4 — Medium: `/api/transform` returns 200 on platform mismatch

**Where:** `backend/app/api/routes.py:248` (`adapter.adapt` called with no header validation).

**Problem.** Plan line 152 requires the adapter to "fail loudly with descriptive error if required ready-to-ship columns are missing." `validate_headers` exists on both adapters (`adapters.py:88`, `:120`, `:205`) but is only ever called from `backend/tests/test_ingestion.py` — never from production code. `adapter.adapt` uses `row.get(COL, default)` throughout, so missing columns degrade to zeros instead of raising.

**Reproduction** — a 3-column unrelated CSV declared as `SHOPEE`:

```
POST /api/transform -> HTTP 200
{'importBatchId': 'SHOPEE-2026-07-13-2026-07-19-5aa0db',
 'totalProducts': 0, 'grandTotalQty': 0, 'grandTotalRevenue': 0,
 'insertedCount': 0, 'skippedCount': 0, 'warningCount': 0}
```

The user gets a successfully-created empty batch. `errors.py:45` already maps `MissingRequiredColumnError` to 422 with code `MISSING_REQUIRED_COLUMN`; the mapping is simply never exercised.

**Severity rationale.** Straightforward user-facing correctness bug with a one-line fix and existing error plumbing. High likelihood of being hit — selecting the wrong platform in a dropdown is the single most probable user error in this UI.

**Suggested fix.** Call `adapter.validate_headers(headers)` at `routes.py:248` before `adapt`. Verify the raised exception type is in the `errors.py` handler map so the response is a 422 envelope and not a 500.

**Acceptance.** A test posting a mismatched file and asserting HTTP 422 with `code == "MISSING_REQUIRED_COLUMN"`, and asserting no batch was persisted.

---

## R5 — Medium: `/api/transform` and `/api/reports/batches` disagree

**Where:** `backend/app/api/routes.py:273-283` (transform response from `_reported_records`), `routes.py:303` → `repository.batch_history()` (Query D, raw `transaction_items` sums).

**Problem.** Same batch, two answers:

```
POST /api/transform    totalProducts=15  qty=11575  rev=658,458,817
GET  /api/reports/batches  totalProducts=21  qty=11589  rev=660,533,024
```

`TransformResponseDTO` deliberately mirrors the workbook (grid-intersected). `batch_history` deliberately mirrors storage. Both are defensible in isolation. The problem is that both DTOs inherit the same `BatchSummaryDTO` field names — `totalProducts`, `grandTotalQty`, `grandTotalRevenue` — so the two meanings are indistinguishable to a consumer. A frontend binding `grandTotalQty` displays a different number depending on which endpoint it last called, with nothing in the contract explaining why.

Note the 11,589 − 11,575 = 14-unit gap is R1's leak (1 unit) plus the 13 `Produk 2` cross-bundling units, which the standard-sheet boundary correctly excludes. Fixing R1 shrinks but does not close this gap; R5 is a contract-clarity issue independent of R1.

**Severity rationale.** No incorrect arithmetic — both figures are right for their own definition. The cost is frontend confusion and likely bug reports that are not bugs. Cheap to fix now, expensive after the SPA binds these fields.

**Suggested fix.** Pick one and make it explicit in the wire contract. Either rename the transform-response fields to signal the boundary (`reportedTotalQty`, `reportedTotalRevenue`, `reportedProductCount`), or have `batch_history` apply the same grid boundary and expose the raw figures as separately-named fields. The first is less invasive and keeps Query D's storage-level meaning intact for audit purposes. Per the `@fullstack-bridge-contract` skill, whichever is chosen must be reflected in the TypeScript interfaces at the same time.

**Acceptance.** A test asserting the two endpoints' same-named fields are equal, or that the field names differ — whichever the chosen resolution implies.

---

## R6 — Medium: CSV delimiter sniffer is quote-blind

**Where:** `backend/app/core/numeric.py:35-44` (`detect_csv_delimiter`).

**Problem.** The function counts raw character occurrences per line with no quote awareness. Indonesian marketplace exports commonly use `;` as the delimiter while product titles contain commas inside quoted fields. When a line has more commas-inside-quotes than real delimiters, detection flips.

**Reproduction** — 5-column `;`-delimited Shopee-shaped CSV with comma-rich quoted titles:

```
commas/line: 6
semis/line : 4
detect_csv_delimiter -> ','      (wrong)
csv.Sniffer          -> ';'      (correct)
```

Note the threshold matters: a 5-column file needs >4 commas per line to flip, which comma-rich RAE product titles (`"Raecca Glow Up Tint, Lip Tint, Lip & Cheek, Waterproof, Long Lasting, 2pcs"`) clear easily. A 2-column file flips at >1 comma. Narrower exports are more fragile, not less.

**Severity rationale.** `.csv` uploads only; both sample files are `.xlsx`, so this is unexercised today. The failure mode is a single-column parse, which currently surfaces as a silent empty batch (compounding R4) rather than an error.

**Suggested fix.** `csv.Sniffer().sniff(sample, delimiters=",;\t")` handles quoting correctly and is a near drop-in. It raises `csv.Error` when it cannot decide, so retain the current `,` default as the fallback on exception rather than propagating.

**Acceptance.** A table-driven test over `;`-delimited fixtures with comma-bearing quoted titles at 2-column and 5-column widths, following the existing `test_numeric.py` style.

---

## R7 — Low: asymmetric OTG catalog label is unreachable

**Where:** `backend/app/domain/catalog.py:171` (`OTG_INTRA_BUNDLE_LABELS[0]`), matching logic at `backend/app/modules/transformer/normalizer.py:438-445`.

**Problem.** `OTG_INTRA_BUNDLE_LABELS[0]` is `"Over Cute + Lovie"` — asymmetric, copied verbatim from the reference workbook. The OTG matching branch strips `"over "` from the whole label only, so it cannot bridge the gap between the resolved shade pair and the stored label:

```
raw='Ov Cute + Ov Lovie'      -> 'Over Cute + Over Lovie'  in_grid=False
raw='Over Cute + Over Lovie'  -> 'Over Cute + Over Lovie'  in_grid=False
raw='Over Cute + Lovie'       -> 'Over Cute + Lovie'       in_grid=True   (exact string only)
```

The Shopee export uses `Ov Cute + Ov Lovie` and golden reports it at 0 units, so Shopee currently matches by luck — zero volume hides the miss. TikTok spells it `Over Cute + Lovie` and hits the exact-match path.

**Severity rationale.** Zero impact this period. Any period where Shopee's `Ov Cute + Ov Lovie` sells a unit, that unit becomes an R1 orphan. All 14 other OTG pairs resolve correctly — this is the only asymmetric label.

**Suggested fix.** Note that `test_domain_catalog.py:115` pins `OTG_INTRA_BUNDLE_LABELS[0] == "Over Cute + Lovie"`, so this is a deliberate golden-fidelity choice, not a typo. Per Execution Rule 5, confirm with the report owner whether the workbook label is authoritative before changing it. If it is, fix the matching side: normalize both the resolved pair and the candidate label through the same per-token `Ov`/`Over` expansion before comparing, rather than relying on whole-label string equality. Fixing R1 first means this becomes a visible tally entry instead of a silent loss, which lowers its urgency.

---

## R8 — Low: `FoldBackEngine(allowed_families=set())` reverts to default

**Where:** `backend/app/modules/transformer/foldback.py:26`.

**Problem.** `allowed_families or self.ALLOWED_FAMILIES` — an explicit empty set is falsy, so the caller's intent is inverted:

```
FoldBackEngine(allowed_families=set()).allowed_families
-> frozenset({'Glow Up Tint'})
```

**Severity rationale.** No current caller passes an empty set. It is a latent trap for a future test that tries to assert "fold-back is disabled," which would silently pass while fold-back remained active.

**Suggested fix.** `if allowed_families is None`.

---

## R9 — Low: Query C end-date bound excludes the intended day

**Where:** `backend/app/modules/storage/repository.py:109` and `:126` (`period_end <= :end_date`).

**Problem.** SQLAlchemy's `DateTime` on SQLite stores text with a `.000000` microsecond suffix. The comparison is lexicographic, so the natural caller bound sorts below the stored value:

```
end_date=date(2026, 7, 19)                        -> 0 rows
end_date=datetime(2026, 7, 19, 23, 59, 59)        -> 0 rows
end_date=datetime(2026, 7, 19, 23, 59, 59, 999999)-> 1 row
end_date=date(2026, 7, 20)                        -> 1 row
```

`routes.py:254` stores `time(23, 59, 59)`, which is precisely the value that fails.

**Severity rationale.** No endpoint exposes Query C yet, so nothing is broken in production. It is a trap primed for whoever wires it up. `backend/tests/test_storage.py:381-384` documents the quirk in a comment and passes `999999` microseconds to work around it rather than fixing the cause — the test encodes the bug as expected behaviour.

**Suggested fix.** Normalize the end bound inside `_coerce_bound` so a bare `date` or an end-of-day `datetime` both resolve to an inclusive upper bound. Then simplify the test to pass the natural value.

---

## R10 — Low: `populate_grid` breaks past ~6,500 grid rows

**Where:** `backend/app/modules/storage/repository.py:426-441`.

**Problem.** Each grid row binds 5 parameters plus 2 fixed; SQLite's host-parameter ceiling is 32,766:

```
n=  813 params= 4,067 -> OK      (current Produk 2 grid)
n=5,000 params=25,002 -> OK
n=6,600 params=33,002 -> OperationalError: too many SQL variables
```

**Severity rationale.** ~8x headroom at current catalog size. Recorded so the limit is known rather than discovered. A third cross-family dimension, or adding case colour to the grid (currently and correctly excluded per Execution Rule 3), would blow past it.

**Suggested fix.** Either chunk the `VALUES` list, or add a comment at `populate_grid` documenting the ceiling and the 5-params-per-row arithmetic. A comment is proportionate to the current risk; chunking is only worth it if the catalog is expected to grow.

---

## R11 — Doc: plan line 157 pruning counts are stale

**Where:** `docs/plan/BackendImplementationPlan.md:157`.

**Problem.** The plan asserts "exactly 295 parent rows pruned from 1061 total rows (766 child rows)." The Shopee adapter returns 951 records, retaining 185 dash rows as standalone products. `backend/tests/test_ingestion.py:66-72` documents the deviation in comments and asserts 951.

The implementation behaviour appears correct — those dash rows are genuine single-variant listings, and the `persist_batch` boundary excludes the non-reportable ones later. The plan text is what is wrong.

**Suggested fix.** Update line 157 to the verified counts with a one-line note on why dash rows are retained at the adapter and excluded at the persistence boundary instead. Per Execution Rule 5, the discrepancy should be confirmed as intended before the text is rewritten.

---

## Also noted, no action proposed

These are correct-as-specified. Listed so they are conscious decisions rather than latent surprises.

- **`sanitize_integer` uses half-away-from-zero** (`sanitize_integer(2.5) == 3`), unlike Python's banker's `round`. Per spec, plan line 104.
- **`_BLANK_MARKERS` maps Excel error strings to `0.0`** (`numeric.py:25`), including `#div/0!`, `#value!` and `#ref!`. Reasonable for this data, but a genuinely broken source cell reads as zero revenue with no warning emitted. If source-file integrity ever becomes a concern, this is the place to add a warning channel entry rather than a silent coercion.
- **Query-parameter casing is mixed:** `?is_cross_bundling=` (snake_case) on the variants/products endpoints versus `?batchIds=` (camelCase) on export. The `@fullstack-bridge-contract` skill mandates camelCase for JSON bodies only, so this is not a violation — but the inconsistency will surface in the generated frontend client and is cheapest to settle before that client exists.

---

## Suggested sequencing

1. **R1 + R2 together.** Both are correctness issues on the same orphan-label path; R2's 3-pack row is an instance of R1's leak. Fixing R1 first gives R2 a visible failure mode to assert against.
2. **R4 + R6 together.** Both are input-validation gaps on the ingest path, and R6's failure currently hides behind R4's silent success.
3. **R3, R5.** Contract and query hygiene. R5 should precede frontend work.
4. **R7–R11.** Low-risk cleanup; R11 is documentation only.

## Verification

Each item above names its own acceptance test. Beyond those, the existing suite must stay green and the golden match must be preserved:

```powershell
pytest backend/tests/ -v
```

The `Produk S` / `Produk T` golden totals (Shopee 6,910 / Rp 525,973,986; TikTok 11,575 / Rp 658,458,817) are the regression anchor. Note that R1's fix is expected to *change* the reconciliation figures while leaving these workbook totals identical — if a golden total moves, the fix has crossed the Execution Rule 2 boundary and is wrong.
