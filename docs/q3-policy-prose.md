# Shared Q3 policy prose (0.3.51)

Integrate the exact accepted `a0ed46715842a01c154beb430f97ac58a0549347` prototype:
one Q3 capture/call plus `src/metadata-prose.html.j2`. Only 2–3 plain fixed policy
paragraphs whose every boundary is a Chinese full stop followed by BMP Han are
joined. English, mixed boundaries, authored HTML and missing-information panels
keep the entire original block unchanged. Fact attributes, text and internal
whitespace are preserved. CSS, fonts, Word styles and all format steps stay fixed.

The earlier broader English merge failed native PDF geometry/pixel checks. It is
not integrated. The current rule uses no coordinate tolerance for unchanged cases.
The Chinese derivative continues through the existing locked translation tool;
775 translation files remain byte-identical. Both language versions move together
to 0.3.51, with the Chinese pipeline locking the complete English commit.

`q3_policy_prose_contract.py` first verifies every actual source/asset and metadata
byte against the frozen recipe. Only then may older tests see the exact 0.3.50
view. Historical recipes/fixtures/seals are not rewritten. New tests reject added,
missing or changed helpers, source, assets, format steps and identities.
`probe_q3_policy_prose.py` checks 7,932 combinations against actual English sources;
the paired integration gate also checks actual Chinese prepared/package content.

This is a bounded integration, not Microsoft Word or full DMP acceptance. Word
line spacing, Chinese wording and fullwidth punctuation glyph widths are separate
tasks. Local validation does not claim a GitHub Actions run or deployment.
