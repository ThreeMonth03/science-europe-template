# Full-KM followup recovery — bounded prototype

Status: experimental overlay of the exact `8c624359fcbc59ff5b364feba1fadab54a2090bf`
(`0.3.45`) source. Production `src/`, metadata and historical byte gates are
unchanged. This is not a released `0.3.46` template.

| Authored answer | Output | Scope |
| --- | --- | --- |
| Agreed project file naming conventions | Q3 / SE-2a | Separate from existing storage-filesystem conventions |
| Publication schedule for newly created reference data | Q10 / SE-5a | Project level, not every produced dataset |
| Maintenance of newly created reference data | Q11 / SE-5b | Project level, not every produced dataset |

These are three previously unconnected paths, not evidence of complete coverage
of the full KM or complete Science Europe compliance. The public English and
Chinese KM 2.7.0 event histories independently verify every ancestor edge.

The shared helper checks compiled KM membership, chapter/question/answer edges,
question types and all selected parent options. A stale answer under an inactive
branch or a filtered-out question is not output and is not a missing-answer
notice. An active blank text answer generates a review-only notice; submission
omits it and its label. Original Markdown, case, zero values and punctuation are
preserved. No runtime LLM or answer translation is involved.

One CSS addition is included: Q10's directly owned identifier list keeps the
value inline with `ARK:`, `DOI:`, etc. The old generic `li > strong:first-child`
rule matches even with preceding text, forcing the value onto another line and
potentially another page. The new fully scoped selector excludes authored lists.
No global strong/list rule, font, conversion step or Word asset changes.

## Run

```bash
python -m unittest discover -s tests -p test_full_km_followup_prototype.py -v
```

The paired Chinese repo's `experiments/full-km-followups/followup_build.py`
applies this source overlay before expansion and normal translation-tree merge.
It does not patch translated Jinja. It preserves all 767 reviewed translation
occurrences and adds six. Unique prototype template IDs prevent confusion with
the still-locked production packages.

## Integration boundary

Work branch: `fix/full-km-followups-prototype` in both repos. This is a temporary
change branch, not a permanent language/profile fork. Before production use:

1. Freeze the bilingual prototype and its PDF/Word evidence.
2. Integrate the owned source delta in English, with an exact new historical
   projection layer. Keep all old gates intact.
3. Commit the six added Chinese units; pin the exact integrated English commit
   and paired package version in `pipeline.yml`.
4. Rebuild clean candidate ZIPs, rerun all CI/native checks, and review actual
   Word pagination separately from LibreOffice previews.

Private project snapshots and native outputs stay outside both repositories.
Only synthetic fixtures/checks and the reviewed template changes belong here.
