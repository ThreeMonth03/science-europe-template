# Upstream upgrade policy

## Provenance

`origin` is the customised template repository. `upstream` is
`https://github.com/ds-wizard/science-europe-template.git`.
[.upstream/base.json](../.upstream/base.json) pins the original released template
and full commit. Keep upstream history and attribution; the customised template
is not an official upstream release.

Substantial question wording, paragraph structure and Word layout are locally
maintained. An upstream update is therefore a reviewed integration, not an
automatic replacement of `src/`.

## Review changes by responsibility

| Change | Required review |
| --- | --- |
| Runtime metadata and format steps | Check DSW/TDK compatibility and every supported output format. |
| Knowledge-model UUIDs or reply shapes | Recheck affected answer bindings, missing values and explicit No. |
| Jinja semantics or fixed English wording | Preserve authored facts, then update/review matching PO keys. |
| PDF CSS and fonts | Compare actual English and Chinese pages. |
| Word reference, Lua or XML processing | Review binary/style changes and render DOCX; do not blindly replace customised assets. |

The standard topic map in `requirements/science-europe-2021.json` and preservation
binding notes remain references, not universal coverage certificates.

## Workflow

1. Fetch upstream without changing the working branch:

   ```sh
   git fetch --no-tags upstream '+refs/heads/main:refs/remotes/upstream/main' 'refs/tags/*:refs/tags/upstream/*'
   python scripts/audit_upstream.py --target upstream/main
   ```

2. Choose a released ref and use a short-lived `codex/` review branch. Separate
   upstream integration from new custom features. Classify conflicts before
   choosing a merge or selective semantic port.
3. Review UUIDs, conditions and authored-answer handling explicitly. Never resolve
   question conflicts by selecting an entire side without reviewing meaning.
4. Advance `.upstream/base.json` only after full integration. For selected fixes,
   retain the original base and record the upstream commit and selected paths in
   the integration commit.
5. Run current tests, update and review the Chinese PO, and compare native
   PDF/Word output with identical answers before publishing.
6. Give published outputs new immutable versions, pin the exact English/Tool
   commits in the Chinese pipeline, and keep the previous installation available
   for rollback. Push only explicitly selected release tags, never all tags.

The existing upstream watcher reports change risk. It does not merge, update
bindings, replace Word styles, change translations or deploy a template.
