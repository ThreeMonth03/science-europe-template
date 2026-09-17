# Short Q5 context pagination — 0.3.34 experiment

0.3.33 added necessary Q3 information but exposed three Chinese Q5 context
separations: metadata-partial Word, metadata-private PDF and Word. In the last
case even the limitation introduction and its two bullets separated.

Only a bounded owned Q5 answer qualifies: workspace policy followed immediately
by the fixed two-item operational-limitations block, at most five fixed policy
paragraphs, plain text, recognized fact/status markup, and at most 900 weighted
characters (CJK/wide characters count twice). Missing/unknown markup, cold-archive
details, rich/authored content and long units fall back unchanged. The helper
captures existing output once and adds only the `q5-short-context` class.

Print CSS keeps that answer together. The Word filter independently rechecks
AST length/structure, then applies existing keep-with-next paragraph styles to
the policy, limitation introduction and first bullet, never the final bullet.
Pandoc discards paragraph data attributes, so semantic eligibility remains the
Jinja helper's responsibility; its exact output and conservative fallbacks are
checked separately. No words, quantities, question mappings, font sizes, style
definitions, translations or reference DOCX are rewritten.

Pinned PDF/Pandoc probes cover print/screen, width boundaries, non-Q5 contexts,
missing hints and long/complex ASTs. Actual Word XML must differ only in declared
paragraph style identifiers. Frozen-Q5 comparisons retain every existing fixture
answer with both autoescape settings. Prior Q13/Q11 style hash gates are composed
with an exact reviewed Q5 delta, not replaced by relaxed checks.

Native bilingual PDF/DOCX and LibreOffice previews remain a separate acceptance
gate. Long/complex fallbacks cannot be judged from unchanged total page count.
This is a short-lived `fix/q5-context-pagination` experiment derived from the
previous reviewed branch; the Chinese repo pins its exact English source. No
upstream merge, production upload, release tag or full-DMP acceptance is implied.

## Native outcome: partial success, not visual acceptance

Ten synthetic cases in both languages were compared against 0.3.33: 120 native
outputs before/after, with 40 LibreOffice Word previews. Body content is retained
and all document page counts are unchanged. Four separations improve: Chinese
metadata-private PDF/Word, Chinese metadata-private-text PDF, and English
metadata-complete PDF. Chinese metadata-partial Word remains split across pages
3 and 4 despite the correct keep-with-next styles. Four local diagnostic copies
with direct keep-next/keep-lines changes also remain split; they are not native
template outputs and were not adopted as a fix.

The native checker exits nonzero for that remaining separation. Build/engine CI
success is not a substitute for this failed visual gate. Evidence is archived
in the Chinese repository under `reviews/2026-09-17-storage-context-pagination`.
