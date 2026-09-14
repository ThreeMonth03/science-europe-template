# 0.3.2 quality-reading experiment

Based on custom 0.3.1, still pinned to official Science Europe 1.30.1. Work on
`feat/quality-reading`; this is not a released template or a new official baseline.

Q4 now uses one paragraph per instrument dataset for selected, fixed quality
methods. Q1 and Q4 include `src/quality-control.html.j2`, so answer selection,
missing/No handling and free-answer boundaries cannot drift between copies.
Each entry is a phrase with no final period; the surrounding sentence supplies
one terminal mark. The existing translation pipeline localizes `join(", ")` to
the Chinese enumeration separator and translates the whole surrounding sentence.
No separate Chinese conditionals, CSS-generated punctuation, runtime LLM, or new
conversion-tool patch is needed. Authored Markdown is not joined or normalized.

Q8 and Q14 gain output-empty fallbacks. These do NOT prove every required topic
or every contributor has been covered; partially rendered sections still need
a later requirement-level audit. The warning says the document lacks the detail,
not that the questionnaire must have been left blank.

Validation includes all 128 selected/not-selected fixed-method combinations in
Q1/Q4, unknown versus No, other-only methods, missing other details, unnamed
datasets, empty legal output and unmatched/unnamed contributors. New synthetic
`quality-rich` and `quality-partial` fixtures keep older fixture bytes unchanged.
The rich example adds a second dataset and twenty authored paragraphs with a
Markdown list, decimal number and version identifier to catch unsafe joining.

The binding audit now reads all Jinja files under `src`, including this new shared
helper. Q4 and the helper are critical upstream overlaps. An upstream upgrade
must reconcile behavior here and rerun both language/format checks, not only
resolve the deleted duplicate lines. No changes to PDF CSS, Word Lua, reference
styles or the separately tracked Markdown-table worker are part of this patch.

Run checks with the existing tool environment:

```sh
make check PYTHON=../dsw-document-template-tool/.venv/bin/python DSW_TDK=../dsw-document-template-tool/.venv/bin/dsw-tdk
../dsw-document-template-tool/.venv/bin/python scripts/generate_quality_fixtures.py
../dsw-document-template-tool/.venv/bin/python scripts/validate_pilot_fixtures.py
```

The last command uses only the isolated local DSW synthetic account. Chinese
repo review artifacts record the locked sources, exact formats, visual checks,
stock-worker table failures and outstanding release limitations.
