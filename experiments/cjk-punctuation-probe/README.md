# Q3 punctuation / sentence-spacing diagnostic prototype

**Finding: the sentence-list recipe is rejected for integration: no benefit.**
The locked translator's `_translation_tree/output_polish.py` already changes
`metadataSentences|join(" ")` to `join("")`. The first packaged Chinese run
correctly failed the expected-improvement gate. The follow-up oracle explicitly
checks that the old package already has the correct joined Chinese sentences,
and that the proposed recipe changes no rendered answer. Preserve that failed
trial as evidence; do not turn this recipe into a production change.

Production stays at 0.3.50 (`a2f97d9312b4ce811b92f5943944997638cc67b8`).
This short-lived branch contains a reversible one-file recipe, not a new
maintained Chinese Jinja fork. It must pass through the locked EN → ZH pipeline.

Two different effects must not be conflated:

- `）。` has no literal space: both are fullwidth punctuation in the bundled font.
- Q3's `metadataSentences|join(" ")` inserts ASCII spaces between owned sentences.

The recipe changes only that list's separator. Every sentence must start with a
Han character and end with `。`, with no HTML, or the old ASCII separator is kept.
It does not trim/rewrite any sentence, join paragraphs, modify user text, change
English spacing, choose fonts, compress punctuation or alter missing-answer rules.
Mixed/unknown text fails back to the previous separator. This heuristic is scoped
to the current fixed-choice list, not a general language detector.

`probe.py` independently enumerates the allowed fixed Chinese paragraphs and
compares the complete rendered HTML tree without collapsing text whitespace.
Tests cover active/missing/unknown/stale choices, both output profiles, default
fallback, autoescape, original answers and the public full-document fixtures.

`font_lab.py` is a synthetic, offline WeasyPrint comparison of normal/chws/halt/palt
using the actual bundled font. FontTools is available in the pinned native worker;
no new host or production dependency is required. No font feature is adopted.
The W3C [Chinese Layout Requirements draft](https://www.w3.org/TR/2026/DNOTE-clreq-20260901/)
describes fullwidth and adjusted punctuation as different layout conventions,
including unadjusted Taiwanese publications, not a universal defect.
Microsoft distinguishes contextual [chws](https://learn.microsoft.com/en-us/typography/opentype/spec/features_ae#tag-chws)
from noncontextual [halt](https://learn.microsoft.com/en-us/typography/opentype/spec/features_fj#tag-halt).
Actual support and output must be measured; enabling an absent feature is not a fix.

`boundary_lab.py` separately tests a naive extension of the existing Q13 CSS/Lua
exception to Q3, using actual prepared 0.3.50 assets in the pinned worker. It is
also **not an accepted fix**: the CSS selector drops the space before an English
opening such as `W3C PROV`, while Word's CJK boundary guard retains it. Six synthetic
cases characterize the real inserted spaces and this discrepancy. AST and styled
Word character comparisons protect all other text/properties; controls cover
English, other policy blocks and authored paragraphs. This is not a project replay.

The next implementation needs one shared, explicitly owned boundary decision for
both renderers, with fallbacks around English openings, authored blocks and gaps.
Do not simply widen the CSS selector or rename the sentence list to bypass the
existing translator's polish rule. Fullwidth glyph design is a separate decision.

Keep new builds under local ignored outputs with separate prototype package IDs.
Do not publish, upgrade production, rebase archived evidence or rewrite translations
as part of this experiment. If accepted later, integrate a small commit and lock
its full EN hash in the Chinese pipeline; retain tests to detect upstream drift.
