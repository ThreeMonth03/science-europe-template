# Completeness-contract experiment

Status update (2026-09-11): this remains a partial proof of concept. The custom
translation profile and machine-ID extraction problems have been fixed; the
translation and structure audits now pass. Actual bilingual HTML/PDF/DOCX have
been rendered. Full acceptance is still blocked by unsupported Markdown pipe
tables and unreviewed content outside the pilot. See the new Chinese repository's
`docs/pilot-results.md` for evidence and the remaining limits.

## Decision being tested

Keep one maintained English Jinja template as the executable source, improve
its content logic and layout, and then produce Traditional Chinese through the
existing translation pipeline. Do not maintain a second independent Chinese
Jinja tree, and do not put an LLM in the document-generation runtime.

This experiment asks whether a small, reviewable change to the upstream
template can prevent incomplete questionnaires from producing deceptively
complete-looking documents.

## Source standard

The normative content source is Science Europe, *Practical Guide to the
International Alignment of Research Data Management — Extended Edition*
(January 2021), DOI
[`10.5281/zenodo.4915861`](https://doi.org/10.5281/zenodo.4915861). Science
Europe describes the six core requirements as minimum requirements and gives
15 questions plus guidance for researchers.

[`../requirements/science-europe-2021.json`](../requirements/science-europe-2021.json)
records every question, its required topics, its Jinja file, and the detailed
DSW bindings audited in this experiment.

## Output contract

For each required fact:

| Questionnaire state | Document behaviour |
| --- | --- |
| Answered | Render the supplied fact. |
| Partly answered | Keep the supplied facts and show each material gap. |
| Unanswered | Render a visible `Information not provided` marker. |
| Explicit No / not applicable | Render that decision; never infer it from an empty reply. |

Language-neutral HTML attributes identify the semantics:

```html
data-requirement-id="SE-3a"
data-fact-id="backup-frequency"
data-status="missing"
```

These identifiers are the future English/Traditional-Chinese alignment
mechanism. Translated prose may change while the IDs remain stable.

## First vertical slice

The three selected questions exercise different Jinja failure modes:

- **SE-1a / Question 1:** an upstream catch-all `else` previously rendered an
  unanswered reply as “no instrument dataset.” Re-use and provenance could
  also disappear.
- **SE-3a / Question 5:** an unanswered top-level choice previously yielded an
  empty answer block. The selected mappings do not yet cover storage/backup
  locations and backup frequency. This is not proof that the entire KM lacks
  suitable questions; a full-KM audit is still required.
- **SE-6b / Question 15:** expertise, hardware/software, project costs, amounts,
  allocation, and cost coverage could disappear independently.

The mapping gaps are experimental results. Jinja must not invent answers.
First audit the complete KM, then bind existing suitable questions or propose
KM additions; do not infer missing questionnaire coverage from one template file.

## Acceptance criteria

The experiment passes when:

1. All 15 official questions remain present and ordered under all six core
   requirements.
2. For the three selected questions, unanswered, explicit negative, partial,
   and populated states are distinguishable in the generated HTML.
3. A missing parent answer cannot suppress the whole answer block.
4. English and translated output can be aligned using stable IDs rather than
   prose similarity.
5. `dsw-tdk verify` succeeds for the template package.
6. A real DSW rendering sample is reviewed in HTML, PDF, and DOCX before the
   experiment is promoted.

## Running the checks

```bash
python -m pip install -r requirements-dev.txt
make check
```

The unit tests render the selected question templates with empty, explicit-No,
and partial reply maps. They also verify the 15-question contract and its UUID
bindings. `dsw-tdk verify` validates the complete package structure.

## Deliberate limits

- Questions other than SE-1a, SE-3a, and SE-6b are recorded but still marked
  `upstream-unreviewed`.
- This branch has not changed the knowledge model. Consequently, an unmapped
  Science Europe topic remains visible as missing in this slice even when its
  mapped fields are answered. These markers must not be used to judge the full KM.
- Runtime LLM generation and JSON-to-prose generation are outside this
  experiment. They can be evaluated later without becoming a workaround for
  missing source data.
