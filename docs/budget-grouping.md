# 0.3.43: mixed-budget headers and row-safe large resource groups

Integrates the already tested bilingual package prototype into the shared
English source. Chinese continues through the existing translation pipeline;
no separate Chinese Jinja implementation or translation-tool change.

Three source files change: `budget-reading.html.j2`, `layout.css`, and
`word/pilot.lua`. Ordinary PDF groups use the existing bounded short-row helper;
long PDF bodies keep continuation identities and the final purpose/allocation.
The whole-table 32-resource cutoff becomes a 32-row ordinary-group bound.
Existing per-row limits remain; Word still rejects the complete transformation
if any table structure, cell or metadata fails its validation.

The source contract reverses precisely these changes to every byte of commit
`200fac5239051e1a877493c7d52c3a199964c718` (0.3.42), including unchanged
preparation and metadata except version. Prior hash gates and frozen archives
are retained. The old 28-case Word matrix remains available; the active grouped
variant adds large-table controls and validates 37 cases in Pandoc.

Provenance: companion Chinese repo review
`reviews/2026-09-21-large-resource-groups` (seal
`a4dc74ea334dfe5e4232e994e1c4955918f82284c9745baeaeec425b83b4c569`).
The tested Jinja and Lua bytes are frozen in unit tests. Native integrated
package parity and bilingual prepared-source projection are recorded there
separately from source verification.

This is an experimental paired revision, not deployment or whole-DMP acceptance.
English Word short rows can still split. Submission-preview notices are not yet
globally suppressed; authored text and missing-answer states must remain intact.
Microsoft Word, arbitrary real projects and full-document reading remain open.
