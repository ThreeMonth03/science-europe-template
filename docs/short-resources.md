# 0.3.40: bounded Q15 PDF reading unit

One PDF-entry hook captures the original document, then applies a presentation
helper. Only the unique, template-owned Q15 opening tag may receive the class
`pdf-short-resources` and `style="break-inside: avoid"`. Every other input byte
is preserved. The underlying question Jinja, translation strings, shared CSS,
fonts, Word filters and Word reference are unchanged. Both PDF profiles use the
same hook; HTML exports and Word never call it.

The rule deliberately accepts only one project, one ordinary three-column table,
one or two budget rows, a simple known overview and at most two flat training
list items. Missing/unknown fact markup, additional projects, large answers,
links, images, nested lists/tables, forced breaks, unknown attributes and invalid
structure fall back unchanged. It is a conservative layout grammar, not a
general HTML parser or validator. Authored plain text, including wording that
looks like a warning, is preserved rather than interpreted as a missing answer.

Bounds are 1,200 weighted visible units for the whole question, 160 per paragraph,
80 per list item, 360 for the question heading, 80 for the budget heading and 40
per column label. Resource/purpose, amount and funding cells are capped at
300/40/80 units with exactly 3/1/1 paragraphs. U+2E80 and above count as two
units. At most 16 paragraphs and 16,000 source characters are accepted. These
limits are tested in the pinned layout engine, not claimed to predict arbitrary
future fonts or renderers.

The independent BeautifulSoup oracle checks parsed structure rather than reusing
the Jinja classifier. Probes exercise autoescaping both on and off, byte-exact
fallbacks, ASCII/CJK boundaries, zero, authored warning-like text, multiple rows
and projects, malformed markup and whole-unit length limits. Source gates first
remove only the exact new PDF entry/helper, then retain the frozen 0.3.39 and
0.3.38 checks. Native bilingual exports and Word regression are separate gates.

This is still an experimental derivative, not a completed or submission-approved
DMP. It neither widens the optional-notice pilot nor fixes every pagination issue.
