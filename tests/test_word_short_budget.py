import copy
from pathlib import Path
import sys
import unittest
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_word_short_budget import examples
from word_short_budget_contract import compare_blocks,OLD,NEW,W


class WordShortBudgetTests(unittest.TestCase):
    def test_selection_and_format_isolation(self):
        rows=examples(ROOT)
        self.assertEqual(len(rows),len({n for n,_,_ in rows}))
        self.assertGreaterEqual(len(rows),46)

    def table(self,widths):
        return etree.fromstring(('<w:tbl xmlns:w="'+W+'"><w:tblGrid>'+''.join('<w:gridCol w:w="'+str(v)+'"/>' for v in widths)+'</w:tblGrid><w:tr><w:tc><w:p><w:r><w:t>Keep 0 TWD.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>').encode())

    def test_only_reviewed_grid_changes_allowed(self):
        left,right=self.table(OLD),self.table(NEW)
        self.assertEqual(compare_blocks([left],[right]),1)
        self.assertEqual(compare_blocks([left],[copy.deepcopy(left)]),0)
        for bad in [etree.fromstring(etree.tostring(right).replace(b'Keep 0',b'Keep 1')),self.table([3880,1981,2059])]:
            with self.assertRaises(AssertionError):compare_blocks([left],[bad])
        right.append(etree.Element('{'+W+'}newStyle'))
        with self.assertRaises(AssertionError):compare_blocks([left],[right])


if __name__=='__main__':unittest.main()
