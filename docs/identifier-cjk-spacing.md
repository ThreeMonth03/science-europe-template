# 0.3.28: Chinese Q13 sentence boundaries

The fixed identifier policy already ends each Chinese sentence with `。`.
The PDF layer nevertheless inserts a CSS-generated Western space and the Word
filter independently inserts a Pandoc Space. Remove those generated separators
only inside `identifier-arrangement`; keep the numbered/type heading separator.

PDF uses the existing `zh-Hant` HTML language. Word has a character-boundary
guard (ideographic full stop followed by Han), because Pandoc does not retain
the HTML root in the block AST. Neither implementation removes existing text.
The Q13 source contains only fixed translatable policy sentences; it is byte-for-
byte unchanged. Its rendered adjacent paragraphs must have no literal whitespace
between them: otherwise the PDF still has a gap. The bilingual branch probe must
verify this assumption rather than globally stripping whitespace from answers.

English sentences, other policy groups, headings, free answers, font sizes and
line/paragraph spacing are outside this change. CSS and Lua are shared English
source, not an independent Chinese Jinja implementation. The translation tree
must remain identical and the Chinese repository pins the English commit.

`probe_identifier_spacing.py` reconstructs the exact frozen 0.3.27 CSS/Lua and
checks actual pinned WeasyPrint/Pandoc outputs, including retained Word run
formatting. Native DSW/LibreOffice before/after comparisons are separate gates;
neither gate establishes Microsoft Word or whole-document acceptance.
