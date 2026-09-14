# 0.3.8: Word rhythm, with unchanged answers

This is a style-only output experiment. All Jinja, translations, PDF CSS and the
Word Lua filter remain unchanged from 0.3.7. The source reference.docx binary is
also retained; the existing deterministic preparation step applies the styles.

| Style | 0.3.7 | 0.3.8 |
| --- | --- | --- |
| Normal / Body Text / First Paragraph | 1.4 relative lines, 4 pt after | 1.2 relative lines, 4 pt after |
| Compact (lists/table cells) | 1.4 relative lines, 4 pt after | 1.2 relative lines, 2 pt after |
| Heading 3 (question) | 12 pt before / 6 pt after | 12 pt before / 4 pt after |
| Heading 4–5 (subsection/dataset) | 12 pt before / 6 pt after | 8 pt before / 3 pt after |

Body type remains 10.5 pt. Heading sizes, paper size, margins, header/footer,
widow control, keep-with-next hints and authored paragraph boundaries do not
change. Relative spacing is retained instead of exact line height; mixed text
must remain expandable. A smaller page count alone is not acceptance.

The Chinese repo's `experiments/word-rhythm/rehearse.py` first changes only
`word/styles.xml` in copies of previously generated DOCX files. Every other ZIP
member must be byte-identical. These copies are style-isolation rehearsals, not
new DSW renders. Native candidate renders and package-bound checks are separate.

The complete Chinese 0.3.7 preservation example previews as 9 pages in
LibreOffice. The line-only rehearsal is 8 pages and the full rhythm rehearsal
is 7. This is a bounded observation, not a Microsoft Word pagination guarantee.

`prepare_layout.py` is now in the **high-risk Word-layout** upgrade category,
alongside the reference document and Lua filter. An upstream reference-style
change must rerun both languages, short/long answers, tables, missing prompts,
paragraph/character retention and visual review. English and Chinese use the
same semantic style roles rather than maintaining separate Jinja logic.

The package remains experimental. No runtime, KM, official upstream baseline,
release tags or production projects are changed by this iteration. The content
review in [selection-policy-review.md](selection-policy-review.md) deliberately
does not certify SE-5b coverage or activate a draft Taiwanese KM.
