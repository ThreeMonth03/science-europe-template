import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_budget_word import allowed_changes,cases


class BudgetProbeTests(unittest.TestCase):
    def test_only_existing_text_in_keep_wrapper_is_allowed(self):
        before={'t':'Plain','c':[{'t':'Str','c':'0 TWD'}]}
        after={'t':'Div','c':[['',[],[['custom-style','Pilot List Lead']]],[{'t':'Para','c':before['c']}]]}
        self.assertEqual(1,allowed_changes(before,after))
        after['c'][1][0]['c']=[{'t':'Str','c':'5000 TWD'}]
        with self.assertRaises(AssertionError): allowed_changes(before,after)

    def test_deleting_table_or_changing_unknown_style_fails(self):
        with self.assertRaises(AssertionError): allowed_changes([{'t':'Table','c':[]}],[])
        with self.assertRaises(AssertionError): allowed_changes({'t':'Str','c':'original'},{'t':'Str','c':'changed'})

    def test_native_probe_has_positive_and_rejected_layout_cases(self):
        rows=cases()
        self.assertEqual(24,len(rows)); self.assertEqual(5,sum(r[2] for r in rows))
        self.assertEqual(len(rows),len({r[0] for r in rows}))

    def test_budget_fixtures_preserve_prior_answers(self):
        from generate_budget_fixtures import budget_cases
        from generate_preservation_fixtures import preservation_cases
        from generate_pilot_fixtures import IDS
        for language in ['en','zh-Hant']:
            base=preservation_cases(language)['preservation-complete']; variants=budget_cases(language)
            changed=[k for k in base if base[k]!=variants['budget-long'][k]]
            self.assertEqual(1,len(changed)); self.assertTrue(changed[0].endswith(IDS['costDescriptionQUuid']))
            self.assertEqual(60,variants['budget-long'][changed[0]]['value'].count('BUDGET-PARA-'))
            changed=[k for k in base if base[k]!=variants['budget-many'][k]]
            self.assertEqual(1,len(changed)); self.assertTrue(changed[0].endswith(IDS['costQUuid']))
            self.assertEqual(8,len(variants['budget-many'][changed[0]]['value']))
