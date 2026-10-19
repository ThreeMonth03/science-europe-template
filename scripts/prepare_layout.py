"""Prepare PDF fonts and Word styles in a disposable build directory."""

import argparse
import copy
import io
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor


def prepare_layout(template: Path, font: Path, language: str) -> None:
    target = template / "src/fonts/PilotTC.ttf"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(font, target)
    style = template / "src/layout.css"
    style.write_text(
        '@font-face { font-family: "Pilot CJK"; src: url("data:font/ttf;base64,'
        '{{ assets("src/fonts/PilotTC.ttf").data_base64 }}") format("truetype"); }\n'
        'html body { font-family: "DejaVu Sans", "Pilot CJK", sans-serif; }\n'
        + style.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    reference = template / "src/word/reference.docx"
    document = Document(reference)
    # A custom derivative must not retain the official Science Europe header logo.
    # Keep the upstream binary in Git for provenance; remove drawings in the build.
    for section in document.sections:
        for container in (section.header, section.first_page_header, section.even_page_header):
            for paragraph in container.paragraphs:
                paragraph.clear()
                properties = paragraph._element.find(qn("w:pPr"))
                if properties is not None:
                    for border in list(properties.findall(qn("w:pBdr"))):
                        properties.remove(border)
            for element in list(container._element.iter()):
                if element.tag in {qn("w:drawing"), qn("w:pict")}:
                    element.getparent().remove(element)
    for section in document.sections:
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.top_margin, section.bottom_margin = Mm(20), Mm(22)
        section.left_margin = section.right_margin = Mm(19)
    for item in document.styles:
        if item.type not in (1, 2):
            continue
        item.font.name = "Arial"
        item.font.color.rgb = RGBColor.from_string("222222")
        props = item.element.get_or_add_rPr()
        fonts = props.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            props.append(fonts)
        fonts.set(qn("w:eastAsia"), "Noto Sans CJK TC")
        for key in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(qn("w:" + key), None)
        for previous in list(props.findall(qn("w:lang"))):
            props.remove(previous)
        lang = OxmlElement("w:lang")
        # Western and East Asian runs have separate language attributes. Marking
        # Latin as Chinese allows word-internal breaks in mixed-language DOCX.
        lang.set(qn("w:val"), "en-GB")
        lang.set(qn("w:eastAsia"), "zh-TW")
        props.append(lang)
    # Links remain identifiable without colouring headings or ordinary lists.
    for name in ("Hyperlink", "FollowedHyperlink"):
        if name in document.styles:
            document.styles[name].font.color.rgb = RGBColor.from_string("185778")
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in document.styles:
            item = document.styles[name]
            item.font.size = Pt(10.5)
            # Use one minimum for both locales: an English document can contain
            # Chinese answers, and a Chinese document can contain Latin answers.
            # Taller CJK runs and equations may expand; never clip them with an
            # exact line height or multiply their already-tall font metrics.
            # Normal shares the body rule so Pandoc's first/table paragraphs
            # cannot silently use a different baseline from ordinary answers.
            item.paragraph_format.line_spacing = Pt(14.5)
            item.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
            item.paragraph_format.space_before = Pt(0)
            item.paragraph_format.space_after = Pt(2 if name == "Compact" else 4)
            item.paragraph_format.widow_control = True
    heading_leading = (25, 18.75, 14.5, 14, 13.5)
    for level, size in enumerate((20, 15, 11.5, 11, 10.5), 1):
        if f"Heading {level}" in document.styles:
            item = document.styles[f"Heading {level}"]
            item.font.size, item.font.bold = Pt(size), True
            item.font.italic = False
            # Minimum leading avoids the large automatic CJK reserve. A larger
            # gap before than after attaches the heading to its following body.
            item.paragraph_format.line_spacing = Pt(heading_leading[level - 1])
            item.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
            if level == 3:
                item.font.bold = True
                item.font.color.rgb = RGBColor.from_string("000000")
            item.paragraph_format.keep_with_next = True
            item.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            item.paragraph_format.keep_together = True
            item.paragraph_format.page_break_before = False
            item.paragraph_format.space_before = Pt(12 if level == 1 or level >= 4 else 14)
            item.paragraph_format.space_after = Pt(2 if level >= 4 else 3 if level == 3 else 5 if level == 2 else 6)
    # Source metadata is secondary text, not another body paragraph. A short
    # owned pair is one block so its final source line cannot become a page.
    provenance = document.styles.add_style("Pilot Provenance", WD_STYLE_TYPE.PARAGRAPH)
    provenance.base_style = document.styles["Body Text"]
    provenance.font.size = Pt(9)
    provenance.font.color.rgb = RGBColor.from_string("526169")
    provenance.paragraph_format.line_spacing = Pt(12)
    provenance.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    provenance.paragraph_format.space_before = Pt(0)
    provenance.paragraph_format.space_after = Pt(2)
    provenance.paragraph_format.keep_together = True
    provenance.paragraph_format.keep_with_next = False
    guidance = document.styles.add_style("Pilot Question Guidance", WD_STYLE_TYPE.PARAGRAPH)
    guidance.base_style = provenance
    guidance.font.size = Pt(10)
    guidance.paragraph_format.line_spacing = Pt(14)
    guidance.paragraph_format.space_after = Pt(4)
    guidance.paragraph_format.keep_with_next = True
    label = document.styles.add_style("Pilot Label", WD_STYLE_TYPE.PARAGRAPH)
    label.base_style = document.styles["Body Text"]
    label.paragraph_format.keep_with_next = True
    label.paragraph_format.space_before = Pt(4)
    label.paragraph_format.space_after = Pt(3)
    # Budget row labels share the other cells' first-line metrics, without the
    # extra separation intended for standalone labels. Retain their keep/after.
    table_label = document.styles.add_style("Pilot Budget Label", WD_STYLE_TYPE.PARAGRAPH)
    table_label.base_style = document.styles["Body Text"]
    table_label.paragraph_format.keep_with_next = True
    table_label.paragraph_format.space_before = Pt(0)
    table_label.paragraph_format.space_after = Pt(3)
    lead = document.styles.add_style("Pilot Lead", WD_STYLE_TYPE.PARAGRAPH)
    lead.base_style = document.styles["Body Text"]
    lead.paragraph_format.keep_with_next = True
    # A bounded Q14 summary may follow a kept name, but must not pull the next
    # person's record onto the same page. Long records retain Body Text.
    responsibility = document.styles.add_style("Pilot Responsibility Summary", WD_STYLE_TYPE.PARAGRAPH)
    responsibility.base_style = document.styles["Body Text"]
    responsibility.paragraph_format.keep_with_next = False
    responsibility.paragraph_format.keep_together = True
    responsibility.paragraph_format.left_indent = Mm(4)
    # Bounded fixed-duty bullets keep their original Compact list geometry.
    # Only nonterminal items keep-next; the last must release the next person.
    for name, keep_next in (("Pilot Responsibility Lead", True), ("Pilot Responsibility Item", False)):
        item = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        item.base_style = document.styles["Compact"]
        item.paragraph_format.keep_with_next = keep_next
        item.paragraph_format.keep_together = True
        item.paragraph_format.space_before = Pt(0)
        item.paragraph_format.space_after = Pt(0)
    # Each bounded frontmatter person is one Compact paragraph with line breaks.
    # Keep that person's lines, never the following person or the whole list.
    contributor = document.styles.add_style("Pilot Contributor Summary", WD_STYLE_TYPE.PARAGRAPH)
    contributor.base_style = document.styles["Compact"]
    contributor.paragraph_format.keep_with_next = False
    contributor.paragraph_format.keep_together = True
    list_lead = document.styles.add_style("Pilot List Lead", WD_STYLE_TYPE.PARAGRAPH)
    list_lead.base_style = document.styles["Compact"]
    list_lead.paragraph_format.keep_with_next = True
    # Q11-specific styles: do not alter free-answer or other list pagination.
    for name, keep_next in (("Pilot Repository Lead", True), ("Pilot Repository Item", False)):
        item = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        item.base_style = document.styles["Compact"]
        item.paragraph_format.keep_with_next = keep_next
        item.paragraph_format.keep_together = True
    # BEGIN bounded preservation label style
    preservation = document.styles.add_style("Pilot Preservation Summary", WD_STYLE_TYPE.PARAGRAPH)
    preservation.base_style = document.styles["Body Text"]
    preservation.paragraph_format.keep_with_next = False
    preservation.paragraph_format.keep_together = True
    # END bounded preservation label style
    # One ownership indent inside dataset records, preserving existing keep
    # semantics. Headings remain flush left; no authored text is rewritten.
    for source, name in (("Body Text", "Detail"), ("Pilot Label", "Label"),
                         ("Pilot Label", "Attribute"),
                         ("Pilot Lead", "Lead"), ("Pilot Provenance", "Provenance"),
                         ("Pilot Preservation Summary", "Summary")):
        item = document.styles.add_style("Pilot Dataset " + name, WD_STYLE_TYPE.PARAGRAPH)
        item.base_style = document.styles[source]
        item.paragraph_format.left_indent = Mm(4)
        if name == "Attribute":
            item.font.size = Pt(9.5)
        if name == "Summary":
            item.paragraph_format.first_line_indent = Mm(-4)
    # The final paragraph of a bounded record must not pull the next dataset.
    terminal = document.styles.add_style("Pilot Dataset Terminal", WD_STYLE_TYPE.PARAGRAPH)
    terminal.base_style = document.styles["Pilot Dataset Detail"]
    terminal.paragraph_format.keep_with_next = False
    terminal.paragraph_format.keep_together = True
    # Subordinate prose shares one 4 mm level. Inline record identities keep
    # their first line at the base margin; long paragraphs remain free to flow.
    for mode in ("Detail", "Record"):
        for source, suffix in (("Body Text", ""), ("Pilot Lead", " Lead"),
                               ("Pilot Label", " Label")):
            item = document.styles.add_style("Pilot Reading " + mode + suffix, WD_STYLE_TYPE.PARAGRAPH)
            item.base_style = document.styles[source]
            item.paragraph_format.left_indent = Mm(4)
            item.paragraph_format.first_line_indent = Mm(-4 if mode == "Record" else 0)
    table_lead = document.styles.add_style("Pilot Table Lead", WD_STYLE_TYPE.PARAGRAPH)
    table_lead.base_style = document.styles["Compact"]
    table_lead.paragraph_format.keep_with_next = True
    table_lead.paragraph_format.keep_together = True
    # Only expanded long Q15 tables: retain the existing header styling, but
    # paragraph rows must not look like dozens of separate budget entries.
    long_budget = document.styles.add_style("Pilot Long Budget", WD_STYLE_TYPE.TABLE)
    long_budget.base_style = document.styles["Table"]
    properties = OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    inside = OxmlElement("w:insideH")
    inside.set(qn("w:val"), "nil")
    borders.append(inside)
    properties.append(borders)
    long_budget.element.append(properties)
    # Each purpose block occupies a row only to support Word pagination. Avoid
    # adding the base table's 2.85 pt padding twice to every authored paragraph.
    # Keep a modest 1.4 pt per edge; font/line/paragraph spacing stays unchanged.
    cells = OxmlElement("w:tcPr")
    margins = OxmlElement("w:tcMar")
    for edge in ("top", "bottom"):
        margin = OxmlElement("w:" + edge)
        margin.set(qn("w:w"), "28")
        margin.set(qn("w:type"), "dxa")
        margins.append(margin)
    cells.append(margins)
    long_budget.element.append(cells)
    # Conditional header formatting is not consistently inherited by readers.
    for conditional in document.styles["Table"].element.findall(qn("w:tblStylePr")):
        long_budget.element.append(copy.deepcopy(conditional))
    document.save(reference)
    # python-docx assigns wall-clock ZIP timestamps; canonicalize for rebuilds.
    original = reference.read_bytes()
    result = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(original)) as archive,
        zipfile.ZipFile(result, "w") as target_zip,
    ):
        for name in sorted(archive.namelist()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target_zip.writestr(info, archive.read(name))
    reference.write_bytes(result.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--language", choices=("en", "zh-Hant"), required=True)
    args = parser.parse_args()
    prepare_layout(args.template, args.font, args.language)
