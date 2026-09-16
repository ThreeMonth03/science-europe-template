# 0.3.26 short-budget Word column experiment

The Word entry enables a format-specific Q15 hint. It reuses the existing shared
short-table classifier (1–3 simple rows, bounded fragments, an owned missing
amount/currency prompt), passing `word=true`. Only the fixed opening table class
changes; answers, punctuation, paragraphs and missing-information wording remain
intact. PDF calls keep the default behavior; HTML does not enable either hint.

Pandoc's HTML reader drops the gap paragraph's fact attributes. The Lua filter
therefore must not guess eligibility from English/Chinese wording. It accepts
only the `word-short-budget` table inside Q15, validates the simple three-column
shape, and changes widths from 57/17/26 to 49/25/26. It does not alter font sizes,
paragraph styles, content, cell margins or page-break rules. Long/complex/many-row
and complete-budget controls keep their previous widths.

`probe_word_short_budget.py` exercises 46 cases including autoescape, actual
question output, rejected hints and pinned worker Pandoc AST/DOCX output.
`word_short_budget_contract.py` permits only the precise column-grid edit; it
rejects wording, styles, table structure and unrelated changes. Existing PDF,
long-budget and label probes remain active.

The Chinese repo supplies the frozen-DOCX width rehearsal, source/translation
scope check and native bilingual comparison. A LibreOffice preview is not
Microsoft Word acceptance. No new renderer, independent Chinese Jinja, engine
font patch, upstream upgrade, main merge or release is included.

Both repositories use the short-lived `fix/word-short-budget-widths` branch.
Chinese builds lock the exact English commit and tooling, not the branch name.
Future upstream Q15 capture or Pandoc changes must rerun the format-isolation,
translation, exact DOCX and native-output checks before integrating this change.
