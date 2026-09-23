# Reuse preparation prose prototype

Baseline: exact EN `678787f2fdf047a3d6cc3577d4589d64ba2cd846` (0.3.48).
Production `src/` and version are unchanged. This is a bounded Q1 overlay,
not an upstream merge, publication or accepted release.

Nine fixed fragments correct harmonization, machine-readability and metadata
wording. The corresponding nine complete EN/ZH units are reviewed in the
paired Chinese repository's `experiments/reuse-preparation-prose/units.json`.
The normal locked translator generates Chinese Jinja; no independent Chinese
branch logic is maintained. The machine-readable paragraph now emits complete
English sentences in each branch. This avoids the translator's exact-match
special rule tied to the old, ungrammatical upstream paragraph. Answer-state
meaning, paths, paragraph count, styles, authored labels, links and list
punctuation expressions are preserved; the Jinja syntax is deliberately changed.

The probe checks affirmative, negative, absent, empty, unknown and zero-like
choices; stale children under inactive parents; repository versus other
sharing; metadata standards with links, punctuation and long names; both
autoescape settings and review/submission/unknown profiles. An independent
sentence oracle checks paragraph text and links. All 396 full-fixture renders
retain six sections, fifteen questions and identical content outside the
bounded block. Unknown output profiles retain the existing review behavior.

Out of scope: additional missing-answer diagnostics, new statements for
negative parent answers, filtered-KM reachability improvements, blank list-item
repair, global punctuation cleanup, layout redesign, production integration.
Do not interpret passing tests as completeness or Microsoft Word acceptance.

Run with the repository requirements installed:

```sh
python -m unittest discover -s tests -p test_reuse_preparation_prose.py -v
```
