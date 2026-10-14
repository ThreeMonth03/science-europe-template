# Maintaining the current bilingual repairs

## Current CI versus immutable historical replay

The existing `Template quality` workflow now defaults to `profile=current` on
push, pull request and manual runs; its required `contract-and-template` identity
is unchanged. Both current lanes must succeed. The unit lane verifies the actual
TDK source, runs all eight `check_current.py` English suites, and explicitly runs
`CurrentI18nTests`, `CurrentBudgetLayoutTests`, `DerivedSubmissionHeadingsTests`,
`DocumentMetadataTests` and all `experiments/legacy434` exporter tests. The native
lane runs five existing tests: the stock 4.35 Markdown parser, owned Word
provenance guard, PDF provenance boundary/long-content flow, deterministic Word
reference styles and English spacing. PDF flow covers both pinned stock 4.34 and
4.35 workers; the parser and Word guard use stock 4.35, not a Worker fork. JSON
suite counts and verbose unittest logs (including `Ran N tests`)
are uploaded even on failure. This is an explicit current test scope, not a claim
that every historical test module ran on PO Jinja or that 27,044 cases equal the
entire repository suite. The companion Chinese workflow additionally builds the
exact pair, checks the authoritative PO with official 4.35 extraction, and runs
all sixteen prepared bilingual suites.

Manual `profile=historical` retains the complete previous unit/native commands
but checks out `0b06afd1b2983ae53d21232926a3e3b933c468bf` (0.3.67) and its
declared dependencies. The matching Chinese replay uses
`4a1e1086d878c76e99bab794fffa4f806100baed` and Tool
`25e339fbdfb1d20796471055790aad6a4226b6ed`. Their original English source seal
and Chinese Word preflight were rechecked without changing a seal; this does
not establish that the full hosted replay passed. The saved invalid 0.3.78
snapshot remains documented separately. Historical replay is not current PO
acceptance, and its seals are never recalculated from current source.

The default checks do not replace complete same-answer PDF/DOCX visual review,
stock 4.34 runtime acceptance or Microsoft Word testing. No workflow deploys to
DSW, publishes a release, or promotes a candidate merely because CI passes.
The older CI descriptions below record the pre-PO workflow and its evidence.

## PO translation and DSW 4.34 compatibility

Server 4.35 is not required for ongoing translation work. The companion Chinese
repository owns the only editable `locales/zh-Hant.po`. English owns shared Jinja,
locale-aware layout and the exporter; pass the Chinese catalog explicitly.
Keep context keys and named parameters intact, translate whole clauses and review
the resulting prose. The old translation tree and meeting packages remain history.
`experiments/official-po/fixtures/zh-Hant-0.3.80.po` is an exact read-only receipt
fixture, not a second translation source.

Install the optional build dependencies in an isolated environment:

```sh
python3 -m venv .venv-po
.venv-po/bin/python -m pip install -r requirements-po.txt
make test-compat434 PYTHON=.venv-po/bin/python
make export-compat434 PYTHON=.venv-po/bin/python \
  ENGLISH_ZIP=/path/to/prepared-english-template.zip \
  PO=/path/to/science-europe-template-zhtw/locales/zh-Hant.po COMPAT_VERSION=0.3.81 \
  COMPAT_OUTPUT=outputs/compat434/template.zip
```

The input is an official TDK English package with its fonts/reference already
prepared, not a raw source directory. Never prepare that reference a second
time. Optional `SOURCE_COMMIT=<full-hash>` records caller-supplied provenance;
the exporter checks its format, not its correspondence to the ZIP. The ZIP and
PO hashes are always recorded in `template.zip.json`.

The generated 4.34 profile embeds the approved PO as a compiled MO asset, enables
legacy i18n on every Jinja/enrich-docx step and fixes its generated language
helper to `zh-Hant`. All other Jinja and existing binary assets retain their
bytes. The package exposes the six supported review/submission HTML, PDF and
Word formats with Chinese labels. LaTeX and ODT are not included in this profile.
Missing, extra, fuzzy, untranslated or placeholder-mismatched catalog entries
fail the build instead of silently falling back to English. Plural messages need
a separately reviewed export rule and are currently rejected.

Translation revisions can be released even when the English source is unchanged.
Use a new `COMPAT_VERSION` for each published source/PO pair and tag it; use
short-lived development branches, not one permanent branch per language or
runtime. The `-zhtw-compat434` template ID is distinct from the meeting and official
templates. The exporter refuses existing local ZIP/sidecar paths, but does not
query the server: an operator must also reject an already-installed coordinate.
Do not overwrite an existing DT/UUID or its installed absolute MO path because
both Worker asset caching and Python gettext caching can retain the old catalog.
The package-relative MO path stays fixed. Generated ZIPs are build
outputs, never a second translation source. No additional CI workflow is added.

Validate with stock Worker 4.34 before uploading: complete, partial and empty
questionnaires; all 15 questions; no submission hints; untouched authored answers;
HTML escaping/parameters; native PDF/Word plus individual page reading. 4.35
acceptance is not a substitute for this check. A local adapted-context Worker test
is also not evidence of a real 4.34 Server/browser installation.

