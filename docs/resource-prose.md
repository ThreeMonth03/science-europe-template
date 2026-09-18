# 0.3.41: two owned Q15 facts, one paragraph

The shared English question captures its unchanged hardware/software and
repository-charge branches. A small presentation helper joins their two fixed
sentences only when hardware is explicitly **No** and charges are explicitly
**Yes** or **No**. Both facts remain identifiable; `complete` on the charge span
means answered, not free of charge. Missing/unknown choices, authored hardware
details, unsupported markup and longer translations retain their exact bytes.

The original English sentences and all existing translation units are retained.
English full-stop boundaries use one space; two Chinese full-stop boundaries use
none. Punctuation itself is never rewritten. This is not automatic translation,
an arbitrary paragraph compactor, or an LLM-generated completion of missing facts.
The owned combined paragraph is capped at 160 weighted units (CJK counts twice).

HTML, PDF and Word use the same shared result, including both review and
submission-preview profiles. The PDF-only short-resource grammar admits exactly
one plain charge span inside the explicit-no hardware paragraph. Its existing
whole-question, paragraph, table and row limits remain unchanged. CSS, fonts,
Word Lua filters and reference styles are untouched.

`resource_prose_contract.py` removes only the exact wrapper, new helper and span
grammar additions, restoring 0.3.40 source bytes. The Chinese build additionally
compares the entire projected prepared-source dictionary with the frozen 0.3.40
hashes before running all older gates. Never replace those baselines with new
hashes merely to pass CI. A future upstream change touching these boundaries
requires a reviewed migration and new before/after evidence.

Versioning remains one English source commit plus its exact Chinese pipeline
lock on the existing work branch, not separate review/submission code branches.
Native DSW PDF and Word/LibreOffice comparisons are required in the companion
Chinese repository. Unit success alone is not release or Microsoft Word approval.
