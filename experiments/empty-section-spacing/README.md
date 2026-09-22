# Empty-section print spacing prototype

Opt-in experiment against exact English `2eebf1f783a6017fe25712c1b01c6a708adfedab`
(0.3.47). Production `src/`, `template.json`, format UUIDs and Word steps are unchanged.

The accepted 0.3.47 source still places Q15 alone on the last page of the English
all-empty submission PDF. An earlier unguarded spacing diagnostic reached two
pages; it was not safe to apply to answered documents.

This recipe appends only print CSS. It requires an owned section id, the original
direct heading position, the exact question count, and the trusted empty marker
on every direct question. Mixed sections, unknown structures and nested authored
markers do not qualify. The marker's conservative 0.3.47 Jinja classifier remains
unchanged. CSS is not a replacement for that classifier or a generic HTML sanitizer.

Only section bottom margin and section-heading top/bottom margins change. Font
sizes, line heights, question headings, empty answer boxes and all text remain.
The `@media print` scope preserves screen styling; actual DOCX and review PDF
equivalence must also be checked using native package renders.

The independent parsed-tree oracle is checked against the pinned public worker's
actual selector engine. Unit tests and the opt-in engine CI step cover all six
section shapes, every filled/empty combination within a section, unknown or extra
nodes, nested/authored markers, print versus screen, and unchanged fallback styles.
The small engine fixture is not a full-font or whole-document acceptance claim.

The Chinese repo rebuilds this overlay through the existing translator, retaining
all 775 translation pairs and byte-checking every other source, asset and format
step. Its experiment lock identifies the English recipe commit separately from
the production pipeline source lock. Neither repo uses a permanent submission branch.

Do not promote or tag a release on the strength of fewer pages alone: the real
paired documents, mixed/long cases and unchanged Word/review controls must pass.
Public native results are recorded in the paired Chinese repo; private answers,
documents and screenshots stay outside both repositories.
