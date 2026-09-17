# Q3 metadata follow-ups — 0.3.33 experiment

Preserve the public Common KM 2.7.0 data/variable dictionary Yes and No answers.
Only the metadata Explore branch asks for a missing dictionary decision. A
nonblank unsupported choice is needs-review, never an inferred No. Public
metadata No with an empty/whitespace reason gets its own missing prompt; public
Yes gets independent prompts for missing/unsupported access instructions and
harvestable/indexable form. Nonblank authored reasons remain Markdown blocks.

Bindings are recorded in `metadata-followup-bindings.json`; native fixtures must
also pass the compiled public English/Traditional Chinese KM validators.
This does not establish coverage of all Science Europe requirements.
Explicit No for DC/DataCite/DDI/keywords/W3C PROV remains outside this change.

Only Q3 and three UUID constants change in template source. CSS, Word Lua,
reference DOCX, fonts, storage capacity and other questions are unchanged.
The independent frozen 0.3.32 projection checks 1,726 whole-Q3 DOM comparisons
per language (including both autoescape settings), composed with the retained
866 capacity comparisons. Mutation tests reject changed authored text, quantity,
negation and punctuation. Native HTML/PDF/Word checks are separate gates.

Eight cases per language: dictionary Yes/No only, partial public metadata,
private metadata with missing/nonblank Markdown reason, complete metadata with
explicit negative follow-ups, empty and negative controls. Fixtures are synthetic.

Development is on `fix/q3-metadata-followups`, descended from the last reviewed
experiment, not a new long-lived upstream branch. The Chinese repository pins
the exact English commit and retains the existing translation pipeline. Upstream
updates remain separate reviewed intake changes (see `upstream-upgrades.md`),
never an automatic merge of new logic into a reviewed language release.
No release, production upload, or Microsoft Word acceptance is implied.
