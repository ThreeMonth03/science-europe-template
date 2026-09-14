# 0.3.10: distribution identity and bounded Q11 pagination

The short `feat/repository-reading` branch follows 0.3.9. Upstream baseline,
knowledge-model bindings and free-answer translation logic remain unchanged.

Q11 uses the original distribution list index, as Q10 and Q13 do. Inline labels
appear only for multiple distributions. A missing repository choice retains its
row and number with an explicit gap; an unsupported choice is a review issue,
not a missing answer. The lead describes destinations without asserting every
respondent has supplied one. Long-term-support states remain distribution-local.

Only inline-only lists with at most three items and at most 900 normalized
characters receive the `short-repository-list` keep hint. Arbitrary contact
arrangements and block markup cannot receive it. This is a conservative content
bound, not a guarantee about all fonts or page sizes. PDF keeps that wrapper,
including its lead, together; it does not keep the dataset or question together.

Word independently checks the actual Pandoc AST and Unicode length. It clears
the generic list keep chain locally before applying Q11-specific paragraph
styles. All short items keep their own lines together; only non-final items keep
with the next item. The final item explicitly releases the next dataset. Body
font size, line spacing and all prior styles remain unchanged.

New reachable synthetic fixtures cover a missing middle repository and sixty
authored contact paragraphs. Adapter tests additionally cover unsupported choices,
inactive parents, long names, block markup, and lists with more than three items.
Actual bilingual PDF/DOCX evidence and limited visual review live in the Chinese
repository. Neither Git/CI success nor this pagination hint establishes full
Science Europe coverage, Microsoft Word acceptance or runtime deployment approval.
