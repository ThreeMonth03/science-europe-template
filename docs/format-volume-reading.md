# Q2 format and volume experiment (0.3.4)

The short-lived `feat/format-volume-reading` branch follows `feat/reading-units`,
including its clean-CI dependency fix. The official 1.30.1 baseline stays fixed.
This is an experimental package identity, not a published release.

Each format now has one template-owned reading paragraph using the existing
PDF CSS and Word Lua paragraph-joining contract. Free-text reasons retain their
own Markdown paragraphs, lists, case and punctuation. Missing details appear
in a separate, consolidated gap paragraph, not mixed into known facts.

Non-standard / unsuitable decisions survive absent followups. An explicit
decision not to convert is distinguished from an unanswered conversion question.
File count and average size survive independently, including zero. A total
entered directly is retained. Count × average is no longer calculated here:
the old integer/float coercion and two-decimal rounding could misrepresent data
(e.g. two 0.0001 GB files as 0.0 GB). Input numeric validation is not implemented
by this template; it never silently substitutes a guessed total for bad input.

New `format-rich` and `format-partial` fixtures leave old fixture files unchanged.
Tests cover selected decisions, inactive followups, blank/zero quantities and
authored blocks. The Chinese repo adds translated branch probes and actual
HTML/PDF/DOCX checks. Controlled comparison excludes only the identified Q2
format block, not all of Q2. Existing collection and all fourteen other questions
must stay unchanged for the same fixture inputs.

Q2 remains a critical overlap in `.upstream/base.json`. Future official updates
need a semantic review of changed question UUIDs and decision logic, plus these
tests and bilingual sample review; a conflict-free Git merge is not sufficient.
No CSS, Word filter, official baseline, KM or runtime worker is changed here.

This does not establish complete SE-1b coverage, all other question branches,
production Markdown-table support, or pagination in Microsoft Word itself.
