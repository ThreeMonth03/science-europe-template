# Synthetic pilot inputs

`populated` means the original **partially populated three-question test**, not a
completed DMP. See `scripts/generate_retention_fixtures.py` for the broader
`representative` and `retention-partial` cases; those exercise all 15 output
questions but still do not prove complete Science Europe topic coverage.

No real project answers or credentials are included. `pilot/en` and
`pilot/zh-Hant` contain reviewed bilingual synthetic answers with identical item
IDs. Runtime event UUIDs are regenerated per test because DSW requires them to
be globally unique. The user-answer text is not translated by the template.

Generate the inputs and copy the pinned tool fixture KM locally:

```sh
../dsw-document-template-tool/.venv/bin/python scripts/generate_pilot_fixtures.py --tooling ../dsw-document-template-tool
../dsw-document-template-tool/.venv/bin/python scripts/validate_pilot_fixtures.py
```

The `.km` copy is ignored by Git and its SHA-256 is recorded for every render.
Validation uses the isolated local DSW's compiled KM graph; it does not trust
the template's guessed reply paths. It creates and deletes only its own test
project. Current cases cover empty, explicit No, partial, populated and long
text, with two reused datasets and budgets of 5000 / 0 TWD. They do not cover
every reachable Q1/Q5/Q15 branch or prove substantive DMP completeness.

The Markdown pipe-table case intentionally remains in the corpus. DSW 4.30
does not render it as a table; the end-to-end acceptance report must stay blocked
until that capability is addressed or the supported input contract is explicitly
revised. Do not silently replace this input merely to turn the tests green.
