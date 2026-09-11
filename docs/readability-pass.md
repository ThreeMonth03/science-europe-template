# Readability iteration (experimental 0.2.0)

This iteration follows the review of the five-page Chinese sample. Successful
rendering and selected fact checks are necessary but do not establish readability,
substantive completeness or Science Europe compliance.

## Owned changes

- PDF and Word now include the same `frontmatter.html.j2`, research overview,
  contributor list, questions and final document-provenance note. Contact/creator
  information is represented once by the contributor roles. A sole research
  project supplies the main title; the DSW document name remains visible.
- The original `header.html.j2` and `word/frontpage.html.j2` remain in the source
  for provenance but are no longer the active entry points. Upstream changes to
  their *meaningful metadata* must be ported to the owned frontmatter explicitly.
- All fifteen original question texts remain. Repeated question IDs are fixed.
  Empty rendered answers in selected questions receive a visible `missing-output`
  note, which does not imply that the questionnaire was left blank. Q5's known
  mapping gaps are now `unmapped`, not reported as the user's missing answers.
- Q1 only shares copy/access/format rules when all selected reference datasets
  have identical recognised values. Unknown/custom restrictions, differing rules
  and non-reference datasets stay separate. Purpose, source, version and version
  policy remain per dataset. No free answer is summarised or rewritten.
- Q15 uses a native editable resource/budget/funding table, preserves zero and
  distinguishes missing currency from missing amount. It no longer refers to
  an empty Q11 for repository charges.
- PDF typography and Word styles remain separate implementations. Word has
  explicit column widths, no duplicate Pandoc title, and no inherited header logo
  or title field. The Lua policy-paragraph join operates only on owned blocks;
  nested free-answer blocks are preserved.

## Upgrade and version boundaries

Work is on short-lived `feat/readability-pass`, based on the previous experiment.
The official baseline stays at **1.30.1 / 22d60aae4b63ee677477ac0c73097807284aaf9f**.
Our experimental package version is 0.2.0, not an upstream release number. There
is no formal release/tag, mainline merge or deployment associated with this edit.

Future upstream updates require a reviewed port of field mappings, conditions and
schema changes; they must not overwrite owned presentation or reinstate duplicate
frontpages. Re-run empty/negative/partial/populated/stress fixtures in both
languages and PDF/DOCX after translation migration. Compare whole pages as well
as field/condition alignment. A successful merge is not acceptance.

The Chinese repo pins an exact English commit and translates complete units using
the existing tool. Its version is independent. This does not create a second
Chinese business-logic implementation or require a runtime LLM.

## Limits

This is not a full audit of every questionnaire branch. In particular, visible
missing-output notes establish absence from the *rendered document*, not why the
answer is unavailable. Native template tables do not fix unsupported Markdown
pipe tables in free answers. DSW worker changes, live projects, knowledge-model
extensions and automatic translation of user answers are outside this iteration.