The bounded [local compatibility acceptance](../experiments/legacy434/acceptance.json)
records the tested ZIP/PO/Worker hashes. Its three synthetic cases produced nine
documents; all 27 PDF/Word-preview pages match the accepted 4.35 output in text
and pixels and were individually read. This is a local candidate, not a production
installation or arbitrary-input bug-free guarantee.

The subsequent [stock 4.34 Server acceptance](../experiments/legacy434/server-e2e.json)
also passed on 2026-10-14 with the same ZIP. Real import, DB/S3 asset fetching,
nine fresh documents and three old-version preview API requests succeeded;
all 78 cached files match the package, and preview HTML matches fresh HTML.
Six unchanged true-context offline controls match all 27 actual PDF/Word-preview
pages. The actual pages were individually read. This does not certify browser
interaction, new-PO preview invalidation, production installation or native Word.

The [subsequent translation batch](../experiments/legacy434/editorial.json) changes
23 Chinese messages and generates a separate immutable `0.3.80` candidate.
Publication/open-access distinctions, calibration, harmonization, consent,
resource necessity, low-risk wording and six colons were corrected together.
All 23 changed keys are called and visible across 17 stock-4.34 HTML outputs;
four PDF and four Word documents (42 pages) were individually read. English
Jinja, format chains and the other 77 render assets are unchanged. A review-only
budget hint has a two-character final line in the stress case, without clipping
or loss; submission is unaffected. This is offline Worker acceptance, not a new
Server/preview, native Microsoft Word or 4.35 acceptance. Previous evidence and
the `0.3.79` ZIP remain preserved rather than relabelled.

The same latest PO also passed a bounded stock-4.35 follow-up; see `latest_po_smoke`
in the [PO status](../experiments/official-po/status.json). Official extraction checks
all 859 keys. Eight format-entry controls verify ten reached edits, unchanged
English under old/new PO and Chinese submission hint suppression. One review
PDF/Word pair has 15 individually inspected pages, with no new confirmed defects.
This uses declared synthetic replies in true 4.35 base contexts, not a new Server
import. The previous Server receipts retain their original PO hashes.

When the server eventually upgrades, use the shared English DT plus attached PO
and explicit document language. The 4.34 package is not a 4.35 fallback: 4.35
ignores its removed legacy i18n options. The maintained PO and English source
remain usable; only the deployment profile changes.

The local cutover gives the Chinese repo PO authority and replaces its build's
translation-tree segment with one English preparation and generated runtime
profiles. Candidate staging binds the English ZIP, Chinese compatibility ZIP,
PO, MO and exporter sidecar plus the complete manifest. English current checks
now select explicit gettext languages. Three template-owned prose joins remove
English separator spaces only in Chinese; tested English output remains exact.
English 0.3.79 and compatibility 0.3.81 are new identities, not meeting overwrites.
Current-package native acceptance and the scoped CI checks remain separate gates. Preserved
historical-tree/source seals do not describe marked PO Jinja and are not reset.

## Historical translation-tree repair baseline

The `fix/answer-mapping` repairs currently include local preview 0.3.78,
not a deployed release. English Jinja remains the shared source; Chinese
is produced by the existing translation pipeline, not a second Jinja fork.

0.3.75 preserves explicit negative answers for Q1 harmonization and
machine-readable preparation, and Q10's choice not to assign persistent
identifiers even when the identifier value is blank. Missing or inactive
choices are not treated as negative; supplied identifier values are retained.

0.3.76 retains the special repository's server-administration and hardware
maintenance arrangement (Yes or Not yet), and other recurring availability
fees (Yes or No) once in Q15. These are distinct from long-term support and
repository service charges; missing or inactive replies imply neither state.

## Template-owned Markdown boundary

The current local repairs route Q2's non-standard-format reason and five Q3
folder/file/object naming details through the existing answer parser. Their
conditions and fixed prose are unchanged. Q3's three fixed folder statements
use paragraph-bearing lead wrappers only when their own details are nonblank;
the existing PDF/Word guards join each statement to its first answer block,
without keeping a whole answer or list. All 858 Chinese sentence/translation
pairs retain their bytes; Q3 metadata paths and source identities move with the
new wrappers. Three existing translations require explicit carry-forward.
The Q3 layout repair is replayed with the pinned stock 4.35 worker; native
Word XML and bundled LibreOffice previews are checked, not Microsoft Word.
The Chinese build selects PDF typography by the final WeasyPrint step, covering review and
submission while excluding HTML/Word. The stock worker is not modified and
there is no PO migration. Uncommitted packages remain previews.

