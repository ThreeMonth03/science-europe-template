# Q3 publication gaps — 0.3.36 print experiment

Two adjacent, unanswered publication follow-ups (access instructions and
harvestable/indexable form) were printed as two individually bordered boxes.
The owned CSS layer now gives exactly that pair one border and reduces its
internal spacing. Both original sentences and their independent fact IDs and
`missing` statuses remain unchanged. This is a visual grouping, not a new answer
and not a claim that the two requirements are interchangeable.

Only the exact two direct, plain-text paragraphs in Q3's metadata policy qualify.
A single gap, unsupported option (`needs-review`), explicit No, `unmapped` fact,
additional child or rich/authored content does not qualify. Screen HTML and
Word rules are unchanged. The current English and Chinese fixed texts are
bounded by engine checks; future wording changes must rerun these checks.

No Jinja, questionnaire binding, prose, translation, Word Lua/reference, font,
or upstream stylesheet changes. `metadata_gap_panel_contract.py` removes only
the exact reviewed incremental CSS before the retained historic layout gates.
It cannot whitelist arbitrary later changes. The Chinese repo pins this English
source; there is no separate Chinese CSS fork or long-lived per-version branch.

`probe_metadata_gap_panel.py` checks 30 real Jinja combinations and 47 pinned
print/screen/near-page-end cases per source tree. It checks same words, wrapping,
font metrics and fallback geometry. Native full-document PDF/DOCX verification
is a separate gate, recorded in the Chinese review repository. This experiment
does not establish full DMP quality or Microsoft Word acceptance.
