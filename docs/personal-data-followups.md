# 0.3.21 personal-data follow-ups

Short-lived branch `fix/personal-data-followups`, from 0.3.20 `7f2fed6`.
Official upstream remains 1.30.1 / `22d60aae4b63ee677477ac0c73097807284aaf9f`.

Q7 now distinguishes missing legal basis, unspecified Other, missing stored-data
identifiability, additional safeguards, transfer decision and transfer measures.
Only reachable follow-ups are prompted. Selecting the safeguards container is
not evidence that its child questions have been answered. Blank free-text replies
remain missing; explicit transfer No remains visible and ignores stale Yes data.
These are informational omissions, not invented answers or new legal obligations.

Free-text safeguards and transfer measures are rendered into `answer-detail`
blocks after their leads, never Markdown block content inside a paragraph.
Authored paragraphs, lists, emphasis, punctuation and link destinations are kept.
The upstream English misspelling `psuedoanonymized` is corrected to `pseudonymized`.

The compiled 2.7.0 KM labels the GDPR parent answer only **Explore**. Q9 no longer
turns this navigation choice into a completed assessment. Its public-interest
sentence now reports the stated legal basis without claiming it outweighs privacy.
Other without its specific follow-up produces a complete sentence referring to Q7,
not a dangling colon. No legal-compliance determination is made by this template.

`generate_personal_data_fixtures.py` adds four bilingual synthetic fixtures and
reuses four unchanged controls. `validate_pilot_fixtures.py` verifies paths against
both server-compiled KMs. Stale descendants are adapter-only negative tests, not
misrepresented as reachable native questionnaire answers.

Maintain logic only here; the Chinese repo locks this commit and migrates its
translation tree. The reviewed change retains 718 of 723 old sentence pairs,
replaces/removes exactly five and adds thirteen; all other pairs must match exactly.
Q7/Q9 are already critical upstream overlap paths. Upgrades must rerun these
branch, block-structure and native-output checks even if Git reports no conflict.

PDF CSS, Word Lua/reference styles and Q15 are unchanged. Short budget prompt
wrapping, whole-document blank space, other consent/DPIA follow-ups and production
worker Markdown tables remain separate work. Native evidence is in the Chinese
pipeline repository; no main merge, version tag, registry or production deployment.
