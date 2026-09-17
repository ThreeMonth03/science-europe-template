# Joined Q5 Word lead — 0.3.35 experiment

The 0.3.34 Chinese `metadata-partial` Word preview separates the storage policy
from its operational limitations despite effective keep-with-next settings.
Reapplying a setting after import works only in memory; saving/reopening does
not. Neither that workaround nor an engine/font upgrade is adopted here.

This incremental experiment joins only the two already-qualified fixed lead
paragraphs in `keep_q5_context`, inserting a visible `LineBreak` before the
limitations introduction. Both original inline lists are retained. The first
limitation bullet keeps its existing style; the final bullet does not keep Q6.
Existing Jinja semantic eligibility, plain AST checks and the 900 weighted-unit
bound are unchanged. Long, rich, authored and cold-archive fallbacks are not
made unbreakable. Earlier merging of adjacent owned workspace facts remains
unchanged and is included in the regression matrix.

No HTML, PDF CSS, questionnaire mapping, translation, font, paragraph-style
definition or reference DOCX changes. Chinese still comes from the shared
English source through the existing pipeline; there is no Chinese-only Lua fork.

`q5_word_join_contract.py` reverses only the exact reviewed source delta before
the historic 0.3.34 hash/style gates. The new independent probe compares real
Pandoc AST and DOCX against that preserved behavior: precisely two adjacent
owned leads become one, with all original runs and one plain line break. Every
other XML block must remain identical. Missing/extra/page breaks, restyling,
changed punctuation/values and unintended fallback joins are rejected.

The pinned probe covers 31 cases, including both languages, the width boundary,
multiple fixed policy facts, and forged hints on long/complex input. A hint is
not an authorization to join arbitrary authored text: Jinja checks semantic
ownership before Pandoc drops its paragraph data attributes.

Native same-fixture bilingual PDF/DOCX and fresh LibreOffice previews must be
compared separately, including missing, negative, complete and long answers.
The earlier four-page reduced counterexample remains immutable evidence of
0.3.34, not an acceptance fixture to overwrite. Passing build/probe checks is
not full-DMP or Microsoft Word acceptance. No production upload, upstream merge,
release tag or permanent product branch is implied by this experiment.
