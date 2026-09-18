# 0.3.42: bounded PDF resource rows

This experimental patch addresses a short many-budget row whose name and
purpose landed on different PDF pages in the 0.3.41 native fixture. It adds
only an inline `break-inside: avoid` hint to independently bounded rows in
ordinary 4–32-row resource tables. The entire table is never kept together.

The PDF-only helper accepts a small explicit fragment grammar, paragraph and
weighted-text limits, and short unbroken tokens in each column. Empty or
unknown markup is rejected. Missing-information paragraphs, including a zero
amount with missing currency, are eligible only within the same bounds.
Long/complex rows retain the prior pagination. Tables with the existing
expanded long-row presentation bypass the new helper completely. Tables of
up to three rows keep their existing whole-table rules.

HTML, Word, CSS, fonts, questions, authored text and translation units are
unchanged. The byte-exact source projection restores 0.3.41 before running
the earlier source gates; it does not move the historic baselines.

`probe_short_resource_rows.py` checks 120 grammar/escaping cases and 28 pinned
print/screen engine pairs, including field bounds, long controls and missing
facts. It compares each cell's entire text, requires selected rows to fit on
one page, and checks unchanged fallback geometry. These probes are not native
DSW or Microsoft Word acceptance; paired native evidence belongs in the
Chinese repository's review archive. No production deployment is implied.
