# Related-paper reference (0.3.13 experiment)

Q11 retains the contiguous data-stage / publication / retention prose from
0.3.12, but moves the related-paper scalar to a separate reference paragraph
after that dataset's preservation summary and before its repositories. A long
URL should not interrupt policy sentences. No generic global paragraph rewrite
or font-size reduction is used.

The field may contain a citation, DOI, URL or other plain text. Preserve the exact
scalar, escape it as text, and do not parse it as Markdown. The reference label
and value share a paragraph. Remove only the template's extra terminal period;
authored punctuation, case, percent escapes, query strings and fragments remain.
Only a whole whitespace-free lowercase HTTP(S) value with a nonempty authority,
without credentials / quotes / angle brackets / backslashes, is linked. This is
conservative eligibility, not a general URL validator. Do not extract or repair
embedded URLs. Other values remain literal text.

Capture the translatable label separately from conditional value markup. The
first combined prototype lost span wrappers when a reviewed plain-text label was
applied by the translation pipeline; the bilingual structure audit rejected it.
The source fix isolates the label without changing its visible placement. Keep
that boundary on upgrades rather than repairing generated Chinese or weakening
the audit.

The paper follows its own data-stage branch. It is not gated by the independent
publication decision, and a stale paper under another stage must not leak.
Missing / blank values retain the prior behavior: no empty reference row, while
stage and preservation answers remain. No new completeness claim is introduced.
Duplicate dataset names or identical independently supplied references must not
cause merging, reassignment or deduplication.

Ownership / upgrade unit: Q11, preservation-dataset.html.j2 and the new
preservation-paper.html.j2. The only CSS addition scopes wrapping to the paper
reference; Lua and Word reference styles remain unchanged. Recheck full text,
field ownership, standalone paragraphs and actual PDF / DOCX hyperlink targets
when either the upstream template or renderer changes. Git merge success alone
does not establish output equivalence. Official baseline remains 1.30.1, and the
Chinese repo still locks an exact English commit and regenerates through its
reviewed phrase tree. This is not a release or production deployment.

The new paper-references fixture contains a long unbroken URL with query / fragment,
a plain citation containing literal angle brackets and terminal punctuation,
duplicate dataset names and a third blank paper field. Existing preservation
fixtures remain byte-identical. Native acceptance evidence belongs in the
companion repository; Microsoft Word and stock Markdown-table limits remain.
