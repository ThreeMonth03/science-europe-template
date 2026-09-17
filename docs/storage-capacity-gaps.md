# Q3 storage capacity: 0.3.32 experiment

The only runtime source change is Q3. A selected capacity follow-up must not
disappear just because metadata or file conventions already have answers.
Under `storageConvExploreAUuid` → `storageSpaceSpecifyAUuid`, a missing, empty
or whitespace-only amount now produces one scoped `storage-capacity` prompt.
Zero and other nonblank strings are retained, not cast, rounded or validated
as numeric values by the template. The quantity is escaped as text; imported
markup must not become document structure. The English estimate gains the
missing “be”; the Chinese sentence is maintained through the translation tree.

The prompt reuses `reading-gap`, so neither PDF nor Word merges it into the
surrounding policy paragraph. CSS, Word Lua, fonts and reference styles do not
change. Free-text answers keep their paragraphs and case-sensitive filenames.

The public Common KM 2.7.0 binding is project-wide: processing chapter
`10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5`, storage parent
`bc5e3dbf-2923-4025-a49a-f204b01d4018`, capacity choice
`38ebf5d0-f7a3-4cf5-93eb-6ee3143c8a69`, quantity
`974f3ad3-90b3-4e00-b751-8c5a5629b2cf`. It includes all data,
software and temporary storage, not one dataset or an inferred total.

`storage_gap_contract.py` projects only the owned capacity block from frozen
0.3.31 and compares the whole question: 866 checks per language, including
inactive/unsupported parents, stale values, No metadata, zero, whitespace and
HTML-looking input. Native fixtures separately cover missing, whitespace with
other answers, zero, 2048, empty and negative controls. Adapter tests are not
native-format or full Science Europe acceptance.

Both repositories use the short-lived `fix/q3-storage-gaps` branch; Chinese
locks the exact English commit. No permanent language-logic fork is added.
Upstream upgrades must revisit this question's UUIDs, parent conditions and
capacity units, then rerun branch, translation and native PDF/Word checks.
Do not advance the upstream baseline or declare all metadata/storage details
complete because this one follow-up is fixed. Other omitted Q3 follow-ups,
especially metadata access explanations, remain a separate audit.
