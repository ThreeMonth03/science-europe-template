# Shared-source submission preview (0.3.44)

This integrates the marked-notice, overview/prose and neutral-dataset-label trials
from the paired Chinese repository. It does not make arbitrary incomplete DMPs
submission-ready. The default remains internal review.

## Scope

- Hide explicitly owned missing-info paragraphs in submission preview only.
- Preserve affirmative restrictions, required software and quality-control facts
  even when their descriptions are absent; unknown answers stay unknown.
- Omit absent overview fields and empty overviews. Preserve supplied `0`, `N/A`,
  grants, funder status and the actual project creator.
- Join selected fixed quality-control methods with the selected Other category
  when its description is absent. Never rewrite authored prose or punctuation.
- Use neutral typed dataset labels at the original questionnaire-list position,
  including filtered reference lists. Review still requests missing names.
- Retain the six Science Europe sections, fifteen questions and all format UUIDs.

The 21 changed files are Jinja. CSS, Lua, fonts, reference DOCX, conversion steps
and allowed knowledge-model declarations do not change.

## Translation and provenance

Chinese is generated from this English source through the existing locked tool.
Classification values use exported `DATASET_*` constants: string arguments would
otherwise be exposed as translatable text by the current extraction tool.
Only the visible labels may be translated.

`requirements/submission-preview-delta.json` pins the independently tested native
prototype and complete file hashes. `submission_preview_contract.py` reverses
only the exact constant adaptation, validates every current source byte, and
exposes the exact 0.3.43 inputs to older regression gates. No HTML cleanup is used.
New tests compare current review bytes against that baseline for every fixture.
The paired repo checks actual translated builds against the frozen prototype and
independent fact/label oracles; historical evidence is never rewritten.

## Versioning and remaining acceptance

English and Chinese use paired version 0.3.44. Chinese pins a full English commit,
not a moving branch. Review and submission are formats of the same package;
neither gets a permanent branch. Work remains on `fix/profile-pagination` until
native integrated PDF/DOCX comparisons and the remaining acceptance work pass.
This is not an upstream merge, a main-branch merge, release or production upload.

Still out of scope: person/project/resource/software-name placeholders, unnamed
formats, empty funder items and ORCID parsing. Full suppression, Science Europe
or Taiwan submission compliance, and Microsoft Word visual acceptance are not
claimed. The frozen 0.3.43 native trials are evidence for those trials, not a
substitute for rendering the actual integrated 0.3.44 packages.
