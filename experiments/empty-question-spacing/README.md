# Empty submission question spacing

User-approved policy: retain the original questions in place, reduce empty space,
and do not introduce missing-answer notices into submission documents. This is a
non-release overlay on the sealed Q1 reuse-summary prototype, not a production edit.

The shared `content.html.j2` wraps each of the 15 includes with one classifier.
It adds a class only when the rendered answer is exactly whitespace, or the known
empty Q5 workspace/gap skeleton. It does not use stripped text to decide emptiness:
zero, images, tables, empty authored blocks and unknown markup are left alone.
No question, heading, answer or translation is removed or reworded. The class only
has scoped spacing rules at the direct question level. Review/default/unknown
profiles keep their old structure and layout.

Word submission gains a final Lua marker filter and a small XML wrapper. The wrapper
first runs the unchanged short-table processor. It then removes only generated
empty-heading markers and adds direct `keepNext=0`, `spacing before=80/after=0` to
the single original Heading3 paragraph. The heading style, outline level, all text
and bookmarks remain intact. Filled headings retain their keep-with-next behavior;
fonts and reference.docx are not changed. Unexpected XML serialization fails rather
than rewriting an arbitrary paragraph. Authored text resembling a marker is escaped
by Pandoc and must remain literal.

## Reproduction

Run `python -m unittest discover -s tests -p test_empty_question_spacing_prototype.py -v`.
The companion Chinese builder tests both actual language packages with 480 cases
each; all 775 existing sentence/translation pairs must remain identical.

For the actual prepared package, run:

```bash
python experiments/empty-question-spacing/engine.py \
  --source-dir ../science-europe-template-zhtw/outputs/empty-question-spacing-08/en \
  --output /tmp/empty-spacing-new-engine.json
```

Use `translated` instead of `en` for Chinese. Each run checks 25 pinned Pandoc
cases, including all 15 question IDs, filled/zero/unknown controls, authored
lookalikes, the Q5 skeleton, and malformed XML rejection. Existing engine outputs
must not be overwritten. Native/private A/B results are documented in the Chinese
repo under `reviews/2026-09-22-empty-question-spacing`.

Builds 04/05 are rejected for escaped Word properties; 06/07 fix that but regress
PDF pagination after authored tables. The final recipe retains empty answer boxes
and checks autoescaping explicitly. Their failed artifacts remain sealed; never
use earlier reduced page counts as acceptance evidence.

## Version boundary

Short-lived branch: `fix/empty-question-spacing` in both repos. The baseline ZIP
hashes and exact prior recipes, not branch names, determine the EN/ZH pair. Output
packages have new `science-europe-empty-question-prototype[-zhtw]` IDs and test
version 0.3.47. Production source, template.json and the Chinese production lock
remain 0.3.46. After acceptance, consolidate this and the Q1 prototype in one
English integration and pin its commit in Chinese; do not create permanent profile
branches or accumulate runtime overlays. Old evidence stays immutable.

This improves spacing, not completeness. An empty DMP remains empty. No claim is
made of Science Europe completeness, Microsoft Word acceptance or online deployment.
