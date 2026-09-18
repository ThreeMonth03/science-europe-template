# Science Europe DMP — customized English template

Experimental derivative of the official DSW Science Europe template, with
explicit missing-answer handling and shared PDF/Word reading structure.
This is not an officially endorsed Science Europe template or a completed DMP.

The template renders questionnaire replies; no runtime LLM invents missing answers.
Review the complete document and resolve missing information before using it.
PDF/Word pagination and Markdown-table support depend on the target renderer.

Version 0.3.38 adds an experimental submission-preview profile alongside internal
review outputs. Only the documented Q3/Q5/Q11, funding-overview and mixed quality
notices are optional in this first pilot. Other notices/placeholders remain.
This is NOT an approved, comprehensive or ready-to-submit output. Selecting a
profile does not complete answers or approve the DMP. Existing format UUIDs are
retained; the new submission formats share the same questionnaire logic.

Version 0.3.39 adds a bounded Word-only Q11 reading unit: a short dataset name
becomes a bold lead joined to its short fixed preservation summary. Question
headings and link anchors are retained. Long, missing or authored summaries
keep their existing structure. PDF and the scope of optional notices do not change.

Build reviewed bilingual packages through the companion Chinese repository.
The bare upstream packaging command does not prepare the reviewed bilingual fonts
and Word reference styles. Compatibility and release status must be checked
before installing any experimental package.

Source and review records: https://github.com/ThreeMonth03/science-europe-template

Bilingual builds: https://github.com/ThreeMonth03/science-europe-template-zhtw

Code is distributed under Apache-2.0. Upstream contributor attribution and
bundled font licences are retained in the source and package assets.
