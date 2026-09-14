# Identifier reading units (0.3.14 experiment)

Q13 had four Word paragraphs per fully answered distribution: its number, the
repository type, the identifier decision, and the assignment/resolution prose.
Group these as one heading and one policy paragraph. Preserve the existing
wording, question title, field conditions, distribution ordering and identity.
No font, line-spacing, margin, reference.docx, table or author-answer change.

The new `identifier-heading` wraps only the existing template-owned labels.
PDF CSS displays its paragraphs inline; Word Lua combines at most two all-Strong
label paragraphs, at most 240 Unicode characters. Existing Pilot Label wrappers
are normalized locally. Unexpected blocks, long labels or free text must not be
flattened. The resulting heading retains the existing Pilot Label style and
keep-with-next; it does not keep an entire question or dataset on one page.

Move the affirmative identifier paragraph inside the existing
`identifier-arrangement dataset-policy` wrapper. Its assignment and resolution
sentences already use this shared PDF/Word joining mechanism. Explicit negative
and unknown top-level decisions stay outside it, as do authored re-use answers.
Do not let stale affirmative child answers escape an inactive parent.

Translation still uses the existing pipeline. All 716 units are exact matches;
no new Chinese prose or separately maintained Chinese branch logic is introduced.
This pass reduces fragmentation, not all repetition in the wording. Empty or
unrecognized assignment/resolution children still lack their own visible gap
prompts: that pre-existing content limitation is NOT solved by this layout pass.
Unknown repository types also still lack a Q13-specific type prompt. Do not call
preserving previous output a completeness audit.

Upgrade/review unit: Q13 plus the dedicated CSS and Word Lua handler. Q13 is
already a critical overlap; Lua is high-risk. Official baseline stays at 1.30.1
(`22d60aae4b63ee677477ac0c73097807284aaf9f`). Both working repos use the short-lived
`feat/identifier-reading` branch, based on 0.3.13; Chinese pins the exact English
commit. No new permanent maintenance branch, merge, tag, release or deployment.

Native acceptance evidence belongs in the companion repository. Compare all
15 questions after restoring ONLY these two declared container edits; compare
the complete Word paragraph stream with only scoped consecutive Q13 joins,
all table cells, full body text in PDF/Word previews, and existing paper links.
Do not accept lower page counts if they hide content or orphan labels. Synthetic
LibreOffice previews do not substitute for Microsoft Word or whole-DMP review.
