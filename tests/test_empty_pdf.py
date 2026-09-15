import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_empty_pdf import ROOT, SELECTOR, cases, split_css, render


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
