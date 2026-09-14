# Reading polish (0.3.5)

Short branch `feat/reading-polish` follows `feat/format-volume-reading`.
The official 1.30.1 baseline, KM and UUID bindings do not change.

- Q2 missing fields keep their individual fact IDs but share one lead and one
  sentence, using locale-specific list punctuation from the existing pipeline.
- Short numeric quantities use a non-breaking space and a scoped PDF rule.
  Long values are not marked unbreakable; authored prose is not normalized.
- Q10 only simple national/institutional/project repositories and CC0/CC-BY
  licence paragraphs are marked as joinable. Access decisions can join them.
  Missing fields, distribution labels, restricted terms, complex repositories
  and free answers remain separate. The Word filter handles only those marked
  wrappers; this does not authorize flattening every nested div.
- `PACKAGE_README.md` is the stable package description used by the bilingual
  build; repository navigation stays in README.md. The bilingual builder dates
  packages by their last English package-input commit, not unrelated doc commits.

Q2, Q10, macros, PDF CSS and Word Lua are owned upgrade-review surfaces. Compare
the same answers before/after and inspect both PDF and DOCX; conflict-free merges
do not establish semantic or visual compatibility. This remains experimental.
