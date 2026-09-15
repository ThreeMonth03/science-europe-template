"""Prepare PDF fonts and Word styles in a disposable build directory."""

import argparse
import copy
import io
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
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
        lang.set(qn("w:val"), "zh-TW" if language == "zh-Hant" else "en-GB")
        lang.set(qn("w:eastAsia"), "zh-TW")
        props.append(lang)
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in document.styles:
            item = document.styles[name]
            item.font.size = Pt(10.5)
            # A relative line height keeps mixed-script text expandable. Do not
            # use an exact height or smaller type merely to reduce page count.
            item.paragraph_format.line_spacing = 1.2
            item.paragraph_format.space_before = Pt(0)
            item.paragraph_format.space_after = Pt(2 if name == "Compact" else 4)
            item.paragraph_format.widow_control = True
    for level, size in enumerate((21, 15, 11, 11, 10.5), 1):
        if f"Heading {level}" in document.styles:
            item = document.styles[f"Heading {level}"]
            item.font.size, item.font.bold = Pt(size), True
            item.font.italic = False
            if level == 3:
                item.font.bold = False
                item.font.color.rgb = RGBColor.from_string("47565C")
            item.paragraph_format.keep_with_next = True
            item.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            item.paragraph_format.keep_together = True
            item.paragraph_format.page_break_before = False
            item.paragraph_format.space_before = Pt(8 if level >= 4 else 12)
            item.paragraph_format.space_after = Pt(3 if level >= 4 else 4 if level == 3 else 6)
    label = document.styles.add_style("Pilot Label", WD_STYLE_TYPE.PARAGRAPH)
    label.base_style = document.styles["Body Text"]
    label.paragraph_format.keep_with_next = True
    label.paragraph_format.space_before = Pt(4)
    label.paragraph_format.space_after = Pt(3)
    lead = document.styles.add_style("Pilot Lead", WD_STYLE_TYPE.PARAGRAPH)
    lead.base_style = document.styles["Body Text"]
    lead.paragraph_format.keep_with_next = True
    list_lead = document.styles.add_style("Pilot List Lead", WD_STYLE_TYPE.PARAGRAPH)
    list_lead.base_style = document.styles["Compact"]
    list_lead.paragraph_format.keep_with_next = True
    # Q11-specific styles: do not alter free-answer or other list pagination.
    for name, keep_next in (("Pilot Repository Lead", True), ("Pilot Repository Item", False)):
        item = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        item.base_style = document.styles["Compact"]
        item.paragraph_format.keep_with_next = keep_next
        item.paragraph_format.keep_together = True
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
