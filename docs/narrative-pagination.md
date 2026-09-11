# 0.3.1: bounded narrative and pagination experiment

Branch `feat/narrative-pagination`, derived from the 0.3.0 experiment. No release,
upstream-baseline advance, new KM, live deployment, or separate Chinese logic.

Q5 owns the already mapped archival/backup facts. Its fixed sentences are grouped
using the existing `dataset-policy` presentation rule; gap paragraphs are separated
by `reading-gap` blocks so they cannot be merged into ordinary prose. User answers
are never joined by this rule. Precise sites and schedules remain mapping limits.

Q6 removes its duplicate archival paragraph, including an unjustified claim that
not needing frequent backups establishes an infrequent actual backup schedule.
It links to Q5 only when archival Yes was answered. The reference is outside the
answer-presence check: an archival-only project must still show a security gap.
Access controls, risk and security content are otherwise unchanged; this does not
claim that all those inherited branches have been reviewed.

Q10 restricted-access introduction is a complete translatable sentence, separate
from supplied Markdown; absence of terms is explicit. Q10 dates and Q11 repository
list introductions use an `answer-lead` div, because paragraph HTML attributes did
not produce the Word keep-with-next style in actual 0.3.0 output.

Q9's fixed personal/sensitive-data flag list is kept together in PDF. Q14's owned
responsibility block requests keep-together only below 500 rendered characters;
the Word filter also checks the length and permits only plain paragraph blocks.
No whole question, arbitrary long answer, or multi-page section is made unbreakable.
Font size, body spacing and line height are unchanged from 0.3.0.

Old fixtures remain unchanged. `archive-only` tests the cross-reference/missing
security distinction and backup-need No. `narrative-long` adds eighty independent
paragraphs to a restricted distribution; they must remain separate and complete.
The Chinese actual-output checker compares all fifteen questions of the three old
reading fixtures against 0.3.0, allowing only declared Q6/Q10 editorial changes.

Upstream changes to Q5/Q6/Q9/Q10/Q11/Q14, layout and Word filter need semantic and
render review. A clean Git merge cannot establish option reachability, Chinese
sentence quality or equivalent pagination. Worker table support is still a separate
pinned local experiment and is not part of this template-only fix.
