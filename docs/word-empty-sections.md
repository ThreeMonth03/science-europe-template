# Integrated Word empty sections (0.3.50)

This paired integration reproduces the accepted Word prototype at English
`2f63e964c481d08b949ec4663209f3d2e0f1b8e4`. It changes only
`src/word/question-spacing.lua` and `src/word/question-spacing.xml` from 0.3.49.

For an exactly recognized, entirely empty submission section, its Heading 2
receives 3 pt before / 2 pt after spacing. Its non-final question headings keep
with the following question. The final heading can break before the next section.
No font, reference DOCX, format UUID, conversion step, question or answer changes.
Review stays the default; all 15 original questions remain in submission.

The exact source/metadata gate runs before every historical regression projection.
The frozen prototype recipe and engine are byte-locked separately. CI runs its
121 cases on actual production assets, covering malformed/untrusted markup,
authored content, Q5's empty skeleton, XML autoescaping and unchanged non-Word output.
Use `python scripts/probe_word_empty_sections.py --output <new-path.json>`.
The original experiment runner remains a historical 0.3.49-only recipe; replay it
from the locked prototype commit, not the current production checkout.

Chinese remains generated through the existing locked translation tool. Both
versions move together to 0.3.50 and its pipeline locks the full English commit;
all 775 translation files must remain byte-identical. The paired native comparison
and local workflow evidence are recorded in the Chinese repo, separately from
source integration. This is not deployment or Microsoft Word acceptance.
