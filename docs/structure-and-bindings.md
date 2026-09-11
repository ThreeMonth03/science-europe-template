# 0.2.2: bounded structure and binding experiment

This remains a derivative of upstream 1.30.1 at the unchanged `.upstream/base.json`
baseline. Changes live on `feat/structure-and-bindings`, based on the previous
answer-retention experiment; no release or live deployment is implied.

- Q3: remove unused lookups of an undefined W3C binding. The actual W3C PROV
  question is retained separately.
- Q7/Q13: repair misspelled contract-basis and institutional PID-assigner bindings.
- Q8: remove obsolete nested embargo lookups; preserve the current chapter-level
  embargo mapping. Use valid block containers for Markdown and close the list intro.
- Q9: record each project once; independently retain approval status and case
  number even without a project name. Render explicit No as a questionnaire
  statement, not an independent ethical/legal assessment. Translate status sentences.
- Q11: close the dataset intro and remove stray list breaks. Repository costs and
  preparation budget no longer depend on the presence of a dataset list.
- Q13: remove the obsolete PID-specification question absent from compiled Common
  KM 2.7.0. Do not remap it to an unrelated DOI field. Replace paragraphs directly
  inside a list with a normal block; repair the non-published branch's closing tag.

Legacy `representative` and `retention-partial` fixture bytes remain unchanged.
New `structured` cases supply `10 years` / `10 年` and select budgeted repository
charges. A number-only retention value is NOT silently interpreted as years.
The old prepaid-plus-no-charges combination receives a review prompt, not a
definitive contradiction verdict: another party may have prepaid the service.

Static KM presence checks and these synthetic cases do not prove all paths are
reachable, all replies retained, or all Science Europe requirements answered.
The package's inherited allowedPackages range is not a compatibility claim;
only Common EN/ZH KM 2.7.0 is exercised. Other KMs need their own validation.

The Markdown pipe-table limitation belongs to the document worker, not a locale
branch. The Chinese repository holds a separately pinned, local-only worker
experiment; it must never be disguised as a template-only fix or released via
the ordinary candidate staging command.

For upgrades, keep the upstream baseline pristine, review upstream changes against
the owned risk paths, and rerun both binding and rendered-output tests. Lock the
Chinese pipeline to the exact reviewed English commit. Branch names identify work;
package versions and commit/image digests identify reproducible outputs.
