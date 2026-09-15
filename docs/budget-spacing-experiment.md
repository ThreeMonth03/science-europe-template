# 0.3.18: bounded budget spacing

Continues `feat/long-budget-reading` (0.3.17, `b7327b9`) on the short-lived
`feat/budget-spacing` branch. Not an upstream merge, release, or deployment.

- PDF/HTML: release the existing whole-table keep only for owned Q15 resource
  tables whose purpose contains at least 12 direct blocks. Row count alone does
  not bound height. Short and many-short-row controls keep their existing rules.
- Word: only `PilotLongBudget` top/bottom cell margins change, 57 to 28 twips
  (2.85 to 1.4 pt). Keep the 0.3.17 full-width purpose rows, repeating resource
  identity, original paragraph boundaries, 10.5 pt type, and 1.2 line spacing.
- Jinja, Lua, KM bindings, answer states, and translated wording are unchanged.

The PDF rule is not a general long-answer classifier. Single huge paragraphs,
complex content, full-width PDF purpose layout, and repeating PDF resource
identity need separate experiments. Fewer pages is not itself acceptance.
Use the paired native artifacts and checks in the Chinese repository; disposable
HTML/DOCX rehearsals are diagnosis only. LibreOffice is not Microsoft Word.

The first native attempt exposed a selector-engine discrepancy: the leading
child combinator in `:has(> tbody > ...)` matched in SoupSieve, not the pinned
worker's engine. Use `:has(tbody > ...)` and keep `probe_budget_pdf.py` in CI:
it tests both matches and computed table break rules in worker WeasyPrint 68.1.
Never accept selector-library tests as native PDF proof. The failed native
attempt remains in the Chinese repository's local outputs; it is not promoted.

Chinese 0.3.18 must pin the exact English commit in `pipeline.yml`; it carries
no separate layout patch. Rebase/squash the feature branch only during an approved
integration, then update the Chinese lock and rebuild. Do not merge official
upstream into this experiment or use permanent language/version branches.
