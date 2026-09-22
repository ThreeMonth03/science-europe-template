# Submission reading integration — 0.3.45

This integrates the bounded prototypes frozen in the companion Chinese repo's
`reviews/2026-09-21-word-asset` archive at commit
`71ae7c33323b8b794c3add6f0537dfe86f4dcb7e`.
It is a paired-source experiment, not a deployment or global submission guarantee.

## Scope

- Five shared Jinja files: macros, project overview, Q9, Q12 and Q15.
- Submission-only neutral project/resource/software names retain original indices.
  Existing neutral dataset numbering remains unchanged. Review keeps its notices.
- Missing Q9 flags do not produce submission prompts or invented assurances.
  An explicitly selected alternative legal basis remains visible as a partial fact.
- Short owned Q9 introductions share a reading unit; authored block order remains.
- Empty Q15 budget groups are omitted in submission only. Partially answered
  groups, zero amounts and original numbering survive.
- Two shared Word assets keep narrowly eligible short Q9 tables together.
  Long, complex, adjacent or nested tables stay on the previous fallback path.

The Word Lua filter and XML rewrite helper are assets, not translation units.
Both existing Word formats use them with unchanged format UUIDs. CSS, fonts,
reference DOCX, the existing Word filter and translator implementation are unchanged.

## Translation and version management

English remains the source of shared logic. The Chinese repo locks this English
commit and the existing translation-tool commit, with paired version `0.3.45`.
Q9 names sentence arrays so the existing Chinese joining rule applies. Q15 uses
complete conditional phrases so translation does not inherit English word order.
The reviewed translation delta retains all 762 previous occurrences and adds five;
duplicate migration gaps must reuse identical existing translations.

Continue development on the working feature branch, then review a paired release.
Do not introduce permanent branches per language or output profile. Future upstream
updates enter as a reviewed source change with explicit compatibility and output
tests; do not merge upstream directly into generated Chinese Jinja.

## Gates

`requirements/submission-reading-delta.json` records every before/after source hash,
the exact metadata delta and the immutable prototype seal. The new contract rejects
extra, missing or modified files before returning the exact 0.3.44 source view.
Earlier gates then run their unchanged historical assertions. Mutation tests cover
source, assets, metadata, format identities and the historical projection.

The Chinese companion validates the real translation build and package bytes,
then runs structural and native bilingual review/submission comparisons separately.
Prototype native results do not substitute for rendering the integrated packages.
LibreOffice previews do not establish Microsoft Word pagination acceptance.
