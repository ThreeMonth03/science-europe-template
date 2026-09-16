# 0.3.25 short-budget PDF reading experiment

The PDF entry may add `pdf-short-budget` to an existing Q15 table. Every original
row, paragraph, punctuation mark, fact attribute and answer remains byte-identical.
HTML and Word do not enter this path. The question template itself is unchanged.

Only 1–3 rows qualify. At least one has the owned missing-budget prompt; every
title/purpose/budget/funding fragment must meet conservative visible-length,
paragraph-count, markup and raw-length bounds. Unknown markup, lists, links,
images, long purposes and many-row tables retain the original layout. Tables
already using the long-budget presentation also retain their previous behavior.
The bounds are hints, not a general HTML sanitizer or universal height guarantee.

The qualifying table uses 49/25/26 percent column widths, .25em vertical cell
padding and .2em paragraph bottom margins. Font size and line height stay fixed.
Frozen-native-HTML preflights rejected 40/29/31: it shortened the prompt but made
the English purpose column/table taller. Preflights are not native acceptance.

`probe_short_budget.py` checks 42 original-fragment/real-question cases per
language; the existing long-budget and empty-Q15 probes remain active. The
Chinese repository additionally checks all 731 translations and prepared source
hashes against frozen 0.3.24, and keeps native bilingual comparisons separately.

Both repositories use `fix/short-budget-reading`; the Chinese `pipeline.yml`
locks this English commit and tooling independently. This is an experimental
0.3.25 derivative, not an upstream upgrade, main merge, tag or release. Upstream
Q15 captures are still an upgrade-review boundary; rebase/cherry-pick alone is
not an acceptance check. Rerun fragment, translation, native PDF and Word tests.
