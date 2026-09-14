# Preservation context flow (0.3.12 experiment)

Q11 previously placed data stage / related paper and publication / retention
arrangements in separate `dataset-policy` wrappers. Even short consecutive
template-owned sentences therefore became separate PDF and Word paragraphs.

The dataset context partial now lives inside Q11's existing preservation-summary
wrapper, without its own nested policy. The existing CSS and Word Lua join only
consecutive direct paragraphs. An authored `answer-detail`, a `reading-gap`, or
another block interrupts the run. No new global paragraph-flattening rule is added.

This is a structural change, not a rewrite: descriptions, related-paper values,
publication decisions, reasons, retention facts, negative answers, missing states
and their order remain unchanged. A dataset stage is still only context; it must
not be inferred to establish publication or preservation. Unanswered publication
decisions remain explicit even when a stage or retention answer exists.

Repository contact answers / references, project-wide cold storage and question
titles are unchanged. CSS, Lua, reference DOCX, fixtures, KM bindings and the
official 1.30.1 baseline are unchanged. The companion Chinese repository must lock
the exact English commit and regenerate through its existing reviewed translation
pipeline. No independently edited Chinese Jinja branch is introduced.

Upgrade boundary: Q11 and `preservation-dataset.html.j2` form one owned structural
unit. If upstream relocates either, review both plus the CSS/Lua policy semantics;
a conflict-free Git merge alone is not evidence of equivalent output. Retain
synthetic complete/partial answers, unchanged authored paragraph checks, and actual
PDF/DOCX comparison. This feature branch is an experiment, not a release branch
or a production deployment. See the companion review for measured results.
