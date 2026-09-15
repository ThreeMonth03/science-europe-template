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
