# Q11 adjacent missing-information panels, 0.3.30

Print/PDF only: join the visual borders of exactly three kinds of adjacent pairs:
archive payer + minimum period; extension authority + basis; format + media
migration. Each remains a separate paragraph with its original wording, fact ID,
status, font size and line height. No Jinja, translation, Lua or Word-reference
change. Screen HTML and editable Word retain their existing layout.

The selector is restricted to the project-wide archive policy inside Q11 and
two plain, missing-status paragraphs. Intervening answers, author blocks,
other-arrangement labels, unknown facts, needs-review or explicit-no states
prevent a match. Each pair has an outer border and two unchanged paragraphs;
only internal borders, wrapper margins and internal padding change. A bounded
two-prompt pair stays together; never keep the whole archive section together.

Tests exercise all 64 combinations of the six controlled missing fields, with
negative selector mutations. Pinned-engine checks cover print versus screen,
page-end placement, exact body text/wrapping, font/line-height preservation and
contiguous borders. Each supported pair is below 200 px in those fixtures.
The test also checks generated footers separately from body text.

This is a presentation experiment, not evidence that answers are complete or
that all Science Europe obligations/Microsoft Word versions are accepted.
Native bilingual comparisons are archived in the Chinese repository.
Use short-lived `fix/archive-gap-panels` branches and a full English commit lock
in the Chinese pipeline; upstream remains 1.30.1. A future changed prompt or
markup requires re-running the fixed-engine and native pagination checks.
