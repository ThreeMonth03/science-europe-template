# Maintaining the current bilingual repairs

The working `fix/answer-mapping` changes are not a new release. The last committed
package identity is still 0.3.51. English Jinja remains the shared source; Chinese
is produced by the existing translation pipeline, not a second Jinja fork.

## One current-behaviour entry point

Install `requirements-dev.txt`, then run from this repository:

```sh
# Fast feedback on one affected area.
python scripts/check_current.py --suite repository_profiles
# All eight current suites on English source.
make check-current
# The same suites against both prepared package trees.
python scripts/check_current.py --build /path/to/bilingual-build --output outputs/current-behavior.json
# Full unit tests and template validation; still required before integration.
make check
```

`make check` and `make test` first fetch the two public 2.7.0 Knowledge Model
bundles from a fixed tooling commit and verify their SHA-256 digests. Downloads
remain ignored; no credentials or project answers are involved. A verified
cache works offline, while a corrupt cache fails without being overwritten.
Before running unittest directly in a fresh checkout, run `make knowledge-models`.

`--build` expects `en/` and `translated/`. Use the English checkout corresponding
to that build; do not mix its UUID bindings or tests with another release.
For one prepared tree, use `--root PATH --language en|zh-Hant`.
`--suite` can be repeated. The runner continues after a suite fails, reports its
traceback, and exits nonzero if any suite fails. It never silently skips a suite.

`tests/test_current_behavior.py` runs the same registry through normal unittest
discovery and therefore through the existing English CI `make check` step.
`scripts/current_support.py` holds shared synthetic fixtures and the reply
adapter. Current checkers do not import test modules or historical projections.
Keep topic-specific assertions in the existing `check_*.py` modules; their old
standalone command-line entry points have been replaced by `check_current.py`.

| Suite | Repair covered | Cases per language |
| --- | --- | ---: |
| `answer_mapping` | Q1 rights holders; Q4 verification choices and active ancestors | 1,086 |
| `sentence_layout` | Non-reuse sentences, authored blocks and inline emphasis | 476 |
| `responsibility_reading` | Responsibilities grouped by contributor without merging identities | 560 |
| `access_reading` | Specific-software decisions; identifier assignment and resolution | 1,368 |
| `project_acronym` | Acronym-only, partial and inactive projects; scoped table rules | 156 |
| `ethics_reading` | Independent ethical flags and partial approval records | 1,288 |
| `publication_reading` | Publication summary, independent timing, stale No-branch children and partial identifier records | 2,136 |
| `repository_profiles` | Review-only repository notices; retained facts, links and numbering | 2,256 |

Counts describe deterministic combinations, not distinct real projects or proof
of every possible input. The suites cover review/submission, missing/unknown/No
states, escaping, record identity and focused/full-body controls as appropriate.
The project-table CSS assertions previously in a separate test are retained in
the project suite. Extend an existing suite for a repair; do not add a wrapper,
runner and chronological report for each iteration.

## Efficient verification, with clear limits

During editing, run the affected suite. Before a paired integration, run all
current bilingual suites, then full CI, including the existing PDF/Word engine
checks. Changes to shared CSS, Word filters or styles need broader rendering
checks than a wording-only change. Inspect the affected output pages in both
languages/profiles, with empty, partial and long-answer controls where relevant.

These quick checks use a lightweight reply/Markdown adapter and render question
bodies; they do **not** replay the complete worker or certify PDF pagination,
Markdown conversion, natural language, or Microsoft Word appearance. Generated
reports explicitly set `release_acceptance` to false. Existing native engine
checks and visual review remain necessary; LibreOffice is not Microsoft Word.

Private replay scripts from earlier experiments depend on local snapshots and a
locally built worker. They are not fresh-checkout CI tests and are not published
as such. Private replies, credentials and rendered documents stay outside Git.
A portable, synthetic-only full-worker smoke test remains separate follow-up
work; this cleanup deliberately does not create another per-topic native runner.

## Paired CI and release boundary

The Chinese workflow calls the shared bilingual runner after building. Its
paired `pipeline.yml` must pin the exact English commit containing this runner.
Push English first, then the Chinese workflow and source-lock update together;
do not substitute a floating branch or skip a missing runner.

Historical frozen-source/reference gates remain enabled. The development-only
`current-repairs-delta.json` verifies the complete candidate tree, changed/added
path scope, support files and unchanged 0.3.51 identity before projecting the
committed parent to those gates. It is explicitly not release approval. In the prior batch,
all 297 English and 482 Chinese unit tests, TDK validation, and the commands from
both workflows pass. The current bilingual runner passes 17,980 combinations;
historical projections remain separate evidence, not tests of current prose.
A private, network-free full-worker replay covers bilingual review/submission
examples with missing, repository-heavy and long answers: 28 renders produced
154 native PDF pages and 140 LibreOffice Word-preview pages. The mechanical
audit found no blank pages, out-of-page text, missing fonts or empty headings;
affected pages were also inspected visually. All 96 active nonempty free-text
answers in these cases were retained. This is representative evidence, not
exhaustive input coverage or Microsoft Word acceptance. Local command results
do not establish GitHub Actions success; check the exact pushed commits there.
Review the release candidate in
the target Word environment before creating a new package identity and Chinese
lock. Do not publish changed assets under the old 0.3.51 identity.

Triage shared causes first: multiple historical failures can come from one
unregistered source layer rather than independent output defects. Old prose or
count expectations must still be reconciled with the approved repair; never
replace an exact assertion with a blanket pass.

CI retains the existing workflow and required-check identities and all checks.
English unit tests and native probes run in two parallel groups. The Chinese
workflow uses five fixed groups: locked-English units, Chinese units, package
integration/current answers, translated reading, and native PDF/Word probes.
Each starts from the same exact locks and prepares its own public KM fixtures;
the three package-consuming groups independently build identical packages.
This avoids transferring prepared trees or depending on another group's outputs.
The existing `contract-and-template` / `build` checks now aggregate the groups:
failure, cancellation or skipping is not success. Matrix fail-fast is disabled
so one failed group does not discard the other groups' evidence.

New commits cancel superseded runs for that branch/PR; manually dispatched runs
remain independent. Reports are uploaded even after a failed check and retained
for 14 days. Only the Chinese integration group uploads the candidate ZIPs;
reading and native reports have separate artifact names. The native group still
runs all 31 probes in two language lanes; either lane failing fails the group.
The slow repeated-font probes reuse compiled CSS/font configurations per exact
CSS/media pair, not rendered documents or answers; before/after geometry and
text must remain identical. Measure improvement on the exact GitHub runs, not
by comparing local and hosted runtimes. Historical native checks are not yet
optional: a portable current
full-package smoke test must cover their role before changing their frequency.

Use short-lived repair branches in both repositories. Pin their paired release
by exact English commit/tool commit/translation version, not by assuming matching
branch names imply matching builds. Continue using the existing upstream audit
and versioning policy; this test cleanup does not change the branching model.

The eight superseded per-round development notes in each repository were
consolidated here and in the Chinese testing guide. Their detailed local evidence
was archived outside Git before removal; existing committed historical evidence
and contracts are preserved. Keep future output reports under ignored `outputs/`
and document lasting decisions here, not another chronological test diary.
