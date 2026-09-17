import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_archive_gap_panels import FIRST,LAST,PAIRS,rows,cases,split_css
from storage_context_contract import without_reviewed_context


class ArchiveGapPanelTests(unittest.TestCase):
    def test_exact_owned_css_addition_to_0329(self):
        old,panel=split_css(without_reviewed_context((ROOT/'src/layout.css').read_text(),'css'))
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(),'30277f858a649ac1874dfb49ffac3bc44929078473dcc39d4af8cf432284e768')
        self.assertIn('@media print',panel)
        for forbidden in ['font-size','line-height','display:','visibility:','content:','height:','overflow:']:
            self.assertNotIn(forbidden,panel)
        for selector in FIRST+LAST:self.assertEqual(panel.count(selector),2)

    def test_all_64_missing_answer_combinations_match_only_intended_pairs(self):
        for name,html,expected in list(rows(ROOT))+cases(ROOT):
            soup=BeautifulSoup(html,'html.parser')
            selected=[]
            for pair,first,last in zip(PAIRS,FIRST,LAST):
                a,b=soup.select(first),soup.select(last)
                self.assertEqual(len(a),len(b),name)
                if a:
                    self.assertEqual(len(a),1);selected.append(list(pair))
            self.assertEqual(selected,expected,name)

    def test_unmarked_css_is_rejected(self):
        with self.assertRaises(AssertionError):split_css('body {}')
