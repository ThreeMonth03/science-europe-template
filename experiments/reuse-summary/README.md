# Q1 reuse-summary prototype

Non-release experiment based on exact English commit
`1b0c82d9bee6984df7f11dc072ebf3c8f7726e08` (0.3.46). Production `src/`,
`template.json`, CSS, fonts and Word assets are unchanged.

## Bounded change

Replace only the non-reference dataset cluster between the scope and personal-data
comments in `src/questions/01-how-data.html.j2`. The new helper groups explicitly
selected scope, format, stability and conditions-of-use facts into one paragraph
per dataset, with independent fact markers. Full sentences replace grammatically
broken fragments. An explicit “can use directly” reply is now represented too.

Authored purpose and restrictions are not summarized or rewritten. Restrictions
remain Markdown in a separate block, avoiding block elements nested in a paragraph.
Selecting “other conditions” retains that known restriction even if its description
is missing: review adds a prompt; submission does not. Neither invents the terms.
Missing/unknown choices do not suppress filled siblings or create unfinished prose.
No new missing prompts are added for scope, format or stability in this experiment.

When a compiled KM is supplied, the helper checks the chapter, list, selected branch,
question types and descendant edges before displaying its facts or restrictions.
This guard covers the new summary, not every legacy Q1 clause. Legacy test callers
without a KM still use explicit known reply choices. Dataset boundaries, original
numbering, source, purpose, ethical clauses and Q2–15 are not restructured.

The Chinese repo's `experiments/reuse-summary/build_prototype.py` applies this English
overlay to verified 0.3.46 packages, then uses the pinned existing translation tools.
Chinese is not maintained as a separately patched Jinja implementation. Captured
fixed sentences are trimmed because translation expansion can add indentation;
this does not trim or normalize authored Markdown.

## Validation and reproduction

Run `python -m unittest discover -s tests -p test_reuse_summary_prototype.py -v`
with the repository's development dependencies. The reusable `probe.check` also
checks the actual translated package: 1,844 cases per language, including 1,600
choice/profile/autoescape combinations, missing and long restrictions, inactive
parents, filtered entities, detached edges, wrong types and two nameless datasets.
An independent empty-helper projection checks unchanged Q1 content. It rejects
unrelated source changes rather than silently rebasing the overlay.

Native offline A/B results and limits are recorded in the companion Chinese repo's
`reviews/2026-09-22-reuse-summary-prototype`. Real contexts and documents stay private.
Passing this experiment is not whole-document visual acceptance or a release.

## Version management

Both repos use the short-lived `fix/reuse-summary-prototype` branch. The matching
branch name is a convenience, not the version lock: the recipe's exact baseline,
source hashes, translation delta and packaged ZIP hashes identify the pair.
Prototype packages have separate IDs (`science-europe-reuse-summary-prototype` and
`science-europe-reuse-summary-prototype-zhtw`) and version 0.3.47; they cannot be
mistaken for an integrated 0.3.47 release of the production templates.

If accepted, integrate the English change first, then pin that reviewed commit in
the Chinese production pipeline and migrate only the declared translation delta.
Rebase/merge upstream changes as reviewed upgrades, not automatic conflict
resolution. Keep review/submission as formats of the same source, not permanent
branches. Archive the prototype oracle when integrating; do not overwrite evidence.

## Still outside scope

Empty submission headings, remaining Q1 harmonization/computer-readable prose,
document-wide paragraph rhythm, Taiwan extensions and native Microsoft Word/DSW
server acceptance remain separate work. No Science Europe requirement is removed.
