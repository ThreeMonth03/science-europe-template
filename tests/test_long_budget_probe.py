import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_long_budget_word import cases,current_cases,units,expand_expected,TAIL_MARKER,SEPARATOR


class LongBudgetProbeTests(unittest.TestCase):
    def test_guard_fixture_coverage(self):
        rows=cases(); self.assertEqual(28,len(rows)); self.assertEqual(9,sum(r[2] for r in rows))
        self.assertEqual(len(rows),len({r[0] for r in rows}))

    def test_current_long_text_cases_extend_without_rewriting_history(self):
        for grouped, count in [(False,33),(True,42)]:
            original=cases(grouped=grouped); current=current_cases(grouped=grouped)
            self.assertEqual(count,len(current))
            self.assertEqual(len(current),len({r[0] for r in current}))
            self.assertEqual([(name,html) for name,html,_ in original],
                             [(name,html) for name,html,_ in current[:len(original)]])
            for name,_,selected in current:
                if name=='wide-paragraph' or name.startswith('single-'):
                    self.assertTrue(selected)
        self.assertFalse(next(ok for name,_,ok in cases() if name=='wide-paragraph'))
        self.assertEqual(15,sum(r[2] for r in current_cases()))

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
        double=copy.deepcopy(table); double['c'][4][0][3].append(copy.deepcopy(row))
        old=expand_expected(double); current=expand_expected(double,current_separator=True)
        self.assertEqual([old[0],SEPARATOR,old[1]],current)
        self.assertEqual(result,expand_expected(table,current_separator=True))

    def test_tail_marker_is_current_only_and_keeps_long_tails_splittable(self):
        attr=['',[],[]]; para=lambda s:{'t':'Para','c':[{'t':'Str','c':s}]}
        cell=lambda blocks:[copy.deepcopy(attr),{'t':'AlignDefault'},1,1,blocks]
        for tail in [para('Allocation.'),para('x'*161),{'t':'Div','c':[attr,[para('Wrapped allocation.')]]}]:
            row=[copy.deepcopy(attr),[cell([para('Resource')]+[para(str(i)) for i in range(12)]+[tail]),cell([para('0 TWD')]),cell([para('Funder')])]]
            table={'t':'Table','c':[copy.deepcopy(attr),[None,[]],[],[copy.deepcopy(attr),[[copy.deepcopy(attr),[cell([para('Title')])]*3]]],[[copy.deepcopy(attr),0,[],[row]]],[copy.deepcopy(attr),[]]]}
            before=copy.deepcopy(table); old=expand_expected(table)
            current=expand_expected(table,current_tail=True)
            final=current[0]['c'][4][0][3][-1][1][0][4]
            if tail['t']=='Para' and len(tail['c'][0]['c'])<=160:
                self.assertEqual(TAIL_MARKER,final.pop(0))
            self.assertEqual(old,current)
            self.assertEqual(before,table)
