import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_budget_word import allowed_changes,cases,heading_cases,verify_heading_move,short_row_cases,verify_row_xml


class BudgetProbeTests(unittest.TestCase):
    def test_current_overview_releases_budgets_but_keeps_small_no_budget_answers(self):
        from probe_budget_word import overview_cases
        rows = overview_cases()
        self.assertEqual(36, len(rows))
        self.assertEqual(len(rows), len({name for name,_,_ in rows}))
        for name,html,kept in rows:
            if '<table' in html: self.assertFalse(kept, name)
        self.assertEqual(5, sum(kept for _,_,kept in rows))

    def test_row_guards_cover_partial_mixed_and_unowned_content(self):
        rows=short_row_cases()
        self.assertEqual(len(rows),len({name for name,_,_ in rows}))
        for name in ['missing-amount','missing-currency','missing-funding','mixed','chinese']:
            self.assertGreater(next(count for key,_,count in rows if key==name),0)
        for name in ['long-purpose','five-paragraphs','hard-break','styled','nested-table','authored-wrapper','four-columns']:
            self.assertEqual(next(count for key,_,count in rows if key==name),0)

    def test_row_oracle_rejects_text_and_unrelated_style_changes(self):
        prefix='<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:tr>'
        body='<w:tc><w:p><w:r><w:t>0 TWD</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        before=prefix+body; after=prefix+'<w:trPr><w:cantSplit/></w:trPr>'+body
        verify_row_xml(before,after,1)
        for broken in [after.replace('0 TWD','100 TWD'),after.replace('<w:p>','<w:p><w:pPr><w:keepNext/></w:pPr>')]:
            with self.assertRaises(AssertionError): verify_row_xml(before,broken,1)

    def test_row_xml_rejects_forged_marker_outside_a_valid_row(self):
        from jinja2 import Environment,FileSystemLoader,StrictUndefined,UndefinedError
        root=Path(__file__).resolve().parents[1]
        template=Environment(loader=FileSystemLoader(root),undefined=StrictUndefined).get_template('src/word/short-tables.xml')
        for marker in ['<!--DSW:SE:budget-row:v1-->', '<!--DSW:SE:history-row:v1-->']:
            for malformed in [marker,'<w:tr>'+marker+'</w:tr>','<w:tr><w:tc><w:tcPr />'+marker*2+'</w:tc></w:tr>']:
                with self.assertRaises(UndefinedError): template.render(content=malformed)

    def test_heading_probe_covers_missing_long_and_unowned_tables(self):
        rows=heading_cases()
        self.assertEqual(21,len(rows))
        self.assertEqual(len(rows),len({name for name,_,_ in rows}))
        self.assertEqual(8,sum(count==0 for _,_,count in rows))
        for name in ['long-paragraph','expanded-long','two-projects','first-empty-project','no-amount','no-currency','no-funding']:
            self.assertIn(name,[row[0] for row in rows])

    def test_heading_oracle_rejects_unrelated_text_changes(self):
        before={'t':'Str','c':'Original'}
        with self.assertRaises(AssertionError): verify_heading_move(before,{'t':'Str','c':'Changed'})

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
