# Integrated empty-section print spacing (0.3.48)

The exact print CSS from English prototype
`c875c950353fae1e36fc4df547e856249f9a7b72` is now in `src/layout.css`.
No Jinja, language, font size, line height, Word assets or format steps change.
Only wholly empty, exactly shaped owned sections get tighter print margins.
The conservative shared empty-question classifier is unchanged; all 15 questions
and every authored answer remain. Review is still the default.

`scripts/empty_section_spacing_contract.py` compares every source/asset byte and
all metadata with the exact 0.3.47 baseline plus the immutable approved CSS.
Only after this proof can old tests receive an exact historical 0.3.47 view.
Actual current-source Jinja checks and pinned public-renderer selector/geometry
checks are separate; old regression projections are not new-version acceptance.

Chinese is rebuilt through the existing translator with an exact English commit
lock and the same 0.3.48 version. Its 775 translation pairs should stay identical.
The independent prototype package IDs are not reused as production identities.
Both repos use short-lived `fix/empty-section-integration`, not permanent output-
profile branches. Push the locked English commit before the paired Chinese branch
when a remote update is requested; do not rewrite a released version or archive.

The preceding prototype passed 28 bilingual native comparisons (including empty,
partial and long answers). English empty submission PDF was 3 to 2 pages, and
English long submission PDF 7 to 6; review PDF and Word previews were unchanged.
Rebuilt integrated packages must reproduce those results before this integration
is considered locally verified. Evidence lives in the paired Chinese repo's
`reviews/2026-09-23-empty-section-integration`; this document is not a claim that
the rebuilt packages, target DSW server or Microsoft Word have been accepted.

Next prose/punctuation work is a separate patch; upstream upgrades still use
`upgrade/*` with knowledge-model, translation and native-output checks.
