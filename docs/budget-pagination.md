# Bounded Word budget pagination (0.3.16)

Only the Word Lua changes. Do not change question wording, Jinja, translations,
PDF CSS, Word reference, fonts, page margins or author paragraph boundaries.
The official baseline stays 1.30.1. Both repos use the short-lived
`feat/budget-pagination`; Chinese locks the exact English commit.

The complete Chinese control has a budget-only eighth Word-preview page.
DOCX-only A/B tests show that compacting cell spacing alone does not fix it;
releasing cell keep rules splits a resource across pages. Neither is adopted.
Instead, for a short Q15 only, keep the overview paragraphs through its budget
heading with the table, using existing Pilot Lead/Pilot List Lead styles.
Do not insert explicit page breaks or restyle table cells. The goal is coherent
question/answer reading, not reducing the page count to seven.

Before any mutation the Lua validates the entire Q15 AST: exactly one project,
one three-column resource table with one header and one or two data rows, two
expected headings, no more than three flat bullet items or 24 paragraphs. Limit
the full text to 1,000 width units (CJK codepoints count twice) and each cell to
200 units and three paragraphs. Reject nested tables/lists, raw blocks, images,
math, links, code, extra headings, row/column spans and trailing prose. Only
plain text and emphasis/span inline wrappers are supported. Boundaries are
conservative layout guards, not a mathematical font-metric proof of fitting.

Long, many-row, multi-project and complex cases must retain the previous AST.
Tests compare actual worker Pandoc output and native DOCX/XML, not just Lua text.
All supplied text, inline formatting, lists, tables, amounts (including zero),
funding sources, links and old missing-answer prompts must remain unchanged.
Every HTML question and the native PDF body/pagination must match 0.3.15.
Same-fixture Word previews must show Q15 and the small budget on the same page;
long cases must still span pages. LibreOffice is not Microsoft Word acceptance.
This is an experiment, not whole-DMP acceptance or a production deployment.

## Current development repair: budget headings (2026-09)

The historical 0.3.16 rule above remains intact. The current Word-only Q15
marker lets `attach_budget_headings` move the original budget title and short
project labels into their own tables' repeating headers. It never edits answers
or moves a later project's budget under an earlier empty project. Long/rich
labels and unowned tables are excluded. HTML/PDF and translation wording do not
change; Chinese uses the same English Lua asset through the existing pipeline.

The final owned table needs an explicit empty 1pt paragraph: without it,
LibreOffice may extract text from a final row that is not actually painted.
A normal-sized empty paragraph instead creates blank tail pages in some long
cases. Only that empty structural paragraph is compacted; body styles stay intact.
The existing `probe_budget_word.py` also checks 21 current cases, without a new
CI job. Local 32-case bilingual/profile renders resolve six heading-only pages.
The separately reproduced full-cover blank page is handled by the current
heading-bound page break described below.
This repair is not a release or Microsoft Word acceptance.

## Current development repair: start of main content

The existing Word XML helper moves the standalone DMP page-break paragraph to
`pageBreakBefore` on the first section heading. It preserves that heading's
style, runs and bookmarks, and touches no cover or answer text. The submission
helper preserves the property when compacting an entirely unanswered section.
This avoids the empty break paragraph overflowing a full cover. The match is
limited to the generated DMP/first-section boundary; unrelated authored breaks
are untouched and unexpected native XML fails closed. Both languages share
these two existing Word assets; no translation, PDF, font or margin changes.
