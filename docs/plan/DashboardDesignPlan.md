# Upload Modal (Replaces Dedicated Upload Page)

Trigger upload from a button (e.g. in the header bar) that opens a modal containing the drag-and-drop dropzone. Remove the dedicated `Upload` item from the nav menu and its `/upload` route/page; keep the existing upload flow (`UploadDropzone`, `useUploadFlow`) but render it inside the modal.

- Modal opens over the current page; closing returns to the unchanged underlying view.
- Close on `Esc`, backdrop click, or an explicit dismiss button.
- Trap focus inside the modal and lock background scroll while open.
- Reset dropzone/draft state on close so re-opening starts clean.
- On successful ingest, close the modal and let the Dashboard refresh its batch list/data.

# Top Section & Batch Control

Compact Header Bar: Consolidate the batch selector, data types checklist, and action Export action button into a single horizontal strip.

Side-by-Side KPI Cards: If you display batch metadata (e.g., Variant rows, Total Units, Total Revenue, Unreported revenue), display them as a clean 3-to-4 card inline flex or grid row directly beside or beneath the batch selector to save vertical real estate.

Table Layout Without Pagination

Constrained Viewport Height: Instead of letting the entire page scroll indefinitely, set the table wrapper to h-[calc(100vh-theme(spacing.header))] with overflow-y-auto. This keeps the page layout static and predictable.

Sticky Header (thead): Use sticky top-0 z-10 bg-slate-50 (with a distinct bottom border) so headers never vanish when reviewing lower rows.

Sticky Key Column (th:first-child, td:first-child): If the essential columns cause horizontal overflow on smaller screens, freeze the primary identifier column with sticky left-0 z-20 and a subtle right border/shadow.

Data Alignment & Scanning Polish

Text: Align text left (items, descriptions, names).

Numbers & Financials: Right-align all quantities, unit costs, and total sums using tabular numbers (font-mono or tabular-nums) to keep decimal points aligned vertically.

Badges/Statuses: Center-align badge tags with muted pill backgrounds.

Row Trackability: Apply an alternating background (even:bg-slate-50/50) paired with hover:bg-blue-50/40 so tracking wide rows across columns remains effortless.

Batch Totals / Sticky Footer: If the report calculates cumulative batch totals, render a sticky tfoot at the bottom of the table so summary numbers are visible without having to scroll all the way down.
