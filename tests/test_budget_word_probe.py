import sys
import json
import subprocess
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_budget_word import allowed_changes,cases,heading_cases,verify_heading_move,short_row_cases,verify_row_xml


class BudgetProbeTests(unittest.TestCase):
    def test_owned_budget_first_lines_align_without_touching_other_content(self):
        from probe_budget_word import ROOT, IMAGE, RUNNER, ROW_CALL, fixture
        lua=(ROOT/'src/word/pilot.lua').read_text()
        call='align_budget_cells('+ROW_CALL+')'
        self.assertEqual(lua.count(call),1)
        expected={'eight':8,'one':1,'32':32,'33-fallback':33,'zero-rows':0,
            'chinese':2,'emphasis':2,'real-fact-attributes':8,'missing-amount':8,
            'missing-currency':8,'missing-funding':8,'missing-purpose':2,
            'four-paragraphs':2,'five-paragraphs':2,'long-purpose':2,'long-token':2,
            'long-funding':8,'hard-break':2,'list':2,'image':2,'link':2,'nested-table':2,
            'styled':2,'column-span':0,'four-columns':0,'other-question':0,'other-table':0,
            'authored-wrapper':0,'mixed':8,'mixed-expanded-33':33,'literal-marker':2}
        self.assertEqual(set(expected),{name for name,_,_ in short_row_cases()})
        cases=[(name,html,expected[name]) for name,html,_ in short_row_cases()]
        base=fixture()
        cases += [
            ('custom-table',base.replace('<table class=', '<table custom-style="Other" class='),0),
            ('custom-amount',base.replace('0 TWD','<div custom-style="Other"><p>0 TWD</p></div>'),0),
            ('no-label',base.replace('<strong>Resource 0</strong>','Resource 0').replace('<strong>Resource 1</strong>','Resource 1'),0),
            ('multi-paragraph-funding',base.replace('Institute.','<p>Institute.</p><p>Original funding note.</p>'),2),
            ('owned-funding-wrapper',base.replace('Institute.','<div class="answer-detail"><p>Institute.</p></div>'),2),
            ('owned-multi-paragraph-funding',base.replace('Institute.','<div class="answer-detail"><p>Institute.</p><p>Original note.</p></div>'),2),
            ('escaped-inline',base.replace('0 TWD','<em>0</em> TWD &amp; tax').replace('Institute.','<a href="https://example.org/?a=1&amp;b=2">Institute.</a>'),2),
        ]
        html=''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_ in cases)
        results=[]
        for source in [lua.replace(call,ROW_CALL),lua]:
            raw=subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],
                input=json.dumps(dict(html=html,lua=source)).encode(),timeout=180)
            results.append({b['c'][0][0]:b for b in json.loads(raw)['blocks']})
        def only_styles(before,after):
            if before==after:return 0
            if isinstance(before,dict) and isinstance(after,dict):
                if before.get('t') in ['Plain','Para'] and after.get('t')=='Div':
                    self.assertEqual(after['c'],[['',[],[['custom-style','Body Text']]],[dict(t='Para',c=before['c'])]])
                    return 0
                if before.get('t')==after.get('t')=='Div' and before['c'][0]==['',[],[['custom-style','Pilot Label']]]:
                    self.assertEqual(after['c'],[['',[],[['custom-style','Pilot Budget Label']]],before['c'][1]])
                    return 1
                self.assertEqual(before.keys(),after.keys())
                return sum(only_styles(before[k],after[k]) for k in before)
            if isinstance(before,list) and isinstance(after,list):
                self.assertEqual(len(before),len(after))
                return sum(only_styles(a,b) for a,b in zip(before,after))
            self.fail('Unexpected content, keep, column width or row change')
        for name,_,count in cases:
            with self.subTest(case=name):
                before,after=[r['case-'+name] for r in results]
                self.assertEqual(only_styles(before,after),count)
                if count==0:self.assertEqual(before,after)

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

    @staticmethod
    def tail_xml_pair(text='This resource supports findability of data.'):
        from probe_budget_word import TAIL_MARKER
        start='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tblPr><w:tblStyle w:val="PilotLongBudget"/></w:tblPr>'
        header='<w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc><w:p><w:r><w:t>0 TWD</w:t></w:r></w:p></w:tc></w:tr>'
        tail='<w:tr><w:tc><w:tcPr><w:gridSpan w:val="3"/></w:tcPr>'+TAIL_MARKER+'<w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:tc></w:tr>'
        before=start+header+tail+'</w:tbl></w:body></w:document>'
        after=before.replace(TAIL_MARKER,'').replace('<w:tr><w:tc>','<w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc>',1)
        return before,after

    def test_current_tail_is_explicit_and_does_not_relax_old_oracle(self):
        before,after=self.tail_xml_pair()
        verify_row_xml(before,after,0,current_tail=True)
        with self.assertRaises(AssertionError): verify_row_xml(before,after,0)
        for text in ['x'*160, '中'*80]:
            verify_row_xml(*self.tail_xml_pair(text),0,current_tail=True)
        from probe_budget_word import TAIL_MARKER
        plain=before.replace(TAIL_MARKER,'')
        verify_row_xml(plain,plain,0,current_tail=True)
        verify_row_xml(plain,plain,0)
        # Two owned tails still preserve their independent record identities.
        two_before=before.replace('</w:body>',before.split('<w:body>',1)[1].split('</w:body>',1)[0].replace('0 TWD','5000 TWD')+'</w:body>')
        two_after=after.replace('</w:body>',after.split('<w:body>',1)[1].split('</w:body>',1)[0].replace('0 TWD','5000 TWD')+'</w:body>')
        verify_row_xml(two_before,two_after,0,current_tail=True)
        # The independent short-row count remains exact after undoing the tail.
        short='<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Keep.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        kept=short.replace('<w:tr>','<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        mixed_before=before.replace('<w:body>','<w:body>'+short)
        mixed_after=after.replace('<w:body>','<w:body>'+kept)
        verify_row_xml(mixed_before,mixed_after,1,current_tail=True)
        with self.assertRaises(AssertionError): verify_row_xml(mixed_before,mixed_after,0,current_tail=True)

    def test_current_tail_rejects_forged_or_unbounded_marker_rows(self):
        from probe_budget_word import TAIL_MARKER
        before,after=self.tail_xml_pair()
        malformed=[
            before.replace('PilotLongBudget','Table'),
            before.replace('<w:gridSpan w:val="3"/>','<w:gridSpan w:val="2"/>'),
            before.replace('<w:gridSpan w:val="3"/>',''),
            before.replace('<w:gridSpan w:val="3"/>','<w:gridSpan w:val="3"/><w:vMerge/>'),
            before.replace('<w:tr><w:tc>','<w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc>'),
            before.replace('</w:tbl>','<w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>'),
            before.replace(TAIL_MARKER,TAIL_MARKER*2),
            before.replace('</w:tc></w:tr></w:tbl>','<w:p/></w:tc></w:tr></w:tbl>'),
            before.replace('</w:r></w:p></w:tc></w:tr></w:tbl>','<w:drawing/></w:r></w:p></w:tc></w:tr></w:tbl>'),
            before.replace(TAIL_MARKER,'').replace('<w:body>','<w:body>'+TAIL_MARKER),
            self.tail_xml_pair('')[0],self.tail_xml_pair('x'*161)[0],self.tail_xml_pair('中'*81)[0],
        ]
        for source in malformed:
            with self.subTest(source=source):
                with self.assertRaises(AssertionError): verify_row_xml(source,after,0,current_tail=True)

    def test_current_tail_rejects_text_style_and_unrelated_row_changes(self):
        before,after=self.tail_xml_pair()
        for changed in [
            after.replace('0 TWD','5000 TWD'),
            after.replace('findability','reusability'),
            after.replace('<w:p>','<w:p><w:pPr><w:keepNext/></w:pPr>',1),
            after.replace('<w:cantSplit/>','<w:cantSplit w:val="1"/>'),
            after.replace('<w:cantSplit/>','<w:cantSplit/>'*2),
            after.replace('<w:cantSplit/>',''),
            after.replace('<w:tblHeader/>','<w:tblHeader/><w:cantSplit/>'),
        ]:
            with self.subTest(changed=changed):
                with self.assertRaises(AssertionError): verify_row_xml(before,changed,0,current_tail=True)

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
