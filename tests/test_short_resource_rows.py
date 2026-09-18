import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from short_resource_rows_contract import project_source, HELPER, ENTRY, historical
from probe_short_resource_rows import check
from probe_pdf_budget_reading import matrix, render
from bs4 import BeautifulSoup


class ShortResourceRowsTests(unittest.TestCase):
    def test_exact_source_projection(self):
        sources,metadata=project_source()
        self.assertEqual(metadata['version'],'0.3.41')
        self.assertNotIn(HELPER,sources)
        self.assertEqual(sources[ENTRY],historical(ENTRY))

    def test_independent_grammar_and_exact_bytes_in_both_escape_modes(self):
        self.assertGreater(len(check(ROOT)),100)

    def test_real_question_format_isolation_and_long_table_controls(self):
        for name,replies,_ in matrix():
            if name not in ['short','rows-8','rows-32','rows-33','long']:continue
            for escaped in [False,True]:
                pdf=BeautifulSoup(render(ROOT,replies,True,autoescape=escaped),'html.parser')
                self.assertEqual(len(pdf.select('.pdf-short-resource-row')),8 if name=='rows-8' else 0,name)
                for word in [False,True]:
                    other=render(ROOT,replies,autoescape=escaped,word=word)
                    self.assertNotIn('pdf-short-resource-row',other)


if __name__=='__main__':unittest.main()
