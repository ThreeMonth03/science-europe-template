import sys
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_empty_pdf import ROOT, SELECTOR, cases, split_css, render, prepared_css


class EmptyPdfTests(unittest.TestCase):
    def test_only_exact_four_missing_facts_match(self):
        for name,source,eligible in cases(render(ROOT,{},True)):
            with self.subTest(name=name):
                self.assertEqual(int(eligible),len(BeautifulSoup('<html><body>'+source+'</body></html>','html.parser').select(SELECTOR)))

    def test_panel_does_not_change_fonts_or_hide_content(self):
        css=(ROOT/'src/layout.css').read_text();before,panel=split_css(css)
        self.assertEqual(3,panel.count(SELECTOR))
        for forbidden in ['font-size','line-height','display:', 'visibility:', 'content:', 'height:', 'overflow:']:
            self.assertNotIn(forbidden,panel)
        self.assertIn('border-left-width: 3px',panel)
        self.assertIn('break-inside: avoid',before)

    def test_prepared_font_is_embedded_in_engine_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src/fonts').mkdir(parents=True)
            (root/'src/layout.css').write_text('{{ assets("src/fonts/PilotTC.ttf").data_base64 }}')
            (root/'src/fonts/PilotTC.ttf').write_bytes(b'test-font')
            self.assertEqual('dGVzdC1mb250',prepared_css(root))

    def test_missing_font_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir()
            (root/'src/layout.css').write_text('{{ assets("src/fonts/PilotTC.ttf").data_base64 }}')
            with self.assertRaises(AssertionError):prepared_css(root)
