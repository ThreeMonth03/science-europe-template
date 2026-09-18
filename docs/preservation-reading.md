# 0.3.39 bounded Q11 Word reading unit

This experimental revision changes Word presentation only. All existing Jinja,
PDF CSS, `pilot.lua`, questionnaire facts and translations are unchanged.
Both Word output profiles run the same new `preservation-reading.lua` **after**
the existing filter; there is no Chinese-only logic or profile-specific branch.

A direct Q11 dataset label and its entire, already-joined fixed summary can
become one paragraph, separated by a line break. The dataset label becomes
bold paragraph text rather than Heading5; its link anchor is retained. The
question itself remains Heading3. A new paragraph style inherits Body Text,
keeps its own lines together and does not keep the following repository list.
No font size, line spacing, forced page break or pre-existing style is changed.

Selection requires a known answer/dataset/policy structure, a nonempty dataset
identity, an unformatted name of at most 80 width units and exactly one plain
summary paragraph of at most 360 units (characters at or above U+2E80 count as
two). Each direct dataset is checked independently, including duplicate names.
Missing-information blocks, authored descriptions/reasons, lists, tables,
links, hard breaks, rich inline formatting and unknown attributes/classes
reject the join. Long or unrecognized content remains unchanged and breakable.
Top-down traversal stops at authored/answer boundaries, so nested lookalike
questions inside user content cannot trigger this rule.

`probe_preservation_reading.py` compares the old filter chain with the new
chain using pinned worker Pandoc, checking exact AST changes, DOCX text/runs,
bookmarks, links and all other package parts. The reference-document oracle
admits exactly one new style and rejects any existing-style change. The source
oracle compares against the frozen 0.3.38 commit and permits only the new filter,
its Word-chain registration, the style-preparation block and the version bump.
Native bilingual exports and LibreOffice/Microsoft Word are separate gates.

The Q15 PDF pagination experiment is deliberately not included. Submission
preview remains partial: this does not hide additional notices, complete
answers, certify Science Europe compliance or approve a DMP for submission.

This change lives on short-lived `fix/profile-pagination`. Upstream upgrades
must inspect the incoming Q11 AST shape and re-run the fallback matrix; the
post-filter is a small owned layer, not a reason to merge changed upstream
questionnaire semantics automatically. Chinese builds continue to pin an exact
English commit and preserve their translation tree.
