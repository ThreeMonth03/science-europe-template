# 0.3.47 — reuse summaries and compact empty questions

The accepted Q1 and empty-question prototypes are consolidated into shared English
source. There is no runtime overlay or independent Chinese Jinja fork. The four
new helpers, three modified source files and submission-only Word suffix exactly
match prototype `9847397dd1e2a7e29385c0d1f67eb4bfc0f93b4f`.

All 15 original questions and six Science Europe sections remain. Empty submission
questions stay in place with tighter spacing, without invented answers or new
missing-answer notices. Review remains the default; zero, unknown choices, authored
blocks and unnamed datasets retain their existing semantics and neutral labels.

Q1 groups known reuse scope, format, stability and conditions into a paragraph.
Authored conditions remain separate editable blocks. Word keeps real Heading3
properties under autoescaping. PDF retains empty answer containers: hiding them
caused a native pagination regression after authored tables and was rejected.

## Maintenance contract

`requirements/submission-flow-delta.json` pins every source/asset byte and the full
metadata, including format UUIDs and steps. The current branch is tested against
the accepted prototype before any test-only projection to 0.3.46. Older byte-level
oracles keep their historical scope; new branches have independent tests. The full
historical Jinja view is overridden so changed Q1/content includes cannot leak in
through filesystem fallback. Unknown changes fail instead of widening goldens.

CI uses the existing pullable public worker digest for the 25 Word engine cases,
not a private locally built image ID. The frozen experiment runner remains intact.
Private native output comparisons use the markdown-table worker separately.

Work branch: `fix/submission-flow-integration`. The prototype branch stays intact.
The Chinese repository pins the full English integration commit and pairs version
0.3.47. Review/submission stay formats of one source, not permanent branches.
Future upstream upgrades belong on an `upgrade/*` branch with a reviewed new delta;
merging upstream or changing a golden hash is not automatic acceptance.

This is source integration, not deployment or full DMP/Microsoft Word acceptance.
The companion repository records paired builds and native comparison separately.
