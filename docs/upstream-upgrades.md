# Upstream upgrade policy

Review update (2026-09-11): the procedure below describes the initial small-patch
experiment. For substantial sentence/layout customization, use the selective
integration and provenance recommendations in the
[pipeline reassessment](pipeline-reassessment-2026-09.md). In particular, do not
automatically replace customized Word styles or advance the upstream baseline
after selectively importing only some changes.

## Repository model

- `origin` is the project repository:
  `https://github.com/ThreeMonth03/science-europe-template.git`.
- `upstream` is the official template:
  `https://github.com/ds-wizard/science-europe-template.git`.
- [`.upstream/base.json`](../.upstream/base.json) pins the exact official tag
  and commit from which the local work was derived.
- Local changes stay in small commits by concern: completeness macro, one
  question family, layout, contract/tests. An upstream sync and a local feature
  must never share the same commit.

The pinned tag, not the moving `upstream/main`, is the reproducible source
baseline. Keep upstream Git history; do not replace it with copied files or a
squashed import.

## Why upgrades require classification

Official releases have changed several independent layers:

| Change class | Examples | Required action |
| --- | --- | --- |
| Runtime contract | `template.json`, metamodel version, format steps | Select a compatible DSW/TDK runtime and validate every output format. |
| KM binding | `src/uuids.j2`, allowed KM versions | Re-audit every affected fact binding; UUID drift can silently remove prose. |
| Semantic Jinja | `src/questions/*.html.j2`, macros | Review branch meaning, especially empty versus explicit No. Re-run contract fixtures. |
| HTML/PDF layout | entry points and CSS | Visually compare page breaks, lists, tables, fonts, and gap callouts. |
| Word layout | `src/word/reference.docx` | Treat as a binary replacement: select the upstream file, then reapply and visually verify local styles. It cannot be safely line-merged. |

This is why a document-template version bump may cause much more movement than
its changelog suggests. A metamodel-only release can still alter value shapes,
and a small Jinja fix can touch many translated strings.

## Upgrade procedure

1. Fetch without changing the working branch:

   ```bash
   git fetch --no-tags upstream '+refs/heads/main:refs/remotes/upstream/main' 'refs/tags/*:refs/tags/upstream/*'
   python scripts/audit_upstream.py --target upstream/main
   ```

2. Choose a released tag, then create a review branch from the current custom
   branch. Classify its changes before selecting a merge strategy:

   ```bash
   git switch -c upgrade/upstream-vX.Y.Z
   ```

3. Review every `critical` and `high` group. Still-inherited files can be merged
   normally; independently rewritten questions and Word styles need selective
   semantic porting. Only after deciding a full merge is appropriate, use
   `git merge --no-commit --no-ff upstream/vX.Y.Z`. Never resolve UUID or question
   conflicts by choosing an entire side.

4. Update the Science Europe contract when a binding or output behaviour has
   changed. If the official standard changes, record that as a separate source
   revision; do not silently edit the 2021 contract.

5. Update `.upstream/base.json` only after a full integration has been reviewed.
   Selective porting must instead record accepted/rejected/pending changes in an
   upgrade ledger, retaining the original base. Record full commit hashes.

6. Run structural and contract checks:

   ```bash
   make check
   ```

7. Use the external render-regression tooling to render deliberately empty,
   explicit-No, partial, and complete projects in HTML, PDF, and DOCX. Compare
   both English and Traditional Chinese outputs using the stable requirement
   and fact IDs.

8. Merge the upgrade branch only after the visual review. Tag the local release
   separately from official namespaced tags: custom `v0.2.0` versus official
   `upstream/v1.31.0`. The manifest records their relationship. Never use
   `git push --tags`; push only an explicitly approved custom release tag.

## Automation boundary

The weekly GitHub workflow fetches upstream and classifies changed paths. It
fails when a change is detected so that the repository receives a visible
signal; it does not merge, rewrite Jinja, update UUIDs, or alter the Word
reference file automatically. Those steps require semantic and visual review.

The pilot already owns substantial Q1/Q15 prose and output styling. Treat those
as selectively maintained derivatives now, not as a promise of conflict-free
full merges. The 1.30.0 → 1.30.1 replay and its translation review queue are
recorded in the new Chinese repository's `docs/pilot-results.md`.
