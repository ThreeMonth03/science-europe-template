# 0.3.27: state known identifier assignment once

Q13 previously stated that persistent identifiers would be assigned, then stated
who would assign them. When the assigner is one of the three recognized choices,
the unchanged assigner sentence now carries both facts: the outer paragraph marks
the affirmative identifier policy and an inner span marks its named role.

If the assigner is missing or unsupported, retain the separate affirmative parent
sentence and the existing missing/review notice. Resolution Yes/No/missing/review,
inactive parent choices, dataset/distribution boundaries and authored reuse answers
remain independent. No answer or unknown state is inferred from another field.

This changes only Q13 Jinja and experimental version metadata. CSS, Word Lua,
reference styles, fonts and question wording remain unchanged. The existing Chinese
translation tree is refreshed; its reviewed sentence/translation pairs are retained,
not rewritten by an LLM or maintained as a separate Chinese Jinja fork.

EN and ZH use the short-lived `fix/identifier-concise-prose` branch; ZH locks an exact
EN commit. Native bilingual HTML/PDF/DOCX and missing-answer comparisons are required
before accepting the reading experiment. This document is not a release claim or
Microsoft Word acceptance.
