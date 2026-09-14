# Sharing and preservation (0.3.6)

Short branch `feat/sharing-preservation` follows 0.3.5. The official 1.30.1
baseline, KM and UUID definitions are unchanged.

- Q10 joins licence dates and fixed restriction introductions in an owned
  summary. Authored conditions and custom access processes remain separate
  blocks; a selected process with missing details is not silently omitted.
- Missing access-process and metadata-publication choices are distinct from
  explicit negative answers. Link punctuation is a full translatable sentence.
- ISO-shaped licence dates have scoped PDF no-wrap and Word non-breaking
  hyphens. This is typography, not date validation; filenames/URLs are untouched.
- Q11 joins fixed publication/retention/metadata prose and fixed funding prose.
  Gap/review notices and free payment arrangements remain block boundaries.
  Repository lists and complex repository prose are not rewritten in this pass.

Q10/Q11, shared macros, PDF CSS and Word Lua remain owned upgrade-review
surfaces. Re-run partial-answer, long-authored-answer and bilingual rendering
checks on upgrades, even if Git reports no conflict. No production changes.
