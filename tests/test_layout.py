import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_layout", ROOT / "scripts/prepare_layout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LayoutTests(unittest.TestCase):
    def test_word_styles_and_deterministic_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            font = root / "test.ttf"
            font.write_bytes(b"fixture font asset")
            references = []
            for name in ("first", "second"):
                folder = root / name
                (folder / "src/word").mkdir(parents=True)
                shutil.copyfile(ROOT / "src/layout.css", folder / "src/layout.css")
                shutil.copyfile(
                    ROOT / "src/word/reference.docx", folder / "src/word/reference.docx"
                )
                module.prepare_layout(folder, font, "zh-Hant")
                references.append((folder / "src/word/reference.docx").read_bytes())
                document = Document(folder / "src/word/reference.docx")
                self.assertFalse(document.styles["Heading 2"].paragraph_format.page_break_before)
                self.assertTrue(document.styles["Pilot Label"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot List Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_together)
                self.assertFalse(document.styles["Heading 4"].font.italic)
                self.assertEqual(0, document.styles["Body Text"].paragraph_format.space_before)
                for section in document.sections:
                    for container in (
                        section.header,
                        section.first_page_header,
                        section.even_page_header,
                    ):
                        self.assertFalse(
                            any(e.tag == qn("w:drawing") for e in container._element.iter())
                        )
            self.assertEqual(references[0], references[1])