0.3.68 adds a shared Jinja → stock Pandoc → original Jinja prefix to all eight
formats. 0.3.69 also routes the six confirmed free-text consumers through its
sanitized fragments: Q1 reuse purpose, Q2 non-equipment description, Q3 metadata
access explanation, shared Q1/Q4 quality details, and Q15 resource purpose and
funding details. Q1 provenance and Q2 other data-entry arrangements remain on
the same path. 0.3.70 adds the nine confirmed Q1 version/reuse-condition,
Q6 pseudonymization, Q8 custom-reason/reuse-condition and Q9 consent/purpose
fields, preserving repeated Q1/Q8 ownership and single/multiple-reason branches.
Fixed Q6/Q8 leads are separate from authored blocks; Q8 restriction leads use
the existing bounded PDF keep without binding the whole answer. Other Markdown
calls, including integration-identity fallbacks, remain unchanged. Original
entries, CSS, fonts, Word filters and conversion engines are preserved. The tested
runtime is the existing pinned official 4.30 worker (Pandoc 3.8.3), not a worker fork
or a replacement Pandoc binary. Other runtime versions require a compatibility check.

`tests/test_answer_markdown.py` tests exact string transport, rejection/fallbacks,
all format chains and a single batched stock-parser regression. Existing body tests
use an explicit test-only Markdown adapter; they cannot certify the new parser.
Raw HTML stays literal, unsafe links retain their labels/targets without active
links, and images retain labels/targets without fetching image data at these
entry points. No original reply or indentation is rewritten. The prefix processes
strings only, never the full document with embedded font CSS.

Uncommitted bilingual builds must remain `--preview`. Before promotion, commit
the reviewed English source and pin that exact commit in the Chinese pipeline;
do not use a floating branch or claim that the current preview is deployable.
This bounded integration is not whole-template or Microsoft Word acceptance.

0.3.71 lets Q8 custom-reason lists flow, including long plain answers; fixed
short reasons retain their original keep. Q1 version answers use a labelled
flow container rather than an outer information table. Recheck the observed
PDF whitespace and Word body-right overflow against the same native inputs.
The local paired replay resolves the English rich-reason whitespace and both
version-table overflows; Chinese Q8 is an unchanged pagination control. The
existing reason test also checks selector matching in the pinned worker, not
only the test HTML parser. These finite previews are not release acceptance.
Q8 permission paragraphs have no actual Word keepNext; the inspected previews
show no orphan, which is not an all-boundaries guarantee.

0.3.72 reuses the exact Q15 bounded two-cell row contract for Q8 reuse-condition
tables. Only direct authored tables in the owned dataset list qualify; short
simple body rows may not split, while long or complex cells, headers, other
questions and adjacent prose retain their original pagination. No whole-table
keep, worker change, or translation change is introduced.

0.3.73 overrides the inherited Word label `keepNext` only in already bounded
Q15 budget rows. Their `cantSplit` protection and repeated table headers remain;
history rows, unmarked or unbounded rows, and the shared label style are unchanged.
The local control isolated the label keep rather than the row-split rule as the
cause of the observed English review-budget whitespace in bundled LibreOffice.
This is not a Microsoft Word or arbitrary-input guarantee.

0.3.74 also maps Q9's explicit DPIA No answer. It reports the questionnaire
response, not an independent legal assessment; missing or unreachable replies
do not become negative claims. Both languages retain the original Yes sentence.

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
| `answer_mapping` | Q1 rights holders; Q4 verification choices and active ancestors | 1,266 |
| `sentence_layout` | Non-reuse sentences, authored blocks and inline emphasis | 1,884 |
| `responsibility_reading` | Responsibilities grouped by contributor without merging identities | 560 |
| `access_reading` | Specific-software decisions; identifier assignment and resolution | 1,924 |
| `project_acronym` | Acronym-only, partial and inactive projects; scoped table rules | 1,724 |
| `ethics_reading` | Independent ethical flags and partial approval records | 1,288 |
| `publication_reading` | Publication summary, independent timing, stale No-branch children and partial identifier records | 2,136 |
| `repository_profiles` | Review-only repository notices; retained facts, links and numbering | 2,688 |

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
path scope, support files and registered 0.3.54 identity before projecting the
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
The 0.3.52 local acceptance covers 26,940 bilingual current-behaviour cases,
4,000 unchanged seeded omission renders and 28 native output groups; all 185
submission PDF/LibreOffice preview pages were visually reviewed. That evidence
is tied to the tested source hashes, not to an arbitrary later version label.
Verify that the clean paired candidate preserves those rendering inputs. Review
the candidate in the target Word environment before promoting it as a fully
Word-tested submission release. Do not publish changed assets under 0.3.51.

The 0.3.54 Word repair was verified locally on 52 bilingual review/submission
groups and all 356 preview pages, including consecutive long-resource tables,
14–18-paragraph boundaries, omitted fields and long-answer controls. Only the
owned long-table separator and bounded short final-row rules change; English
and Chinese prose, translation units, PDF assets and historical oracles stay
unchanged. The 334 English and 492 Chinese unit tests pass on that repair.
This bounded evidence is not arbitrary-input or Microsoft Word certification;
new package identities must still reproduce the verified rendering inputs.

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
