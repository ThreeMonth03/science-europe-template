# Bounded long-budget Word reading (0.3.17)

Only Word Lua and the build-time reference preparation change. HTML/Jinja,
translation wording, PDF CSS, fonts, margins and existing styles stay unchanged.
The official baseline remains 1.30.1; both repos use the short-lived
`feat/long-budget-reading`, and Chinese locks the exact English commit.

For a long resource purpose, keep the translated column headings plus the
original resource name, amount and funding cells in a two-row repeating table
header. Put the existing purpose blocks into separate full-width, three-column-
spanning body rows. Adjacent short resources remain in their original compact
tables. Do not add summaries, duplicate stored costs, force page breaks, flatten
author paragraphs or rewrite any content. Repeated headers are display context,
not additional budget entries. The reference adds only `Pilot Long Budget`
(ID `PilotLongBudget`): based on Table, with inner horizontal rules removed and
the existing conditional header formatting copied explicitly.

The Lua validates the entire resource table before editing. Require three
columns, one header row and body, no footer/caption/spans, 1–32 resources and
an original all-bold resource title (at most 160 width units). Metadata permits
at most three paragraph units, 80 width units for amount and 160 for funding.
No forced line breaks, nested tables/lists, images, raw content, headings,
unknown custom styles or identified Divs. Preserve inline emphasis, links,
code and wrapper attributes. Purpose units are at most 800 width units;
flat bullet lists at most eight items and 800 units. At least 12 purpose units
trigger expansion; above 160 units the old layout is retained. CJK codepoints
count twice. These are conservative guards, not universal font-metric proofs.

The block/table API is documented in [Pandoc's Lua reference](https://pandoc.org/lua-filters.html#creating-a-table).
Tests use the pinned worker's actual Pandoc, not an assumed version: 28 new
cases (9 accepted, 19 rejected), with independent exact expected ASTs, plus the
existing 24 short-budget cases. The new probe disables only this handler for
its baseline; historic native DOCX and PDF comparisons remain separate.

Keep synthetic `preservation-complete`, `budget-long` and `budget-many` inputs
unchanged. Verify the long DOCX has each original paragraph, run, list, link,
amount and funding source in its original resource; every page containing an
identified long-purpose paragraph must also contain that resource's metadata.
The budget heading must have the first resource and purpose on its page.
Short/many-case body XML and pagination must match 0.3.16. Compare all fifteen
HTML questions and native PDF bodies/pages unchanged. Do not weaken prior
oracles or alter archived 0.3.16 evidence for the new layout.

LibreOffice preview is not Microsoft Word acceptance. Long or complex inputs
outside the guards retain known old defects. Stock Markdown table handling,
full Chinese prose review and full DMP acceptance remain separate blockers.
