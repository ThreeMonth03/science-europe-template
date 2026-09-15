import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_q9_word import allowed_changes,cases
from generate_q9_word_fixtures import q9_word_cases,IDS


class Q9ProbeTests(unittest.TestCase):
    def test_only_identical_strong_label_in_styled_para(self):
        old={'t':'Plain','c':[{'t':'Strong','c':[{'t':'Str','c':'Original.csv'}]}]}
        new={'t':'Div','c':[['',[],[['custom-style','Pilot List Lead']]],[{'t':'Para','c':copy.deepcopy(old['c'])}]]}
        self.assertEqual(1,allowed_changes(old,new))
        new['c'][1][0]['c'][0]['c'][0]['c']='changed.csv'
        with self.assertRaises(AssertionError):allowed_changes(old,new)

    def test_deleted_flags_and_wrong_style_are_rejected(self):
        with self.assertRaises(AssertionError):allowed_changes([1,2],[1])
        with self.assertRaises(AssertionError):allowed_changes('Compact','Pilot Label')

    def test_boundaries_and_complex_fallbacks_present(self):
        rows=cases();self.assertEqual(29,len(rows));self.assertEqual(9,sum(n>0 for _,_,n in rows))
        self.assertEqual(len(rows),len({name for name,_,_ in rows}))

    def test_partial_fixtures_keep_unknown_distinct_from_no(self):
        for locale in ['en','zh-Hant']:
            replies=q9_word_cases(locale)['q9-partial-flags'];parent=IDS['preservingCUuid']+'.'+IDS['producedDataQUuid']
            first,second,third=[parent+'.'+v for v in replies[parent]['value']]
            self.assertEqual(IDS['containPersonalYesAUuid'],replies[first+'.'+IDS['containPersonalQUuid']]['value'])
            self.assertNotIn(first+'.'+IDS['containSensitiveQUuid'],replies)
            self.assertNotIn(second+'.'+IDS['containPersonalQUuid'],replies)
            self.assertEqual(IDS['containSensitiveNoAUuid'],replies[second+'.'+IDS['containSensitiveQUuid']]['value'])
            for key in ['containPersonalQUuid','containSensitiveQUuid']:self.assertNotIn(third+'.'+IDS[key],replies)

    def test_many_and_long_are_reproducible_public_inputs(self):
        for locale in ['en','zh-Hant']:
            matrix=q9_word_cases(locale);parent=IDS['preservingCUuid']+'.'+IDS['producedDataQUuid']
            self.assertEqual(8,len(matrix['q9-many-datasets'][parent]['value']))
            purpose=next(v['value'] for k,v in matrix['q9-long-purpose'].items() if k.endswith(IDS['cpersGdprPurposeQUuid']))
            self.assertEqual(30,purpose.count('Q9-PARA-'));self.assertIn('Ethics-v1.2.csv',purpose)
            self.assertIn('https://example.org/ethics?a=1&b=2',purpose)
