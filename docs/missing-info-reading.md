# 0.3.20 missing-information regression

Branch: `fix/missing-info-reading`, based on 0.3.19 `62338c5`.
The official upstream base remains 1.30.1 / `22d60aae4b63ee677477ac0c73097807284aaf9f`.

This bounded change addresses three native bilingual counterexamples:

- Q7: when personal data / Explore is selected, answering the legal basis must
  not hide an unanswered safeguards question. The new SE-4a fact prompt is
  branch-local; an inactive parent does not produce it. This does **not** yet
  cover every nested safeguards or legal-basis follow-up.
- Q15 PDF: accept an exact whitelist of template-owned missing metadata tags in
  the repeated resource header. Keep available amounts, zero, currency and gap
  text; move original fragments without rewriting them. Height estimates ignore
  source indentation, not authored text; unknown markup and large headers still
  fall back. Missing headers get wider budget/funding columns.
- Q15 PDF: keep the question and exactly four fixed, wholly unanswered facts
  together. No authored prose, resource table or long answer gets this rule.

Native revalidation also exposed a malformed translated Q7 paragraph: the legal
basis closed inside separate answer branches, and translation dropped those
closures. Its closing tag now sits after the conditional. The six existing
legal-basis translations are rebound exactly, not retranslated. The initial
failure and the separate final native rerun are retained in the Chinese repo.

Non-PDF Q15 output is still compared to frozen 0.3.18. Word Lua and reference
styles are unchanged. Q7's new content deliberately applies to every format.
The PDF fragment oracle now contains 32 cases; 8 run against the pinned worker's
WeasyPrint engine. Native export evidence belongs in the Chinese pipeline repo;
unit/fragment passes are not a full DMP or Microsoft Word acceptance claim.

`scripts/generate_missing_info_fixtures.py` reproduces 9 missing/negative cases
and 2 complete controls. Existing synthetic fixtures are verified, never
overwritten; validate all replies against the server-compiled KM before export.

Maintain fixes in this English source, lock its exact commit in the Chinese
repository, and review translation-tree migration before building a candidate.
Do not merge official upstream blindly into translated Jinja or edit generated
Chinese templates by hand. Preserve the 0.3.19 failing audit as historical evidence.
