# 0.3.19: PDF-only long resource reading

Short-lived `feat/pdf-budget-reading` continues 0.3.18. Not a release/deployment.
The PDF format selects a tiny `src/pdf/index.html.j2` entry that enables a
presentation flag. All formats still share Q15's data bindings and answer logic.
Q15 captures each original fragment once in namespaces and keeps the original
table output. Only PDF may replace eligible long rows with separate tables:
original column labels and resource identity in a repeating `thead`, original
purpose and allocation across all three columns. Short runs remain normal tables.
HTML, Word, ODT and LaTeX keep the original path; Word Lua/reference are untouched.

`src/budget-reading.html.j2` contains no translatable prose or KM paths. It moves
captured title/purpose/budget/funding fragments, never reconstructs or edits them.
Each resource's full path remains one ownership marker on its new table; metadata
is stored once, with the renderer repeating the header on continuation pages.

Conservative eligibility: <=32 resources, 12–160 purpose/allocation paragraphs,
<=400 characters per paragraph and <=30000 total plain-text characters. Permit
simple paragraphs, inline emphasis/code/links and at most one list of <=8 items.
Header text is limited to 80/80/100 characters, <=3 paragraphs and simple markup;
unknown tags, images, forced breaks, nested tables/lists, long/linked funding or
missing metadata retain the original row. These are shape/height hints, not a
general HTML parser or universal layout guarantee. No fallback discards data.

The bilingual pipeline resegments Q15 translation units. Eight unmatched units
are rebound to the same reviewed wording, not rewritten. Chinese owned allocation
paragraphs lose source indentation; compare only that outer space and structural
inter-block indentation, never authored paragraph content. Native Word XML and
control pagination must still remain identical. English non-PDF output is checked
against the frozen 0.3.18 Q15 source (`0945a807...`) in tests/fixtures.

Tests cover 28 matrices, including exact thresholds, missing answers/zero values,
rich inline content, same titles/different resource paths, short-long mixtures,
32/33 rows and multiple projects. An independent HTML oracle verifies exact moved
fragments. The pinned worker probe checks full-width cells and repeating identity;
full native DSW exports and visual inspection remain required in the Chinese repo.

Future upgrades must review the PDF entry, capture scope, translated bindings,
semantic ownership and each format's rendered files. Do not blindly merge upstream
Q15 or maintain a second Chinese implementation. Update the exact English source
lock only after the bilingual and native regressions pass.
