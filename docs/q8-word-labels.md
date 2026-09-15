# 0.3.22 Q8 Word label continuity

Short-lived branch `fix/q8-word-labels`, from 0.3.21 `f7520f3`.
Official upstream remains 1.30.1 / `22d60aae4b63ee677477ac0c73097807284aaf9f`.

The 0.3.21 Chinese Word preview of `personal-transfer-complete` left Q8's first
dataset name on page 4 and its permission on page 5. The generic BulletList rule
keeps the end of an item with the next item, but not the name with its own text.

Only `src/word/pilot.lua` changes presentation. In Q8's direct answer lists, a
plain name Div and one short permission paragraph receive the existing
`Pilot List Lead` style on the name. A Plain name becomes one Para with identical
inlines: the DOCX writer ignores the custom style on Plain. Text, paragraph
count, other attributes and list numbering are preserved. No prose is merged or added.
Names are bounded to 80 display units, permissions to 320 (CJK counts double),
and lists to 32 entries. Each qualifying pair is considered independently.
Long, attributed, nested or complex content falls back unchanged. Other questions,
PDF CSS, Word reference styles, Jinja, bindings and translations are unchanged.

`probe_q8_word.py` checks 26 cases with the pinned Pandoc image, both AST and actual
DOCX output. Its AST oracle permits only the exact style attribute on a previously
unstyled name Div and Plain-to-Para with identical inlines. The DOCX oracle allows
only Compact-to-PilotListLead, preserving all other paragraph XML. Tests include
English/Chinese boundaries, many entries, missing text, long paragraphs, tables,
nested lists, images, links, attributes and unrelated question scopes.

`generate_q8_word_fixtures.py` adds 30-paragraph custom restrictions and eight
reference entries. Both KMs must validate the reply paths before native export.
Compare those cases to fresh native 0.3.21 baselines, and the original failure,
empty/negative and complete controls to their preserved 0.3.21 outputs.
The Chinese repository records unchanged HTML/PDF, Word XML allowing only Q8
name styles, actual name/permission page locations and the original failure.
The first 0.3.22 native attempt caught the ignored Plain style despite its passing
AST-only probe. Preserve that failed output separately; the new DOCX probe must
not be replaced by an AST-only test.

The Chinese pipeline locks this English commit; all 731 translation files must
remain byte-identical. Future upstream upgrades must re-run the AST and native
checks even when Word Lua merges without a text conflict. Do not edit generated
Chinese Jinja or create a permanent language-specific layout branch.

This does not establish whole-document or Microsoft Word acceptance. Short
budget prompt wrapping, general white space and long/complex Q8 reading remain
separate work; no main merge, tag, release or production deployment is implied.
