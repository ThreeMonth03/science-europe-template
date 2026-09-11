# Answer-retention experiment (0.2.1, not a release)

The previous `populated` fixture covered selected Q1/Q5/Q15 branches, not a
completed questionnaire. It must not be used to estimate how much of a fully
answered project is retained. `representative` now adds instrument measurements,
quality checks, format/volume, metadata, storage capacity, security, personal-data
decisions, publication, preservation, identifiers and software. It exercises all
15 output questions but still does **not** answer every Science Europe topic.
Q5 storage/backup locations and frequency remain explicitly unmapped.

## Reproduced defects and bounded fixes

1. Q3 suppressed a supplied capacity (including `2048` or `0`) unless a storage
   technology question was also answered. Capacity now independently enables its
   output. We do not render inactive child answers as current decisions.
2. Q3 tested `metadataOpenInstrNoAUuid` for both Yes and No. A No therefore
   incorrectly promised access instructions; a Yes lost that detail. Compare
   Yes, No and unanswered separately. Labels were checked against compiled KM 2.7.0.
3. Q12 treated unknown publication as no publication, and unknown software or
   required-but-unlisted software as no tools needed. Each now has a distinct
   output. Dataset identity survives, and native list markup is properly closed.
4. Q3 applied `capitalize` to a free answer, corrupting case-sensitive names such
   as `CHANGELOG.md`. The original case is now retained. This is not a general
   audit of every text-transform filter elsewhere in the template.

The new unit regressions failed before the changes (seven subcase failures for
the first three defects, then a separate file-case failure). Existing tests remain
in place. Q1/Q4 multi-method quality lists and Q3 file-convention blocks also get
valid block boundaries; no new visual theme is introduced.

## Reproduction

Use the existing tooling checkout's virtual environment. The two scripts using
DSW below are hard-coded to the **isolated localhost runtime** and create/delete
only their own synthetic inspection project. They never use desktop credentials.

```sh
../dsw-document-template-tool/.venv/bin/python scripts/generate_retention_fixtures.py
../dsw-document-template-tool/.venv/bin/python scripts/validate_pilot_fixtures.py
../dsw-document-template-tool/.venv/bin/python scripts/audit_km_bindings.py --output /tmp/science-europe-km-binding-audit.json
../dsw-document-template-tool/.venv/bin/python -m unittest discover -s tests
```

`retention-partial` removes the filesystem-answer subtree and the software list
from the representative scenario, while retaining the storage amount and the
decision that specific software is required. Both inputs must be valid against
the server-compiled English and Chinese KM, independently of our template paths.

## Binding audit is not answer coverage

The static audit finds 8 unbound variable references across 5 question templates
and one referenced entity absent from Common KM 2.7.0. Some are unused variable
assignments, some appear to be typos, and some need a historical mapping review.
Do not equate those counts with nine lost user answers. In particular, the old
`publishedDataIdentifierSpecifyQUuid` does not exist in the compiled KM; no fake
answer is inserted to make that branch appear tested. These findings remain open.

## Versions and acceptance

Work uses short-lived `feat/answer-retention`, based on `feat/readability-pass`.
The official baseline remains 1.30.1 / `22d60aae4b63ee677477ac0c73097807284aaf9f`.
Experimental EN and ZH versions are 0.2.1; Chinese locks the exact English commit.
No mainline merge, release/tag, runtime upgrade or live DSW deployment is implied.

The Chinese review records real HTML/PDF/DOCX, exact versions and checksums,
selected fact checks, the static binding audit and a parser-only Markdown probe.
Outstanding malformed markup, unsupported Markdown tables, substantive gaps and
actual Microsoft Word verification must remain visible. A fuller-looking sample
is not a completed or compliant DMP.
