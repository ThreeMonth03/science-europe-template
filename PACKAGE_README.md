# Science Europe DMP — customized English template

Experimental derivative of the official DSW Science Europe template, with
explicit missing-answer handling and shared PDF/Word reading structure.
This is not an officially endorsed Science Europe template or a completed DMP.

The template renders questionnaire replies; no runtime LLM invents missing answers.
Review the complete document and resolve missing information before using it.
PDF/Word pagination and Markdown-table support depend on the target renderer.

Choose the HTML, PDF or Word format labeled **Internal review** while preparing
the plan. These outputs show template-generated missing-answer and review notices.
Use the formats labeled **Submission preview (pilot)** to omit those internal
notices. Both profiles share the same questionnaire logic and retain filled answers
from applicable questionnaire branches; inactive follow-up answers are not included.

Submission previews retain all fifteen question headings, with compact spacing
for unanswered questions. Unnamed records with presentable content retain neutral
labels based on their original list positions. The preview does not fill missing
answers, correct irrelevant free-text answers or approve the DMP. Review the
content for completeness and accuracy before submission.

The profile names retain their experimental labels. Neither selecting a profile
nor successfully generating a document guarantees funder approval or compatibility
with every PDF/Word renderer. Version history and bounded layout changes are
documented in the source repository, rather than in this package description.

Build reviewed bilingual packages through the companion Chinese repository.
The bare upstream packaging command does not prepare the reviewed bilingual fonts
and Word reference styles. Compatibility and release status must be checked
before installing any experimental package.

Source and review records: https://github.com/ThreeMonth03/science-europe-template

Bilingual builds: https://github.com/ThreeMonth03/science-europe-template-zhtw

Code is distributed under Apache-2.0. Upstream contributor attribution and
bundled font licences are retained in the source and package assets.
