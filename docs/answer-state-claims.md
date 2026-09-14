# 0.3.9: truthful answer states (bounded experiment)

This patch follows 0.3.8 on `fix/answer-state-claims`; it does not update the
official 1.30.1 upstream baseline, the knowledge model, or the runtime.

Q5's mapping-limit introduction is neutral for all answer states. It describes
the limits of mapped fields, not an assertion that a respondent has supplied
storage arrangements and backup needs. Existing `partial` / `unmapped` location
and schedule markers remain mapping limitations, not newly invented user fields.

Q11 now renders Yes, No, and unspecified long-term support for each selected
special-purpose repository. The fact is scoped to the distribution item, under
publication = Yes and repository kind = Special. Inactive follow-ups cannot
become answers. The independent service-level answer remains in the same list
item, without adding a paragraph for every sentence. A No is not softened into
“not yet”, and a Yes does not establish a duration, maintenance plan or funder.

The public Common KM 2.7.0 English/Traditional Chinese compiled inventories
agree on question `f83a9afd-c6de-452b-be9f-bd76e5eb6b54` and its Yes/No answer UUIDs.
The previously unused No UUID is now bound explicitly. The synthetic
`support-mixed` fixture exercises three repositories with Yes / No / missing
and independent Download / Simple / Advanced service levels. Existing fixtures
are unchanged. Unit tests also cover missing/inactive parents and stale replies.

No PDF CSS, Word reference preparation, Lua, free-answer transformation, or
official Science Europe question heading changes are part of this patch.
This is not full SE-3a / SE-5b coverage or release acceptance. Actual bilingual
output evidence belongs in the corresponding Chinese repository review archive.
