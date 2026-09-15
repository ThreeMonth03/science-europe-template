# Identifier follow-up completeness (0.3.15 experiment)

Under Q13's explicit "identifiers will be assigned" branch, independently handle
the assignment actor (project steward/PI, institutional steward or repository)
and the repository's resolution guarantee (yes/no). Missing child answers used
to disappear. Their absence must not erase an answered sibling or become a
negative answer; a negative resolution guarantee must remain visible.

New per-child markers are `identifier-assigner` and `identifier-resolution`,
mapped to the existing SE-5d requirement. Known affirmative values are `complete`;
the explicit negative resolution answer is `explicit-no`; empty or whitespace-only
values are `missing`; nonempty unrecognized values are `needs-review`. Do not trim
a padded UUID into a valid choice or echo an unknown raw value into the document.
The existing parent `persistent-identifier/complete` describes ONLY the supplied
decision to assign an identifier, not completeness of its follow-ups or all Q13.

Preserve all known policy wording and the 0.3.14 joined policy paragraph. Put
notices immediately after it, outside `.dataset-policy`. Capture the two fixed
field labels separately and group them by status: at most one missing paragraph
and one review paragraph per distribution, each with one terminal period. The
existing translation pipeline localizes the separator and punctuation. Do not
hand-edit generated Chinese, add bullets per missing field, or flatten author text.
Reset lists within every active distribution; use item identity, never names.

Visual review caught an English PDF orphan: a child notice moved to the next
page without its distribution. Wrap only the fixed policy and notices in an
`identifier-followup-unit short-reading-unit`, reusing existing PDF and Word
rules. The independent oracle enforces the 500-character bound and rejects
author prose, lists and tables inside this unit. Keep notices as separate
paragraphs; only non-final paragraphs inherit the existing Pilot Lead style.
Check the complete heading, policy and notices together on one native page,
not merely the heading and first answer. Complete controls keep their style.

Inactive, negative, missing or unsupported parent decisions must not produce
child promises or child notices. Publication gating is unchanged. No new KM
questions, types or options; no upstream baseline update. The four-distribution
fixture covers both fields missing, an answered actor with negative resolution,
a missing actor with negative resolution, and an answered actor with missing
resolution. Complete preservation is the unchanged control. Unsupported UUIDs
are offline robustness cases, not claimed as valid native KM fixtures.

Ownership: only Q13 source changes. CSS, Word Lua/reference, questionnaire titles,
all other Jinja files, the conversion tool and existing fixtures remain unchanged.
The official baseline is still 1.30.1 / 22d60aae4b63ee677477ac0c73097807284aaf9f.
Both repos use short-lived `feat/identifier-followups`, based on 0.3.14; Chinese
locks the exact English commit and maintains reviewed translations, not independent
branch logic. This existing critical Q13 overlap must be revalidated on upgrades.

Acceptance must compare the same fixtures through stock and patched workers.
Only the two child markers, validated notices, bounded wrapper and its non-final
Word keep styles may differ from 0.3.14; restore those exact additions before comparing all 15 questions, Word body/tables
and PDF/preview body text. Validate native notice boundaries and punctuation.
This is not whole-DMP or Microsoft Word acceptance: Q13 unknown repository-type
wording, other uncovered branches, Word's budget tail page and stock Markdown
tables remain separate issues. No merge, formal tag/release or production deployment.
