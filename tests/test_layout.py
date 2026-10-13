import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_LINE_SPACING
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_layout", ROOT / "scripts/prepare_layout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LayoutTests(unittest.TestCase):
    def test_word_terminal_budget_and_single_person_keeps_are_bounded(self):
        import copy
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from probe_budget_word import RUNNER
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        def budget(rows=2, purpose='Keep the original records.', tail='No extra equipment. Charges apply.'):
            row = ('<tr><td><p><strong>Resource 2</strong></p>'
                   '<div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>' + purpose + '</p></div>'
                   '<p>Findability and management.</p></td><td><p>0 TWD</p></td>'
                   '<td><div class="answer-detail"><p>Institute.</p></div></td></tr>')
            return ('<div id="q-required-resources"><h3>15. Resources?</h3><div class="answer">'
                    '<p>Earlier overview.</p><p>' + tail + '</p><h4 class="word-budget-heading">Budget</h4>'
                    '<div class="project-resources" data-item-id="project"><table class="resource-table">'
                    '<thead><tr><th scope="col">Purpose</th><th scope="col">Amount</th><th scope="col">Funder</th></tr></thead><tbody>' + row * rows +
                    '</tbody></table></div></div></div>')
        base = budget()
        cases = [('budget-en', base, 'Pilot Lead'),
                 ('budget-zh', budget(tail='不需額外設備。資料儲存庫會收費。', purpose='保留原始紀錄。'), 'Pilot Lead'),
                 ('budget-one', budget(rows=1), 'Pilot Lead'), ('budget-three', budget(rows=3), 'Pilot Lead'),
                 ('budget-known-charge-span', budget(tail='No extra equipment.<span data-fact-id="repository-charges" data-status="complete">Charges apply.</span>'), 'Pilot Lead'),
                 ('budget-long-earlier-answer', base.replace('<p>Earlier overview.</p>', '<div class="answer-detail"><p>'+'Keep the earlier authored answer. '*100+'</p></div>'), 'Pilot Lead'),
                 ('budget-ascii-boundary', budget(tail='a '*159+'ab'), 'Pilot Lead'),
                 ('budget-cjk-boundary', budget(tail='中'*160), 'Pilot Lead')]
        rejected = {
            'four-rows': budget(rows=4), 'long-cell': budget(purpose='a '*161),
            'long-tail': budget(tail='a '*159+'abc'), 'long-cjk-tail': budget(tail='中'*161),
            'long-token': budget(tail='A'*41), 'linked-tail': budget(tail='<a href="https://example.org">Keep.</a>'),
            'unknown-span': budget(tail='<span data-extra="x">Keep.</span>'),
            'list-cell': budget(purpose='<ul><li>Keep.</li></ul>'),
            'linked-cell': budget(purpose='<a href="https://example.org">Keep.</a>'),
            'nested-cell': budget(purpose='<table><tr><td>Keep.</td></tr></table>'),
            'empty-amount': base.replace('<p>0 TWD</p>', ''),
            'rich-budget': base.replace('class="resource-table"', 'class="resource-table word-rich-budget-metadata"'),
            'wrong-question': base.replace('q-required-resources', 'q-other'),
            'unowned-heading': base.replace(' class="word-budget-heading"', ''),
            'unknown-project': base.replace('data-item-id="project"', 'data-item-id="project" data-extra="x"'),
            'unknown-answer': base.replace('class="answer"', 'class="answer original"'),
            'unknown-header': base.replace('scope="col"', 'scope="row"', 1),
            'trailing-answer': base.replace('</table></div>', '</table></div><p>Keep later text.</p>'),
            'two-projects': base.replace('</table></div>', '</table></div><div class="project-resources"><p>Other project.</p></div>'),
        }
        cases += [('budget-'+name, html, None) for name, html in rejected.items()]
        def person(text='A. Example manages data. A. Example implements the plan.', ending='', attrs=''):
            return ('<div class="person-responsibilities short-reading-unit" data-contributor-id="person" '
                    'data-contributor-index="2"'+attrs+'><p>'+text+'</p>'+ending+'</div>')
        cases += [('person-en', person(), 'Pilot Responsibility Summary'),
                  ('person-zh', person('範例團隊負責資料管理。範例團隊負責執行資料管理方案。'), 'Pilot Responsibility Summary'),
                  ('person-boundary', person('x'*500), 'Pilot Responsibility Summary'),
                  ('person-long', person('x'*501), None),
                  ('person-missing-name-hint', person(ending='<p class="data-gap">Please provide the name.</p>'), None),
                  ('person-link', person('<a href="https://example.org">A. Example</a> manages data.'), None),
                  ('person-extra-attribute', person(attrs=' data-extra="original"'), None),
                  ('person-unmarked', person().replace(' short-reading-unit', ''), None),
                  ('person-invalid-index', person().replace('contributor-index="2"', 'contributor-index="0"'), None)]
        lua = (ROOT/'src/word/pilot.lua').read_text()
        call = '  if div.identifier == "q-required-resources" then div = keep_short_budget_narrative(div) end'
        guard = 'utf8.len(pandoc.utils.stringify(div)) <= 500 and #div.content == 1'
        self.assertEqual(lua.count(call), 1); self.assertEqual(lua.count(guard), 1)
        before = lua.replace(call, '').replace(guard, 'false and '+guard)
        runner = 'import contextlib,io,json,sys\np=json.load(sys.stdin);results=[]\nfor source in p["sources"]:\n sys.stdin=io.StringIO(json.dumps(dict(lua=source,html=p["html"])))\n out=io.StringIO()\n with contextlib.redirect_stdout(out): exec('+repr(RUNNER)+',{})\n results.append(json.loads(out.getvalue()))\nprint(json.dumps(results))'
        raw = subprocess.check_output(['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i','--entrypoint','python',image,'-c',runner],
            input=json.dumps(dict(sources=[before,lua], html=''.join('<div id="case-'+name+'">'+html+'</div>' for name,html,_ in cases))).encode(), timeout=180)
        old, new = json.loads(raw)
        self.assertEqual(old['meta'], new['meta'])
        next_marker = '<!--DSW:SE:bounded-budget-next-row:v1-->'
        def restore_row_markers(node):
            if isinstance(node, dict):
                if node.get('t') == 'RawBlock' and node.get('c') == ['openxml', next_marker]:
                    node['c'][1] = '<!--DSW:SE:budget-row:v1-->'
                    return 1
                return sum(restore_row_markers(value) for value in node.values())
            return sum(restore_row_markers(value) for value in node) if isinstance(node, list) else 0
        def only_wrapper(left, right, style):
            if left == right: return 0
            if isinstance(left, dict) and isinstance(right, dict):
                if left.get('t') == 'Para' and right.get('t') == 'Div':
                    self.assertEqual(right['c'], [['',[],[['custom-style',style]]],[left]])
                    return 1
                self.assertEqual(left.keys(), right.keys())
                return sum(only_wrapper(left[k], right[k], style) for k in left)
            self.assertIsInstance(left, list); self.assertIsInstance(right, list)
            self.assertEqual(len(left), len(right))
            return sum(only_wrapper(a,b,style) for a,b in zip(left,right))
        self.assertEqual(len(cases), len(old['blocks'])); self.assertEqual(len(cases), len(new['blocks']))
        for (name, _, style), left, right in zip(cases, old['blocks'], new['blocks']):
            with self.subTest(case=name):
                right = copy.deepcopy(right)
                rows = 1 if name == 'budget-one' else 3 if name == 'budget-three' else 2
                self.assertEqual(restore_row_markers(right), rows - 1 if name.startswith('budget-') and style else 0)
                if style is None: self.assertEqual(left, right)
                else: self.assertEqual(only_wrapper(left,right,style), 1)

    def test_question_hierarchy_is_scoped_without_smaller_body_text(self):
        css = (ROOT/'src/layout.css').read_text()
        self.assertIn('html body .question > h3 { font-size: 11.5pt; font-weight: bold; color: #000; }', css)
        self.assertIn('html body { font-size: 10.5pt; line-height: 1.5; color: #222; }', css)
        self.assertIn('html body .dataset-list h5 { font-size: 11pt;', css)

    def test_review_diagnostic_and_restricted_permission_keep_only_their_leads(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from probe_budget_word import IMAGE, RUNNER
        diagnostic = '<div class="data-gap template-gap storage-detail-limits"><p>Details not mapped:</p><ul><li>Storage locations.</li><li>Backup schedule.</li></ul></div>'
        def q5(body=diagnostic, qid='q-store-backup'):
            return '<div id="'+qid+'"><div class="answer"><p>Earlier answer.</p>'+body+'</div></div>'
        def q8(body='<p>Original conditions.</p>', permission='Restrictions apply:', label='Dataset 1', attrs='class="answer-detail"', qid='q-copyright-ipr'):
            return '<div id="'+qid+'"><div class="answer"><ul><li><div>'+label+'</div><p>'+permission+'</p><div '+attrs+'>'+body+'</div></li></ul></div></div>'
        cases = [('q5',q5(),1),('q5-chinese',q5(diagnostic.replace('Details not mapped:', '下列細節未涵蓋：')),1),
            ('q5-long-lead',q5(diagnostic.replace('Details not mapped:', 'x'*161)),0),
            ('q5-other-question',q5(qid='q-other'),0),
            ('q5-nested',q5('<div>'+diagnostic+'</div>'),0),
            ('q5-extra-class',q5(diagnostic.replace('storage-detail-limits"','storage-detail-limits original"')),0),
            ('q5-extra-attribute',q5(diagnostic.replace('storage-detail-limits"','storage-detail-limits" data-extra="original"')),0),
            ('q8-short',q8(),1),('q8-long-paragraph',q8('<p>'+'Original terms. '*200+'</p>'),1),
            ('q8-long-list',q8('<ul>'+'<li>Original terms.</li>'*12+'</ul>'),1),
            ('q8-table',q8('<table><tr><td>Original cell.</td><td>Evidence.</td></tr></table>'),1),
            ('q8-code',q8('<pre><code>Original.csv</code></pre>'),1),
            ('q8-neutral',q8(label='<span class="dataset-label" data-list-kind="non-reference" data-list-index="2">Non-reference dataset 2</span>'),1),
            ('q8-chinese',q8(permission='此資料的限制如下：',body='<p>原始條件。</p>'),1),
            ('q8-no-introduction',q8(permission='Freely available.'),0),
            ('q8-empty',q8(''),0),('q8-whitespace',q8('<p> </p>'),0),
            ('q8-unowned',q8(attrs='class="original"'),0),
            ('q8-extra-attribute',q8(attrs='class="answer-detail" data-extra="original"'),0),
            ('q8-long-label',q8(label='x'*81),0),
            ('q8-long-permission',q8(permission='x'*320+':'),0),
            ('q8-other-question',q8(qid='q-other'),0)]
        lua = (ROOT/'src/word/pilot.lua').read_text()
        q5_call = 'return keep_q5_diagnostic_lead(keep_q5_context(div))'
        q8_guard = 'if #item == 3 and (text:sub(-1) == ":"'
        self.assertEqual(lua.count(q5_call),1); self.assertEqual(lua.count(q8_guard),1)
        before = lua.replace(q5_call,'return keep_q5_context(div)').replace(q8_guard,'if false and #item == 3 and (text:sub(-1) == ":"')
        html = ''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_ in cases)
        runner = 'import contextlib,io,json,sys\np=json.load(sys.stdin);results=[]\nfor source in p["sources"]:\n sys.stdin=io.StringIO(json.dumps(dict(lua=source,html=p["html"])))\n out=io.StringIO()\n with contextlib.redirect_stdout(out): exec('+repr(RUNNER)+',{})\n results.append(json.loads(out.getvalue()))\nprint(json.dumps(results))'
        raw = subprocess.check_output(['docker','run','--rm','--network','none','--log-driver','none','-i','--entrypoint','python',IMAGE,'-c',runner],
            input=json.dumps(dict(sources=[before,lua],html=html)).encode(),timeout=180)
        results = [r['blocks'] for r in json.loads(raw)]
        def only_lead_wrapper(old,new):
            if old == new: return 0
            if isinstance(old,dict) and isinstance(new,dict):
                if old.get('t') in ['Para','Plain'] and new.get('t') == 'Div':
                    self.assertIn(new['c'][0], [['',[],[['custom-style','Pilot Lead']]],['',[],[['custom-style','Pilot List Lead']]]])
                    self.assertEqual(new['c'][1],[dict(t='Para',c=old['c'])])
                    return 1
                self.assertEqual(old.keys(),new.keys())
                return sum(only_lead_wrapper(old[k],new[k]) for k in old)
            self.assertIsInstance(old,list); self.assertIsInstance(new,list); self.assertEqual(len(old),len(new))
            return sum(only_lead_wrapper(a,b) for a,b in zip(old,new))
        self.assertEqual(len(results[0]),len(cases)); self.assertEqual(len(results[1]),len(cases))
        for (name,_,expected),old,new in zip(cases,*results):
            with self.subTest(case=name): self.assertEqual(only_lead_wrapper(old,new),expected)

    def test_word_provenance_keeps_only_owned_bounded_metadata_and_all_inlines(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        env.filters['datetime_format'] = lambda value, fmt: '2026-09-22'
        provenance = env.get_template('src/document-provenance.html.j2').render(dc=dict(
            project=dict(name='Workspace label'), document=dict(created_at=''),
            pkg=dict(name='Coastal KM', version='2.7.0', organization_id='dsw', km_id='root'),
            config=dict(service_name='DMP service', service_url='https://example.org/?a=1&b=2')),
            ctx=dict(phaseUuid=None), output_profile='review')
        short_pair = ('<aside><p>Knowledge model: Coastal KM, 2.7.0 (dsw:root:2.7.0)</p>'
                      '<p>Generated with <a href="https://example.org/?a=1&amp;b=2">DMP service</a>.</p></aside>')
        def owned(body, attrs='id="dmp-provenance" class="document-provenance"'):
            return '<div '+attrs+'>'+body+'</div>'
        def current(parts):
            return ''.join('<p>'+text+'</p>' for text in parts)
        final_link = '<a href="https://example.org/?a=1&amp;b=2">s</a>'
        current_five = current(['Document: Original workspace', 'Created on 2026-09-22',
            'Project phase: Planning', 'Knowledge model: Coastal KM', 'Generated with '+final_link+'.'])
        cases = [
            ('real-include-four', owned(provenance), True),
            ('current-five', owned(current_five), True),
            ('current-chinese', owned(current(['文件名稱：原始名稱', '文件建立日期：2026-09-22',
                '計畫階段：規劃', '問卷知識模型：沿岸觀測', '本文件由 '+final_link+' 產生。'])), True),
            ('current-paragraph-boundary', owned(current(['x'*320, 'Date', 'KM', final_link])), True),
            ('current-cjk-boundary', owned(current(['中'*160, '日期', '模型', final_link])), True),
            ('current-total-boundary', owned(current(['x'*300, 'y'*300, 'z'*299, final_link])), True),
            ('current-paragraph-too-long', owned(current(['x'*321, 'Date', 'KM', final_link])), False),
            ('current-cjk-too-wide', owned(current(['中'*161, '日期', '模型', final_link])), False),
            ('current-total-too-long', owned(current(['x'*300, 'y'*300, 'z'*300, final_link])), False),
            ('current-empty-value', owned(current(['', 'Date', 'KM', final_link])), False),
            ('current-missing-link', owned(current(['Name', 'Date', 'KM', 'Generated with service.'])), False),
            ('current-earlier-link', owned(current([final_link, 'Date', 'KM', 'Generated with '+final_link])), False),
            ('current-two-final-links', owned(current(['Name', 'Date', 'KM', final_link+final_link])), False),
            ('current-link-class', owned(current_five.replace('<a href=', '<a class="unknown" href=')), False),
            ('current-rich-value', owned(current_five.replace('Original workspace', '<em>Original workspace</em>')), False),
            ('current-six-paragraphs', owned(current_five+'<p>Extra.</p>'), False),
            ('current-nested-value', owned(current_five.replace('<p>Document: Original workspace</p>', '<div><p>Document: Original workspace</p></div>')), False),
            ('current-owned-aside', owned('<aside class="document-provenance">'+current_five+'</aside>'), True),
            ('current-unknown-aside', owned('<aside class="unknown">'+current_five+'</aside>'), False),
            ('current-aside-attribute', owned('<aside class="document-provenance" data-extra="x">'+current_five+'</aside>'), False),
            ('current-unowned-div', owned('<div>'+current_five+'</div>'), False),
            ('old-short-pair', owned(short_pair), True),
            ('chinese', owned('<aside><p>問卷知識模型：沿岸觀測。</p><p>由 <a href="https://example.org/">資料服務</a> 產生。</p></aside>'), True),
            ('limit', owned('<p>'+'x'*239+'</p><p>y</p>'), True),
            ('over-limit', owned('<p>'+'x'*240+'</p><p>y</p>'), False),
            ('unicode-over-limit', owned('<p>'+'中'*240+'</p><p>文</p>'), False),
            ('aside-only', short_pair, False),
            ('wrong-id', owned(short_pair, 'id="other" class="document-provenance"'), False),
            ('wrong-class', owned(short_pair, 'id="dmp-provenance" class="other"'), False),
            ('extra-class', owned(short_pair, 'id="dmp-provenance" class="document-provenance other"'), False),
            ('extra-attribute', owned(short_pair, 'id="dmp-provenance" class="document-provenance" data-extra="x"'), False),
            ('three-paragraphs', owned(short_pair+'<p>Original third paragraph.</p>'), False),
            ('nested-paragraph', owned('<div><p>Original first.</p></div><p>Original second.</p>'), False),
            ('image', owned('<p><img src="unfetched.png"></p><p>Original source.</p>'), False),
            ('styled-text', owned('<p><em>Original first.</em></p><p>Original source.</p>'), False),
        ]
        lua = (ROOT/'src/word/pilot.lua').read_text()
        anchor = 'if div.identifier == "dmp-provenance"'
        self.assertEqual(lua.count(anchor), 1)
        runner = '''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin);results=[]
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'pilot.lua'
 for lua in p['variants']:
  f.write_text(lua)
  results.append(json.loads(subprocess.check_output(
   ['pandoc','--from=html','--to=json','--lua-filter='+str(f)],input=p['html'].encode())))
print(json.dumps(results))
'''
        raw = subprocess.check_output(['docker','run','--rm','--network','none','-i',
            '--entrypoint','python',image,'-c',runner], input=json.dumps(dict(
                variants=[lua.replace(anchor, 'if false and div.identifier == "dmp-provenance"', 1), lua],
                html=''.join('<div id="case-'+str(i)+'"><p>Ordinary before.</p>'+body+'<p>Ordinary after.</p></div>' for i, (_, body, _) in enumerate(cases)))).encode(), timeout=180)
        before, after = json.loads(raw)
        self.assertEqual(before['meta'], after['meta'])
        self.assertEqual(len(before['blocks']), len(cases))
        self.assertEqual(len(after['blocks']), len(cases))
        for (name, _, changed), old, new in zip(cases, before['blocks'], after['blocks']):
            with self.subTest(case=name):
                if not changed:
                    self.assertEqual(old, new)
                    continue
                self.assertEqual(old['c'][0], new['c'][0])
                self.assertEqual(old['c'][1][0], new['c'][1][0])
                self.assertEqual(old['c'][1][-1], new['c'][1][-1])
                old_div, new_div = old['c'][1][1], new['c'][1][1]
                self.assertEqual(old_div['c'][0], ['dmp-provenance', ['document-provenance'], []])
                self.assertEqual(new_div['c'][0], ['dmp-provenance', ['document-provenance'], [['custom-style', 'Pilot Provenance']]])
                old_target, new_target = old_div, new_div
                if len(old_div['c'][1]) == 1 and old_div['c'][1][0]['t'] == 'Div':
                    old_target, new_target = old_div['c'][1][0], new_div['c'][1][0]
                    self.assertEqual(old_target['c'][0], new_target['c'][0])
                joined = []
                for index, paragraph in enumerate(old_target['c'][1]):
                    self.assertEqual(paragraph['t'], 'Para')
                    if index:
                        joined.append({'t':'LineBreak'})
                    joined.extend(paragraph['c'])
                self.assertEqual(new_target['c'][1], [{'t':'Para', 'c':joined}])
                self.assertEqual(len(old['c'][1]), 3)
                self.assertEqual(len(new['c'][1]), 3)

    def test_pdf_review_provenance_is_one_block_but_oversized_values_flow(self):
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        css = (ROOT/'src/layout.css').read_text()
        rule = 'html body aside.document-provenance { break-inside: avoid; }'
        self.assertEqual(css.count(rule), 1)
        def block(values, tag='aside', attrs='class="document-provenance"'):
            return '<'+tag+' '+attrs+'>'+''.join('<p>'+v+'</p>' for v in values)+'</'+tag+'>'
        values = ['Document: Original workspace', 'Created on 2026-09-22', 'Project phase: Planning',
                  'Knowledge model: Coastal KM', 'Generated with <a href="https://example.org/">DMP service</a>.']
        cases = [('five', block(values), True), ('four', block(values[:2]+values[3:]), True),
                 ('chinese', block(['文件名稱：原始名稱', '文件建立日期：2026-09-22', '計畫階段：規劃',
                    '問卷知識模型：沿岸觀測', '本文件由資料服務產生。']), True),
                 ('wrong-class', block(values, attrs='class="ordinary"'), False),
                 ('wrong-element', block(values, tag='div'), False),
                 ('oversized', block(['Long metadata '*500]+values[1:]), None)]
        runner = '''import json,sys
from weasyprint import HTML
p=json.load(sys.stdin)
def inspect(body,css):
 doc=HTML(string='<html><head><style>'+css+'</style></head><body><div style="height:230mm"></div>'+body+'</body></html>').render()
 rows=[]
 for page_index,page in enumerate(doc.pages):
  for box in page._page_box.descendants():
   if type(box).__name__=='TextBox':
    left=page._page_box.content_box_x(); right=left+page._page_box.width
    assert box.position_x>=left-1 and box.position_x+box.width<=right+1,('overflow',box.text)
    rows.append((page_index,box.text,box.position_x,box.position_y,box.width,box.height))
 return rows
for name,body,kept in p['cases']:
 before=inspect(body,p['css'].replace(p['rule'],'')); after=inspect(body,p['css'])
 assert ''.join(x[1] for x in before)==''.join(x[1] for x in after),(name,'text changed')
 pages=set(x[0] for x in after)
 if kept is True:
  assert len(pages)==1,(name,'split metadata',pages)
  assert len(set(x[0] for x in before))>1,(name,'control did not split')
 elif kept is False: assert before==after,(name,'ordinary layout changed')
 else: assert len(pages)>1,(name,'oversized metadata did not flow')
print(json.dumps({'passed':True,'cases':len(p['cases'])}))
'''
        raw = subprocess.check_output(['docker','run','--rm','--network','none','-i',
            '--entrypoint','python',image,'-c',runner], input=json.dumps(dict(css=css, rule=rule, cases=cases)).encode(), timeout=180)
        self.assertEqual(json.loads(raw), dict(passed=True, cases=6))

    def test_fixed_list_leads_keep_only_the_intro_without_changing_list_xml(self):
        import base64
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from probe_q8_word import IMAGE, RUNNER
        questions = [
            ('q-what-data', '02-what-data',
             'The non-equipment datasets are:', '非儀器資料集如下：'),
            ('q-access-security', '06-access-security',
             'We will use the following policies and procedures:',
             '我們將採用以下政策與程序：'),
            ('q-copyright-ipr', '08-copyright-ipr',
             'The following conditions apply to the reference and non-reference datasets that we reuse:',
             '此計畫再利用的參考及非參考資料集須遵守以下條件：'),
            ('q-share-restrictions', '10-share-restrictions',
             'Identifier information for this dataset:', '此資料集的識別碼資訊：'),
            ('q-share-restrictions', '10-share-restrictions',
             'References to other datasets:', '其他資料集的參照資訊：'),
        ]
        bodies = []
        for qid, filename, english, chinese in questions:
            source = (ROOT / ('src/questions/' + filename + '.html.j2')).read_text()
            self.assertEqual(1, source.count('<div class="answer-lead"><p>' + english + '</p></div>'))
            for lead in (english, chinese):
                for count in (1, 8):
                    # A long first item must stay free to paginate, not pull the
                    # entire list into an unbreakable chain with its short lead.
                    permission = '<p>' + ('Original answer。 ' * 160 if count == 8 else 'Original answer.') + '</p>'
                    items = ''.join('<li><div>Dataset ' + str(i) + '</div>' + permission +
                                    '<p><a href="https://example.org/item/' + str(i) + '">Original link</a></p></li>'
                                    for i in range(count))
                    bodies.append('<div id="' + qid + '"><div class="answer"><p>Earlier fixed paragraph.</p>'
                                  '<div class="answer-lead"><p>' + lead + '</p></div><ul>' + items + '</ul></div></div>')
        marked = ''.join(bodies)
        results = []
        for html in (marked.replace('<div class="answer-lead">', '<div>'), marked):
            raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i',
                '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(dict(
                    lua=(ROOT / 'src/word/pilot.lua').read_text(), html=html,
                    reference=base64.b64encode((ROOT / 'src/word/reference.docx').read_bytes()).decode())).encode(), timeout=180)
            results.append(json.loads(raw)['paragraphs'])
        self.assertEqual(len(results[0]), len(results[1]))
        changed = 0
        for before, after in zip(*results):
            self.assertEqual(before['text'], after['text'])
            self.assertEqual(before['other_xml'], after['other_xml'])
            if before['style'] != after['style']:
                self.assertEqual('PilotLead', after['style'])
                self.assertIn(after['text'], [lead for _, _, english, chinese in questions for lead in (english, chinese)])
                changed += 1
        self.assertEqual(len(bodies), changed)

    def test_generic_word_leads_are_bounded_without_changing_authored_content(self):
        import base64
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from probe_q8_word import IMAGE, RUNNER
        cases = []
        for cls in ['answer', 'answer-detail', 'unowned']:
            for value, long in [('x' * 160, False), ('x' * 161, True),
                                ('中' * 80, False), ('中' * 81, True),
                                ('<em>Original.csv</em> ' * 80, True)]:
                for bold in [False, True]:
                    name = 'case-' + str(len(cases))
                    content = '<strong>'+value+'</strong>' if bold else value
                    body = '<div class="'+cls+'"><p>'+content+'</p><p>Original second paragraph.</p></div>'
                    cases.append((name, body, int(long and (bold or cls != 'unowned'))))
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        guard = 'return units <= 160'
        self.assertEqual(lua.count(guard), 1)
        html = ''.join('<div id="'+name+'">'+body+'</div>' for name, body, _ in cases)
        results = []
        for variant in [lua.replace(guard, 'return true'), lua]:
            raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i',
                '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(dict(
                    lua=variant, html=html,
                    reference=base64.b64encode((ROOT/'src/word/reference.docx').read_bytes()).decode())).encode(), timeout=180)
            results.append(json.loads(raw))
        def removed_leads(before, after):
            if before == after: return 0
            if isinstance(before, dict) and isinstance(after, dict):
                if before.get('t') == 'Div' and after.get('t') == 'Para':
                    self.assertIn(before['c'][0], [['', [], [['custom-style', style]]] for style in ['Pilot Lead', 'Pilot Label']])
                    self.assertEqual(before['c'][1], [after])
                    return 1
                self.assertEqual(before.keys(), after.keys())
                return sum(removed_leads(before[k], after[k]) for k in before)
            self.assertIsInstance(before, list); self.assertIsInstance(after, list)
            self.assertEqual(len(before), len(after))
            return sum(removed_leads(a, b) for a, b in zip(before, after))
        for (name, _, expected), before, after in zip(cases, results[0]['ast']['blocks'], results[1]['ast']['blocks']):
            with self.subTest(case=name): self.assertEqual(removed_leads(before, after), expected)
        # The actual DOCX paragraphs preserve text and every non-style XML property.
        self.assertEqual(len(results[0]['paragraphs']), len(results[1]['paragraphs']))
        changed = 0
        for before, after in zip(results[0]['paragraphs'], results[1]['paragraphs']):
            self.assertEqual(before['text'], after['text'])
            self.assertEqual(before['other_xml'], after['other_xml'])
            if before['style'] != after['style']:
                self.assertIn(before['style'], ['PilotLead', 'PilotLabel'])
                self.assertIn(after['style'], [None, 'BodyText', 'FirstParagraph'])
                changed += 1
        self.assertEqual(changed, sum(expected for _, _, expected in cases))

    def test_authorization_keep_changes_only_the_fixed_word_lead(self):
        import sys
        from lxml import etree as E
        sys.path.insert(0, str(ROOT / 'scripts'))
        from current_support import IDS, PREFIX, environment, path
        from probe_budget_word import IMAGE
        parent = path('accessCUuid', 'openImmediatelyQUuid')
        reason = path(parent, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        auth = path(reason, 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid')
        who = path(auth, 'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthorizeQUuid')
        cases = []
        for question in ['08-copyright-ipr', '10-share-restrictions']:
            template = environment(ROOT).from_string(PREFIX + "{% include 'src/questions/"+question+".html.j2' %}")
            for kind, lead in [('Other', 'We will use the following authorization arrangements:'),
                    ('OldCommittee', 'We will make use of an existing data committee:')]:
                for value in ['', '  ', '<p>Access office.</p>', '<p>Original.</p>' * 50,
                        '<ul><li>Original A.</li><li>Original B.</li></ul>',
                        '<table><tr><td>Original.</td><td>Keep.</td></tr></table>']:
                    replies = {parent: IDS['openImmediatelyNoAUuid'], reason: IDS['notOpenLegalReasonsYesAUuid'],
                        auth: IDS['legalReasonsAuthenticatedYesAUuid'], who: IDS['legalReasonsAuthorize'+kind+'AUuid'],
                        path(who, 'legalReasonsAuthorize'+kind+'AUuid', 'legalReasonsAuthorize'+kind+'QUuid'): value}
                    for profile in ['review', 'submission']:
                        html = template.render(repliesMap=replies, output_profile=profile)
                        cases.append([html, int(bool(value.strip())), lead if question.startswith('08-') else 'We will permit authenticated access to the data.'])
        runner = '''import json,sys,subprocess,tempfile,zipfile
from pathlib import Path
p=json.load(sys.stdin);results=[]
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'pilot.lua';f.write_text(p['lua']);out=Path(tmp)/'test.docx'
 for html,count,lead in p['cases']:
  pair=[]
  for text in [html.replace('class="answer-lead"','class="authorization-control"'),html]:
   subprocess.run(['pandoc','--from=html','--to=docx','--lua-filter='+str(f),'-o',str(out)],input=text.encode(),check=True)
   with zipfile.ZipFile(out) as z:pair.append(z.read('word/document.xml').decode())
  results.append([count,lead,pair])
print(json.dumps(results))
'''
        raw = subprocess.check_output(['docker','run','--rm','--network','none','-i',
            '--entrypoint','python',IMAGE,'-c',runner],
            input=json.dumps(dict(cases=cases,lua=(ROOT/'src/word/pilot.lua').read_text())).encode(),timeout=180)
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for count, lead, pair in json.loads(raw):
            before, after = [E.fromstring(value.encode()) for value in pair]
            oldps, newps = [tree.findall('.//w:p',ns) for tree in [before,after]]
            self.assertEqual(len(oldps),len(newps)); changed = 0
            for oldp,newp in zip(oldps,newps):
                if E.tostring(oldp) == E.tostring(newp): continue
                style = newp.find('w:pPr/w:pStyle',ns)
                self.assertIsNotNone(style)
                self.assertEqual(style.get('{'+ns['w']+'}val'),'PilotLead')
                old_style = oldp.find('w:pPr/w:pStyle',ns)
                if old_style is not None:
                    self.assertEqual(old_style.get('{'+ns['w']+'}val'),'FirstParagraph')
                self.assertIn(lead, ''.join(newp.itertext()))
                prop = style.getparent()
                if old_style is None: prop.remove(style)
                else: style.set('{'+ns['w']+'}val','FirstParagraph')
                if not len(prop) and oldp.find('w:pPr',ns) is None: newp.remove(prop)
                changed += 1
            self.assertEqual(changed,count)
            self.assertEqual(E.tostring(before),E.tostring(after),'Authored content or other Word properties changed')

    def test_version_value_alignment_preserves_content_and_unowned_tables(self):
        probe_spec = importlib.util.spec_from_file_location('budget_worker', ROOT / 'scripts/probe_budget_word.py')
        worker = importlib.util.module_from_spec(probe_spec)
        probe_spec.loader.exec_module(worker)
        def table(value='<p>2026.1</p>', label='Version'):
            return ('<table class="dataset-version" data-fact-id="dataset-version" data-status="complete">'
                    '<tbody><tr><th scope="row">'+label+'</th><td>'+value+'</td></tr></tbody></table>')
        base = table()
        cases = [(name, table(value, label), count) for name, value, label, count in [
            ('english', '<p>2026.1</p>', 'Version', 1),
            ('chinese', '<p>2026.1</p>', '使用版本', 1),
            ('chinese-value', '<p>第二版（校正後）</p>', '使用版本', 1),
            ('plain', '2026.1', 'Version', 1), ('empty', '', 'Version', 0),
            ('long', '<p>'+'校正版本 2026.1；'*160+'</p>', '使用版本', 1),
            ('paragraphs', '<p>2026.1</p><p>Original note.</p>', 'Version', 1),
            ('bold', '<p><strong>2026.1</strong></p>', 'Version', 1),
            ('inline', '<p><em>2026.1</em> &lt;tag&gt; &amp; <code>v2</code><br>Keep.</p>', 'Version', 1),
            ('link', '<p><a href="https://example.org/?a=1&amp;b=2">2026.1</a></p>', 'Version', 1),
            ('list', '<ul><li>2026.1</li></ul>', 'Version', 0),
            ('styled-value', '<div custom-style="Other"><p>2026.1</p></div>', 'Version', 0),
            ('nested-table', '<table><tr><td>2026.1</td></tr></table>', 'Version', 0),
        ]]
        cases += [(name, base.replace(old, new), 0) for name, old, new in [
            ('unmarked', ' data-fact-id="dataset-version"', ''),
            ('missing', 'data-status="complete"', 'data-status="missing"'),
            ('other-class', 'class="dataset-version"', 'class="authored"'),
            ('extra-class', 'class="dataset-version"', 'class="dataset-version authored"'),
            ('custom-table', '<table ', '<table custom-style="Other" '),
            ('extra-column', '</td>', '</td><td>Original.</td>'),
            ('span', '<td>', '<td colspan="2">'),
            ('extra-row', '</tbody>', '<tr><td>Original.</td><td>Keep.</td></tr></tbody>'),
        ]]
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        self.assertEqual(lua.count('return align_dataset_version(tbl)'), 1)
        sources = [lua.replace('return align_dataset_version(tbl)', 'return tbl'), lua]
        html = ''.join('<div id="case-'+name+'">'+body+'</div>' for name, body, _ in cases)
        runner = '''import json,sys,subprocess,tempfile
from pathlib import Path
p=json.load(sys.stdin);results=[]
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'filter.lua'
 for lua in p['sources']:
  f.write_text(lua);row=[]
  for fmt in ['json','html']:
   row.append(subprocess.check_output(['pandoc','--from=html','--to='+fmt,'--lua-filter='+str(f)],input=p['html'].encode()).decode())
  results.append(row)
print(json.dumps(results))
'''
        output = subprocess.check_output(['docker','run','--rm','--network','none','-i',
            '--entrypoint','python',worker.IMAGE,'-c',runner],
            input=json.dumps(dict(sources=sources,html=html)).encode(),timeout=180)
        rows = json.loads(output)
        self.assertEqual(rows[0][1], rows[1][1], 'Non-Word output changed')
        results = [{b['c'][0][0]: b for b in json.loads(row[0])['blocks']} for row in rows]
        def only_first_style(before, after):
            if before == after: return 0
            if isinstance(before, dict) and isinstance(after, dict):
                if before.get('t') in ['Plain','Para'] and after.get('t') == 'Div':
                    self.assertEqual(after['c'], [['',[],[['custom-style','Body Text']]],[dict(t='Para',c=before['c'])]])
                    return 1
                if before.get('t') == after.get('t') == 'Div' and before['c'][0] == ['',[],[['custom-style','Pilot Label']]]:
                    self.assertEqual(after['c'], [['',[],[['custom-style','Body Text']]],before['c'][1]])
                    return 1
                self.assertEqual(before.keys(), after.keys())
                return sum(only_first_style(before[k], after[k]) for k in before)
            self.assertIsInstance(before, list); self.assertIsInstance(after, list)
            self.assertEqual(len(before), len(after))
            return sum(only_first_style(a,b) for a,b in zip(before,after))
        for name, _, count in cases:
            with self.subTest(case=name):
                self.assertEqual(only_first_style(results[0]['case-'+name],results[1]['case-'+name]),count)

    def test_word_history_keeps_only_bounded_rows_and_preserves_every_other_xml_byte(self):
        probe_spec = importlib.util.spec_from_file_location('budget_worker', ROOT / 'scripts/probe_budget_word.py')
        worker = importlib.util.module_from_spec(probe_spec)
        probe_spec.loader.exec_module(worker)
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        env.filters['datetime_format'] = lambda value, fmt: '30 Sep 2026'
        template = env.get_template('src/word/versions.html.j2')
        def render(title='Review A', note='Short note.', count=1):
            return template.render(dc=dict(project=dict(versions=[dict(name=title, description=note, created_at='')] * count)))
        base = render()
        cases = [('short', base, 1), ('many', render(count=24), 24), ('64', render(count=64), 64),
            ('no-versions', render(count=0), 0), ('missing-note', render(note=''), 1),
            ('missing-name', render(title=''), 0), ('chinese', render(note='核對資料與後設資料。'), 1),
            ('escaped', render(title='Review <A> & "B"', note='Keep <sensor> &lt;tag&gt;.'), 1),
            ('literal-marker', render(note='<!--DSW:SE:history-row:v1-->'), 1),
            ('ascii-boundary', render(note='a ' * 79 + 'ab'), 1),
            ('ascii-over', render(note='a ' * 79 + 'abc'), 0),
            ('cjk-boundary', render(note='中' * 80), 1), ('cjk-over', render(note='中' * 81), 0),
            ('token-boundary', render(title='A' * 40), 1), ('token-over', render(title='A' * 41), 0),
            ('long-note', render(note='Long note. ' * 100), 0),
            ('long-name', render(title='Review A ' * 20), 0),
            ('unmarked', base.replace(' class="version-history"', ''), 0),
            ('other-class', base.replace('version-history', 'authored-table'), 0),
            ('extra-class', base.replace('version-history', 'version-history authored'), 0),
            ('styled-table', base.replace('<table ', '<table custom-style="Other" '), 0),
            ('extra-column', base.replace('<td>Short note.</td>', '<td>Extra</td><td>Short note.</td>'), 0),
            ('spanning-cell', base.replace('<td>Short note.', '<td colspan="2">Short note.'), 0)]
        for name, detail in [('paragraphs', '<p>First.</p><p>Second.</p>'), ('break', 'First.<br>Second.'),
                ('list', '<ul><li>Keep.</li></ul>'), ('code', '<code>Keep.</code>'),
                ('style', '<span style="font-size:40pt">Keep.</span>'),
                ('nested-table', '<table><tr><td>Keep.</td></tr></table>')]:
            cases.append((name, base.replace('Short note.', detail), 0))
        for name, start, end in [('abstract', '<div class="abstract">', '</div>'),
                ('answer', '<div class="answer">', '</div>'),
                ('q9', '<div id="q-ethical-issues" class="question"><div class="answer"><div class="answer-detail">', '</div></div></div>'),
                ('q15', '<div id="q-required-resources" class="question">', '</div>')]:
            cases.append((name, start + base + end, 0))
        mixed = render(count=3).replace('Short note.', 'Long note. ' * 100, 1)
        cases.append(('mixed', mixed, 2))
        lua = (ROOT / 'src/word/short-tables.lua').read_text()
        self.assertEqual(lua.count(', Table=history_rows'), 1)
        runner = '''import json,sys,tempfile,subprocess,zipfile
from pathlib import Path
p=json.load(sys.stdin);results=[]
with tempfile.TemporaryDirectory() as tmp:
    f=Path(tmp)/'filter.lua';out=Path(tmp)/'test.docx'
    for name,html,count in p['cases']:
        pair=[]
        for lua in p['lua']:
            f.write_text(lua)
            subprocess.run(['pandoc','--from=html','--to=docx','--lua-filter='+str(f),'-o',str(out)],input=html.encode(),check=True)
            with zipfile.ZipFile(out) as z:pair.append(z.read('word/document.xml').decode())
        results.append([name,count,pair])
    outputs=[]
    for lua in p['lua']:
        f.write_text(lua)
        outputs.append(subprocess.check_output(['pandoc','--from=html','--to=html','--lua-filter='+str(f)],input=''.join(c[1] for c in p['cases']).encode()))
    assert outputs[0]==outputs[1],'Non-Word output changed'
print(json.dumps(results))
'''
        raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i',
            '--entrypoint', 'python', worker.IMAGE, '-c', runner],
            input=json.dumps(dict(cases=cases, lua=[lua.replace(', Table=history_rows', ''), lua])).encode(), timeout=180)
        templates = [Environment(loader=FileSystemLoader(ROOT), undefined=StrictUndefined, autoescape=escape)
                     .get_template('src/word/short-tables.xml') for escape in [False, True]]
        for name, count, (before, marked) in json.loads(raw):
            with self.subTest(case=name):
                self.assertEqual(marked.count('<!--DSW:SE:history-row:v1-->'), count)
                after = templates[0].render(content=marked)
                self.assertEqual(templates[1].render(content=marked), after)
                self.assertNotIn('<!--DSW:SE:history-row:v1-->', after)
                worker.verify_row_xml(before, after, count)

    def test_history_and_provenance_wrap_without_changing_ordinary_layout(self):
        probe_spec = importlib.util.spec_from_file_location('budget_worker', ROOT / 'scripts/probe_budget_word.py')
        worker = importlib.util.module_from_spec(probe_spec)
        probe_spec.loader.exec_module(worker)
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        env.filters['datetime_format'] = lambda value, fmt: '30 Sep 2026'
        template = env.from_string("{% include 'src/versions.html.j2' %}{% include 'src/document-provenance.html.j2' %}")
        css = (ROOT / 'src/style.css').read_text() + (ROOT / 'src/layout.css').read_text()
        rule = ('html body #dmp-versions td.version-name,\n'
                'html body #dmp-versions td.version-changes,\n'
                'html body .document-provenance { overflow-wrap: anywhere; word-break: break-word; }')
        self.assertEqual(css.count(rule), 1)
        cases = []
        for name, count, title, description, model in [
                ('short', 1, 'Review A', 'Checked the data.', 'Coastal KM'),
                ('missing-description', 1, '核對 A', '', '沿岸觀測'),
                ('many', 24, 'Review A', 'Checked the data.', 'Coastal KM'),
                ('long', 1, 'VERSION' + 'ABCDEFGHIJ' * 18, 'CHANGES' + '0123456789' * 45, 'MODEL' + 'ABCDEFGHIJ' * 18)]:
            dc = dict(project=dict(name='Workspace label', versions=[dict(name=title, description=description, created_at='')] * count),
                      document=dict(created_at=''),
                      pkg=dict(name=model, version='2.7.0', organization_id='dsw', km_id='root'),
                      config=dict(service_name='DMP service', service_url='https://example.org/'))
            cases.append(dict(name=name, html=template.render(dc=dc, ctx=dict(phaseUuid=None),
                output_profile='review'), text=[title, description, model]))
        runner = '''import json,sys,re
from weasyprint import HTML
p=json.load(sys.stdin)
def render(case,css):
    return HTML(string='<html><head><style>'+css+'</style></head><body>'+case['html']+'</body></html>').render()
def boxes(doc):
    return [(i,b.text,b.position_x,b.position_y,b.width,b.height) for i,page in enumerate(doc.pages)
            for b in page._page_box.descendants() if type(b).__name__=='TextBox']
norm=lambda s:re.sub(r'\\s+','',s)
for case in p['cases']:
    doc=render(case,p['css']); current=boxes(doc)
    for i,text,x,y,w,h in current:
        page=doc.pages[i]._page_box; left=page.content_box_x(); right=left+page.width
        assert x>=left-1 and x+w<=right+1,(case['name'],'overflow',text)
    for text in case['text']:
        assert norm(text) in norm(''.join(row[1] for row in current)),(case['name'],'missing',text)
    if case['name']!='long':
        assert current==boxes(render(case,p['css'].replace(p['rule'],''))),(case['name'],'ordinary layout changed')
print(json.dumps({'passed':True,'cases':len(p['cases'])}))
'''
        output = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i',
            '--entrypoint', 'python', worker.IMAGE, '-c', runner],
            input=json.dumps(dict(css=css, rule=rule, cases=cases)).encode(), timeout=180)
        self.assertEqual(json.loads(output), dict(passed=True, cases=4))

    def test_word_styles_and_deterministic_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            font = root / "test.ttf"
            font.write_bytes(b"fixture font asset")
            references = []
            for name in ("first", "second"):
                folder = root / name
                (folder / "src/word").mkdir(parents=True)
                shutil.copyfile(ROOT / "src/layout.css", folder / "src/layout.css")
                shutil.copyfile(
                    ROOT / "src/word/reference.docx", folder / "src/word/reference.docx"
                )
                module.prepare_layout(folder, font, "zh-Hant")
                references.append((folder / "src/word/reference.docx").read_bytes())
                document = Document(folder / "src/word/reference.docx")
                self.assertFalse(document.styles["Heading 2"].paragraph_format.page_break_before)
                title = document.styles["Heading 1"].paragraph_format
                self.assertEqual(26.25, title.line_spacing.pt)
                self.assertEqual(WD_LINE_SPACING.AT_LEAST, title.line_spacing_rule)
                provenance = document.styles["Pilot Provenance"]
                self.assertEqual('Body Text', provenance.base_style.name)
                self.assertEqual(9, provenance.font.size.pt)
                self.assertEqual('526169', str(provenance.font.color.rgb))
                self.assertEqual(12, provenance.paragraph_format.line_spacing.pt)
                self.assertEqual(WD_LINE_SPACING.AT_LEAST, provenance.paragraph_format.line_spacing_rule)
                self.assertEqual(0, provenance.paragraph_format.space_before.pt)
                self.assertEqual(2, provenance.paragraph_format.space_after.pt)
                self.assertTrue(provenance.paragraph_format.keep_together)
                self.assertFalse(provenance.paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Label"].paragraph_format.keep_with_next)
                budget_label = document.styles["Pilot Budget Label"]
                self.assertEqual('Body Text', budget_label.base_style.name)
                self.assertTrue(budget_label.paragraph_format.keep_with_next)
                self.assertEqual(0, budget_label.paragraph_format.space_before.pt)
                self.assertEqual(3, budget_label.paragraph_format.space_after.pt)
                self.assertIsNone(budget_label.paragraph_format.line_spacing)
                self.assertEqual(4, document.styles["Pilot Label"].paragraph_format.space_before.pt)
                self.assertTrue(document.styles["Pilot Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_together)
                self.assertFalse(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_with_next)
                self.assertEqual('Body Text', document.styles["Pilot Responsibility Summary"].base_style.name)
                self.assertTrue(document.styles["Pilot List Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_together)
                self.assertTrue(document.styles["Pilot Repository Lead"].paragraph_format.keep_with_next)
                self.assertFalse(document.styles["Pilot Repository Item"].paragraph_format.keep_with_next)
                for name in ["Pilot Repository Lead", "Pilot Repository Item"]:
                    self.assertTrue(document.styles[name].paragraph_format.keep_together)
                    self.assertEqual('Compact', document.styles[name].base_style.name)
                self.assertFalse(document.styles["Heading 4"].font.italic)
                question = document.styles["Heading 3"]
                self.assertEqual(11.5, question.font.size.pt)
                self.assertTrue(question.font.bold)
                self.assertEqual('000000', str(question.font.color.rgb))
                self.assertEqual(0, document.styles["Body Text"].paragraph_format.space_before)
                for style_name in ("Normal", "Body Text", "First Paragraph", "Compact"):
                    item = document.styles[style_name]
                    self.assertEqual(10.5, item.font.size.pt)
                    if style_name == "Normal":
                        self.assertEqual(1.2, item.paragraph_format.line_spacing)
                        self.assertEqual(WD_LINE_SPACING.MULTIPLE, item.paragraph_format.line_spacing_rule)
                    else:
                        self.assertEqual(15.75, item.paragraph_format.line_spacing.pt)
                        self.assertEqual(WD_LINE_SPACING.AT_LEAST, item.paragraph_format.line_spacing_rule)
                    self.assertEqual(2 if style_name == "Compact" else 4, item.paragraph_format.space_after.pt)
                    self.assertTrue(item.paragraph_format.widow_control)
                for level in range(1, 6):
                    item = document.styles[f"Heading {level}"].paragraph_format
                    self.assertEqual(8 if level >= 4 else 12, item.space_before.pt)
                    self.assertEqual(3 if level >= 4 else 4 if level == 3 else 6, item.space_after.pt)
                    self.assertTrue(item.keep_with_next)
                    self.assertTrue(item.keep_together)
                for section in document.sections:
                    for container in (
                        section.header,
                        section.first_page_header,
                        section.even_page_header,
                    ):
                        self.assertFalse(
                            any(e.tag == qn("w:drawing") for e in container._element.iter())
                        )
            self.assertEqual(references[0], references[1])

    def test_english_uses_same_spacing_without_changing_body_font_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'src/word').mkdir(parents=True)
            shutil.copyfile(ROOT / 'src/layout.css', root / 'src/layout.css')
            shutil.copyfile(ROOT / 'src/word/reference.docx', root / 'src/word/reference.docx')
            font = root / 'font.ttf'; font.write_bytes(b'fixture font asset')
            module.prepare_layout(root, font, 'en')
            d = Document(root / 'src/word/reference.docx')
            for name in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):
                self.assertEqual(1.2, d.styles[name].paragraph_format.line_spacing)
                self.assertEqual(WD_LINE_SPACING.MULTIPLE, d.styles[name].paragraph_format.line_spacing_rule)
                self.assertEqual(10.5, d.styles[name].font.size.pt)
            self.assertEqual('en-GB', d.styles['Normal'].element.rPr.find(qn('w:lang')).get(qn('w:val')))
