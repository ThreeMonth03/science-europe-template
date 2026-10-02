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
    def test_fixed_list_leads_keep_only_the_intro_without_changing_list_xml(self):
        import base64
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from probe_q8_word import IMAGE, RUNNER
        questions = [
            ('q-copyright-ipr', '08-copyright-ipr',
             'The following conditions apply to the reference and non-reference datasets that we reuse:',
             '此計畫再利用的參考及非參考資料集須遵守以下條件：'),
            ('q-share-restrictions', '10-share-restrictions',
             'The dataset has the following identifiers:', '此資料集具有以下識別碼：'),
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
        template = environment(ROOT).from_string(PREFIX + "{% include 'src/questions/10-share-restrictions.html.j2' %}")
        cases = []
        for kind in ['Other', 'OldCommittee']:
            for value in ['', '  ', '<p>Access office.</p>', '<p>Original.</p>' * 50,
                    '<ul><li>Original A.</li><li>Original B.</li></ul>',
                    '<table><tr><td>Original.</td><td>Keep.</td></tr></table>']:
                replies = {parent: IDS['openImmediatelyNoAUuid'], reason: IDS['notOpenLegalReasonsYesAUuid'],
                    auth: IDS['legalReasonsAuthenticatedYesAUuid'], who: IDS['legalReasonsAuthorize'+kind+'AUuid'],
                    path(who, 'legalReasonsAuthorize'+kind+'AUuid', 'legalReasonsAuthorize'+kind+'QUuid'): value}
                html = template.render(repliesMap=replies, output_profile='submission')
                cases.append([html, int(bool(value.strip()))])
        runner = '''import json,sys,subprocess,tempfile,zipfile
from pathlib import Path
p=json.load(sys.stdin);results=[]
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'pilot.lua';f.write_text(p['lua']);out=Path(tmp)/'test.docx'
 for html,count in p['cases']:
  pair=[]
  for text in [html.replace('class="answer-lead"','class="authorization-control"'),html]:
   subprocess.run(['pandoc','--from=html','--to=docx','--lua-filter='+str(f),'-o',str(out)],input=text.encode(),check=True)
   with zipfile.ZipFile(out) as z:pair.append(z.read('word/document.xml').decode())
  results.append([count,pair])
print(json.dumps(results))
'''
        raw = subprocess.check_output(['docker','run','--rm','--network','none','-i',
            '--entrypoint','python',IMAGE,'-c',runner],
            input=json.dumps(dict(cases=cases,lua=(ROOT/'src/word/pilot.lua').read_text())).encode(),timeout=180)
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for count, pair in json.loads(raw):
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
                self.assertIn('A data sharing agreement will be required.', ''.join(newp.itertext()))
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
            dc = dict(project=dict(versions=[dict(name=title, description=description, created_at='')] * count),
                      pkg=dict(name=model, version='2.7.0', organization_id='dsw', km_id='root'),
                      config=dict(service_name='DMP service', service_url='https://example.org/'))
            cases.append(dict(name=name, html=template.render(dc=dc), text=[title, description, model]))
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
