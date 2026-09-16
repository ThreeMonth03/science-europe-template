# Q11 archival-extension criteria, 0.3.29

The three fixed multichoice labels now form one short paragraph instead of a
lead and up to three one-line bullets. Each selected label retains its own
`data-fact-id` and complete status. The paragraph names the criteria, not a
claim that the extension has already been assessed or approved.

Only `src/post-project-archive.html.j2` changes in the runtime source. No
authored answers, CSS, Lua, font or Word reference are rewritten. Missing
criteria retain their prompt; unsupported selections get a needs-review prompt,
with recognized selections still visible. No/missing parent answers suppress
stale descendants. Unknown UUIDs are adapter-only tests, not native KM fixtures.

The existing translation pipeline captures each translated span and localizes
the join separator. Traditional Chinese therefore uses `、` and one final `。`,
not an English comma or a period per label. There is no independent Chinese
Jinja implementation and no runtime LLM.

The frozen 0.3.28 fragment and an independent DOM transformation check all eight
subsets, reversed/duplicate inputs, unsupported/malformed inputs and parent
guards, plus authored block controls, with autoescape both off and on. The
whole Q11 DOM outside the allowed change must be identical. Native PDF/DOCX
and LibreOffice preview evidence is maintained in the Chinese repository.

Use short-lived `fix/archive-basis-reading` branches in both repositories; the
Chinese `pipeline.yml` locks the full English commit and an independent Chinese
version. Upstream remains 1.30.1. Future upstream Q11 changes must be ported by
intent and checked against these contracts; a conflict-free merge alone does
not establish correct bilingual output. This is an experiment, not a release
or full Science Europe/Microsoft Word acceptance.
