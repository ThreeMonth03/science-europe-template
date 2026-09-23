# Q3 renderer-neutral fixed policy prose (prototype only)

Production remains the paired 0.3.50, English source
`a2f97d9312b4ce811b92f5943944997638cc67b8`. The recipe changes one Q3 capture and
adds `src/metadata-prose.html.j2`; it changes no CSS, Lua, Word styles, font or
wording. It is not the rejected sentence-list or widened-CSS experiment.

The caller passes only the existing Q3 metadata-policy block. The helper admits
exactly 2–3 plain paragraphs with complete sentences. It preserves the dictionary
fact's attributes on a span, retains the original order and internal text, and
joins at the same boundary for HTML/PDF/Word. Every boundary must be a fullwidth
stop followed by a BMP Han opening; no new ASCII separator is inserted. Any other
boundary returns the entire original block byte-for-byte, including a three-part
run with just one mixed boundary. English and mixed-language runs are not merged.
This is deliberately not a general language detector.

The initial broader prototype merged English too, preserving its ASCII separators.
Native engine checks nevertheless found a 0.013055 pt coordinate change and changed
72-dpi pixels in an English control. The narrowed rule avoids that unnecessary
reshaping; unchanged cases must pass exact geometry and pixel checks, not an
increased tolerance. Initial failed evidence remains separate from the final run.

The whole block is returned unchanged when it contains a gap, an authored Div,
inline markup/entities, an unknown attribute, a duplicate dictionary fact,
incomplete text, or anything other than the permitted paragraph run. No authored
HTML is flattened or globally stripped. A single fixed paragraph also stays intact.
The existing stylesheet and Word filter already visually run these paragraphs
together: this makes their inter-paragraph separator explicit in the shared HTML,
not a new keep-together or pagination rule.

`probe.py` uses a separate parsed-DOM oracle, preserves all other whitespace/text,
and tests answer combinations, stale parents, unknown/missing choices, profiles,
autoescape, original markup and all public full-document fixtures. Mutation tests
reject fact/status, user text, punctuation and mixed-boundary separator changes.
Do not edit historical fixtures or old diagnostics to make this prototype pass.

The Chinese counterpart must run the locked existing expand/export/merge/sync
pipeline with 775 byte-identical translation files and an exact English recipe
commit. Both prototype IDs must stay separate from production. Actual packaged
engine checks and offline full-document comparison are required before integration;
LibreOffice previews are not Microsoft Word acceptance. No push/deployment here.
