# Output profiles pilot (0.3.38)

One maintained English template, translated by the existing locked pipeline;
two named output profiles per language. No parallel review/submission branches,
runtime LLM, CSS hiding, or text search-and-delete of user answers.

The existing HTML/PDF/Word UUIDs remain review outputs. Three new stable UUIDs
select thin submission entry points, which set `output_profile = 'submission'`
and include the same HTML/PDF/Word source. Engines, CSS, Lua, reference DOCX and
fonts are unchanged. LaTeX/ODT retain their existing review behavior.
An absent or unrecognised profile retains diagnostics conservatively.

## Deliberately limited coverage

See `requirements/output-profiles.json` for the machine-readable boundary.
This pilot optionally removes Q3 diagnostics, the Q5 mapping-limit box, the Q11
preservation-selection review note, and an entirely missing funding row.
When quality control is selected without any methods, submission retains the
affirmative plan as a **partial** fact, not a completed-method claim.
Empty Q3 storage subheadings are not emitted. The 15 questions and 6 Science
Europe sections remain; a completely unanswered question is not invented or
silently certified. Some other questions still show diagnostics in submission
preview. This profile therefore is not ready for real grant submission.

Authored text resembling a warning, explicit No, restrictions, quantities,
zero values, links and filenames are never suppressed by string matching.
The companion internal checklist is derived from review output and does not
certify completeness: it cannot discover fields not mapped by the template.

## Version management

Use the same package version for both profiles. Work on the short-lived
`feat/output-profiles-experiment` branch; do not create permanent `submission`
and `review` branches. The Chinese repository locks the exact English commit
and retains its own reviewed translations and format display labels. Future
upstream upgrades remain isolated upgrade branches with semantic and native
output comparisons; merging upstream alone is not acceptance.

Only if actual users need two separate DT entries should packaging produce
two distinct template IDs from this same source, with the profile fixed at
build time. That is not implemented here and does not justify a third repo.

## Verification

`test_output_profiles.py` compares every synthetic fixture in review mode to
the frozen 0.3.37 source, and checks an independently specified submission
projection in both escaping modes. Existing regression tests remain active.
The bilingual native pilot additionally exercises the real output format UUIDs,
PDF/Word conversions and authored warning-like text. A passing build does not
establish Microsoft Word or full-document visual acceptance.
