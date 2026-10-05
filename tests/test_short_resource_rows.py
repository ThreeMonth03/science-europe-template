import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from short_resource_rows_contract import project_source, project_hints, HELPER, ENTRY, historical
from probe_short_resource_rows import check, fixture
from probe_pdf_budget_reading import matrix, render
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


class ShortResourceRowsTests(unittest.TestCase):
    def test_exact_source_projection(self):
        sources,metadata=project_source()
        self.assertEqual(metadata['version'],'0.3.41')
        self.assertNotIn(HELPER,sources)
        self.assertEqual(sources[ENTRY],historical(ENTRY))

    def test_independent_grammar_and_exact_bytes_in_both_escape_modes(self):
        self.assertGreater(len(check(ROOT)),100)

    def test_small_row_projection_is_explicit_and_rejects_mutated_hints(self):
        helper=Environment(loader=FileSystemLoader(ROOT),extensions=['jinja2.ext.do']).get_template(HELPER).module
        for count in [1,2,3]:
            original,rows=fixture(count)
            actual=str(helper.table(original,rows))
            self.assertEqual(len(BeautifulSoup(actual,'html.parser').select('.pdf-short-resource-row')),count)
            self.assertEqual(project_hints(actual,current_small=True),original)
            with self.assertRaises(AssertionError):project_hints(actual)
            for changed in [actual.replace('break-inside: avoid','break-inside: auto',1),
                            actual.replace('class="pdf-short-resource-row"','class="pdf-short-resource-row" hidden',1),
                            actual.replace('Keep original files and the audit trail.','Long text. '*100,1)]:
                with self.subTest(count=count),self.assertRaises(AssertionError):
                    project_hints(changed,current_small=True)

    def test_real_question_format_isolation_and_long_table_controls(self):
        for name,replies,_ in matrix():
            if name not in ['short','rows-8','rows-32','rows-33','long']:continue
            for escaped in [False,True]:
                pdf=BeautifulSoup(render(ROOT,replies,True,autoescape=escaped),'html.parser')
                self.assertEqual(len(pdf.select('.pdf-short-resource-row')),{'short':2,'long':1,'rows-8':8,'rows-32':31,'rows-33':32}.get(name,0),name)
                for word in [False,True]:
                    other=render(ROOT,replies,autoescape=escaped,word=word)
                    self.assertNotIn('pdf-short-resource-row',other)


if __name__=='__main__':unittest.main()
