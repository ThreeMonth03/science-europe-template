import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_long_budget_word import cases,units,expand_expected


class LongBudgetProbeTests(unittest.TestCase):
    def test_guard_fixture_coverage(self):
        rows=cases(); self.assertEqual(28,len(rows)); self.assertEqual(9,sum(r[2] for r in rows))
        self.assertEqual(len(rows),len({r[0] for r in rows}))

    def test_units_preserve_all_wrappers_and_inline_content(self):
        para={'t':'Para','c':[{'t':'Code','c':[['',[],[]],'Cost-2027.csv']}]}
        attr=['',['answer-detail'],[['data-fact-id','resource-justification']]]
        source=[{'t':'Div','c':[attr,[para,copy.deepcopy(para)]]}]
        result=units(source)
        self.assertEqual(2,len(result)); self.assertEqual([para],result[0]['c'][1])
        self.assertEqual(attr,result[1]['c'][0]); self.assertEqual(2,len(source[0]['c'][1]))

    def test_table_oracle_keeps_zero_and_exact_paragraph_order(self):
        attr=['',[],[]]; para=lambda s:{'t':'Para','c':[{'t':'Str','c':s}]}
        cell=lambda blocks:[copy.deepcopy(attr),{'t':'AlignDefault'},1,1,blocks]
        row=[copy.deepcopy(attr),[cell([para('Resource')]+[para(str(i)) for i in range(12)]),cell([para('0 TWD')]),cell([para('Funder')])]]
        table={'t':'Table','c':[copy.deepcopy(attr),[None,[]],[],[copy.deepcopy(attr),[[copy.deepcopy(attr),[cell([para('Title')])]*3]]],[[copy.deepcopy(attr),0,[],[row]]],[copy.deepcopy(attr),[]]]}
        before=copy.deepcopy(table); result=expand_expected(table)
        self.assertEqual(before,table); self.assertEqual(1,len(result))
        head=result[0]['c'][3][1]; self.assertEqual(2,len(head)); self.assertEqual([para('0 TWD')],head[1][1][1][4])
        rows=result[0]['c'][4][0][3]
        self.assertEqual([[para(str(i))] for i in range(12)],[r[1][0][4] for r in rows])
        self.assertTrue(all(r[1][0][3]==3 for r in rows))
