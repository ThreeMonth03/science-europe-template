# 0.3.37: concise missing metadata follow-ups

Experimental branch: `fix/metadata-gap-prose`, based on the reviewed 0.3.36
commit `950db54d25bc4a519dc6125815a23fa802f25487`. This is not a release.

Only when metadata is openly available and both publication follow-ups are
absent (including whitespace-only values), render one warning paragraph:

> Information not provided: whether the metadata will include instructions for accessing the data; whether the metadata will be available in a form that can be harvested and indexed.

Both clauses retain their own `data-fact-id` and `data-status="missing"`.
No answer is invented. Single missing fields, explicit No, unknown choices,
private metadata reasons, dictionaries, storage capacity and authored text
keep their previous behavior. Existing Science Europe questions are unchanged.

The 0.3.36 seven-line CSS panel is retired. The shared Jinja paragraph works in
HTML, PDF and Word without another CSS/Lua/font/reference-document patch.
The previous panel probe remains explicitly historical, not current acceptance.

## Translation boundary

Two captured Jinja fragments own the fact spans; three translation units own
the two clause texts and the enclosing sentence. Translators can choose the
sentence's punctuation/order using named placeholders without copying HTML
attributes. A trial with bare inline spans failed the existing structure audit:
the converter flattened the spans when the entire sentence was translated.
The final approach keeps the converter pinned and leaves its source untouched.

## Gates

- Frozen 0.3.36 complete-Q3 comparison: 1,726 scenarios including autoescape,
  whitespace, unknown/No, stale descendants and authored blocks.
- Retain cumulative Q3 follow-up/capacity and unrelated Q2/Q5/Q11 contracts.
- `probe_metadata_gap_prose.py`: 33 branches, 70 print/screen/page-end engine
  checks; actual DOCX pair-to-paragraph projection with unchanged other XML.
- Chinese repo: exact 744 retained translation pairs plus three reviewed units;
  only Q3 translation files may migrate; full source delta limited to Q3/CSS.

Native DSW and LibreOffice previews are separate acceptance steps. Passing
these probes does not establish Microsoft Word or whole-DMP acceptance.

## Versioning

Keep changes on this short-lived topic branch. The Chinese repo pins an exact
English commit, not a moving branch; its translation delta names the prior
Chinese commit. Future upgrades compare frozen source/behavior contracts and
the three translation units instead of merging independently edited Chinese
Jinja. Do not overwrite a published template version or rewrite old reviews.
