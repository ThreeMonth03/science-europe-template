# 0.3.23 Q9 Word dataset-label continuity

Short-lived branch `fix/q9-word-labels` follows 0.3.22 `f1f8970`; official
Science Europe upstream stays 1.30.1 / `22d60aae4b63ee677477ac0c73097807284aaf9f`.
No independent Chinese layout or Jinja branch is introduced.

The preserved English Word example stranded a Q9 produced-data name on page 4
and its first ethics flag on page 5. The Lua rule now styles only a Strong-only
Plain name before a short nested flag list, inside a direct Q9 answer list.
Names are limited to 80 display units; 1–2 plain flags to 160 units each; outer
lists to 32 entries. CJK counts double. Two template-owned flags become one
plain list paragraph, preserving both complete sentences in original order;
one flag stays unchanged. A name Para lets Word honor `Pilot List Lead`.

The first style-only native attempt fixed Q9 but increased the complete English
Word example from 7 to 8 pages, pushing Q15 to a sparse last page. It is retained
as a rejected layout tradeoff. Joining only the two fixed flag sentences avoids
that extra line; native validation now also rejects whole-Word page growth.

No generic keep rule, Jinja, translation, PDF CSS, reference style or font changes.
Long/complex labels, flags and authored answers remain unchanged. A malformed
empty list item rejects the Q9 transformation to avoid Pandoc normalization.
Missing flags are not converted into negative answers or fabricated policies.

29 pinned Pandoc probes check both AST and actual DOCX XML, including boundaries,
partial/missing flags, nested author content and mixed malformed fallbacks.
Actual bilingual native exports compare the original failure, empty/negative
controls and new partial, eight-dataset and 30-paragraph purpose fixtures with
genuine 0.3.22 exports. Only Q9 label styles may change in Word; HTML question
bodies, native PDF text/pages and every other Word block must stay exact.
The Word oracle builds an exact expected XML projection: the name style plus
one merged plain flag paragraph, with no other text, formatting or table edits.

The Chinese repository locks this source commit and proves all 731 translations
unchanged. Re-run both native outputs and probes after upstream upgrades, even
when Git merges cleanly. This is not full-document or Microsoft Word acceptance;
short-budget prompt wrapping, sparse pages and stock-worker Markdown tables
remain separate acceptance work. No release/tag/main merge is implied.
