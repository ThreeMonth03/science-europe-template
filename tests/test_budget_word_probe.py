import sys
import json
import subprocess
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_budget_word import allowed_changes,cases,heading_cases,verify_heading_move,short_row_cases,verify_row_xml


class BudgetProbeTests(unittest.TestCase):
    def test_terminal_review_gaps_join_only_the_owned_short_pair_stock435(self):
        import copy
        from probe_budget_word import ROOT, RUNNER
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        call = '  if div.identifier == "q-required-resources" then div = join_q15_terminal_gaps(div) end'
        self.assertEqual(lua.count(call), 1)
        authored = ('<div class="answer-detail"><p>' + 'Keep the original authored paragraph. ' * 120 + '</p>'
                    '<ul><li>Keep the first item.<ul><li>Keep its child.</li></ul></li><li>Keep the second item.</li></ul>'
                    '<table><tr><th>Action</th><th>Evidence</th></tr><tr><td>Keep records.</td><td>0 TWD</td></tr></table>'
                    '<pre><code>A&lt;B&amp;C&gt;D\noriginal.csv</code></pre>'
                    '<p><a href="https://example.org/?a=1&amp;b=2">Original link</a></p></div>')

        def gap(fact, text, prefix='Information not provided:', status='missing', extra=''):
            return ('<div class="q15-terminal-gap" data-fact-id="' + fact + '" data-status="' + status + '"' + extra + '>'
                    '<p class="data-gap"><strong>' + prefix + '</strong> ' + text + '</p></div>')

        def question(left, right, qid='q-required-resources', between='', ending='', outside=''):
            return ('<div id="' + qid + '"><h3>15. Resources?</h3><div class="answer">' + authored +
                    left + between + right + ending + '</div>' + outside + '</div>')

        left = gap('repository-charges', 'whether repository service charges will be incurred.')
        right = gap('resources-costing', 'the financial and time resources budgeted for data management and FAIR data.')
        base = question(left, right)
        zh_left = gap('repository-charges', '是否需支付資料儲存庫服務費。', '尚待補充：')
        zh_right = gap('resources-costing', '資料管理及落實 FAIR 原則所編列的經費與時間。', '尚待補充：')
        zh_plain = question(zh_left.replace('<strong>', '').replace('</strong>', ''),
                            zh_right.replace('<strong>', '').replace('</strong>', ''))
        cases = [('english', base, True), ('chinese', question(zh_left, zh_right), True),
                 ('chinese-plain', zh_plain, True),
                 ('wrong-question', question(left, right, qid='q-other'), False),
                 ('missing-first-marker', base.replace('class="q15-terminal-gap"', 'class="original"', 1), False),
                 ('missing-last-marker', question(left, right.replace('class="q15-terminal-gap"', 'class="original"')), False),
                 ('known-first-status', question(gap('repository-charges', 'Known fees.', status='complete'), right), False),
                 ('known-last-status', question(left, gap('resources-costing', 'Known budget.', status='complete')), False),
                 ('first-extra-attribute', question(gap('repository-charges', 'Pending fees.', extra=' data-extra="original"'), right), False),
                 ('last-extra-attribute', question(left, gap('resources-costing', 'Pending budget.', extra=' data-extra="original"')), False),
                 ('extra-class', base.replace('class="q15-terminal-gap"', 'class="q15-terminal-gap original"', 1), False),
                 ('reversed-order', question(right, left), False),
                 ('intervening-author', question(left, right, between='<p>Keep this independent authored answer.</p>'), False),
                 ('nested-pair', question('<div class="answer-detail">' + left, right + '</div>'), False),
                 ('long-ascii', question(left, gap('resources-costing', 'x' * 241)), False),
                 ('long-chinese', question(zh_left, gap('resources-costing', '中' * 121, '尚待補充：')), False),
                 ('inline-link', question(left, gap('resources-costing', '<a href="https://example.org/budget">Original budget</a>')), False),
                 ('inline-code', question(left, gap('resources-costing', '<code>0 TWD</code>')), False),
                 ('emphasized-prefix', question(left, right.replace('<strong>', '<em>').replace('</strong>', '</em>')), False),
                 ('two-paragraphs', question(left, right.replace('</p>', '</p><p>Keep this second paragraph.</p>')), False),
                 ('next-answer-block', question(left, right, ending='<p>Keep this next answer.</p>'), False),
                 ('next-question', question(left, right, outside='<h3>16. Original next question?</h3>'), False)]
        self.assertEqual(len(cases), 22)
        self.assertEqual(len({name for name, _, _ in cases}), len(cases))
        html = ''.join('<div id="case-' + name + '">' + body + '</div>' for name, body, _ in cases)
        runner = ('import contextlib,io,json,sys\np=json.load(sys.stdin);results=[]\n'
                  'for source in p["sources"]:\n'
                  ' sys.stdin=io.StringIO(json.dumps(dict(lua=source,html=p["html"])))\n'
                  ' out=io.StringIO()\n'
                  ' with contextlib.redirect_stdout(out): exec(' + repr(RUNNER) + ',{})\n'
                  ' results.append(json.loads(out.getvalue()))\n'
                  'print(json.dumps(results))')
        raw = subprocess.check_output(
            ['docker', 'run', '--rm', '--pull=never', '--network=none', '--cap-drop=ALL',
             '--security-opt=no-new-privileges', '--log-driver=none', '-i', '--entrypoint', 'python', image, '-c', runner],
            input=json.dumps(dict(html=html, sources=[lua.replace(call, ''), lua])).encode(), timeout=180)
        before, after = json.loads(raw)
        self.assertEqual(before['meta'], after['meta'])
        self.assertEqual(len(before['blocks']), len(cases))
        self.assertEqual(len(after['blocks']), len(cases))
        for (name, _, selected), old, actual in zip(cases, before['blocks'], after['blocks']):
            with self.subTest(case=name):
                self.assertEqual(old['c'][0][0], 'case-' + name)
                if not selected:
                    self.assertEqual(actual, old, 'Rejected inputs must retain the entire AST')
                    continue
                expected = copy.deepcopy(old)
                answer = expected['c'][1][0]['c'][1][1]
                first, last = answer['c'][1][-2:]
                self.assertEqual([block['t'] for block in (first, last)], ['Div', 'Div'])
                self.assertEqual([block['c'][0] for block in (first, last)],
                                 [['', ['q15-terminal-gap'], [['fact-id', fact], ['status', 'missing']]]
                                  for fact in ('repository-charges', 'resources-costing')])
                left_para, right_para = first['c'][1][0], last['c'][1][0]
                self.assertEqual([p['t'] for p in (left_para, right_para)], ['Para', 'Para'])
                if name == 'chinese-plain':
                    self.assertTrue(all(node['t'] in ('Str', 'Space', 'SoftBreak')
                                        for p in (left_para, right_para) for node in p['c']))
                else:
                    self.assertEqual([p['c'][0]['t'] for p in (left_para, right_para)], ['Strong', 'Strong'])
                separator = [{'t': 'Space'}] if name == 'english' else []
                first['c'][1] = [{'t': 'Para', 'c': left_para['c'] + separator + right_para['c']}]
                answer['c'][1].pop()
                self.assertEqual(actual, expected, 'Only the two owned prompt paragraphs may be concatenated')
                if name == 'chinese-plain':
                    joined = actual['c'][1][0]['c'][1][1]['c'][1][-1]['c'][1][0]['c']
                    self.assertNotIn('Strong', [node['t'] for node in joined])
                    self.assertEqual(''.join(node['c'] for node in joined if node['t'] == 'Str').count('尚待補充：'), 2)

    def test_authored_resource_rows_keep_only_bounded_owned_cells(self):
        import copy
        from probe_budget_word import ROOT, IMAGE, RUNNER
        source = (ROOT/'src/word/short-tables.lua').read_text()
        call = 'return keep_authored_resource_rows(div), false'
        self.assertEqual(source.count(call), 1)
        marker = '<!--DSW:SE:authored-resource-row:v1-->'
        reuse_call = 'keep_authored_reuse_rows(keep_authored_authorization_rows(div))'
        reuse_marker = '<!--DSW:SE:authored-reuse-row:v1-->'
        self.assertEqual(source.count(reuse_call), 1)
        data = ''.join('<tr><td>ROW-%02d</td><td>10</td></tr>' % n for n in range(1, 49))
        def fixture(kind='purpose', rows=data, metadata=2):
            meta = ('<table class="word-rich-funding-metadata" data-item-id="cost-1">' if metadata == 2 else '<table class="resource-table word-rich-budget-metadata">')
            meta += '<thead><tr><th>Resource</th><th>Budget</th>'+('<th>Funding</th>' if metadata == 3 else '')+'</tr></thead><tbody><tr data-item-id="cost-1"><td><p><strong>Resource 1</strong></p></td><td>0 TWD</td>'+('<td>Institute.</td>' if metadata == 3 else '')+'</tr></tbody></table>'
            table = '<table><thead><tr><th>Record</th><th>Retention</th></tr></thead><tbody>'+rows+'</tbody></table>'
            attrs = ' data-fact-id="resource-justification" data-status="complete"' if kind == 'purpose' else ''
            return '<div id="q-required-resources"><div class="answer"><h4 class="word-budget-heading">Budget</h4><div class="project-resources">'+meta+'<div class="word-rich-resource-'+kind+'" data-item-id="cost-1"><div class="answer-detail"'+attrs+'>'+table+'</div></div></div></div></div>'
        base = fixture()
        mixed = ''.join('<tr><td>'+value+'</td><td>10</td></tr>' for value in ['Short.', '中'*40, '中'*41, 'X'*41, 'long word '*12, 'A<br>B', '<ul><li>Keep list.</li></ul>', '<img src="unused.png" alt="Keep">'])
        cases = [('purpose', base, 48), ('funding', fixture('funding'), 48), ('three-cell-metadata', fixture(metadata=3), 48), ('mixed', fixture(rows=mixed), 2)]
        cases += [(name, value, 0) for name,value in [
            ('other-question', base.replace('q-required-resources', 'q-other')),
            ('unowned-project', base.replace('project-resources', 'unowned')),
            ('unowned-wrapper', base.replace('word-rich-resource-purpose', 'unowned')),
            ('wrong-id', base.replace('word-rich-resource-purpose" data-item-id="cost-1', 'word-rich-resource-purpose" data-item-id="cost-2')),
            ('empty-id', base.replace('cost-1', '')),
            ('no-metadata', base.replace('word-rich-funding-metadata', 'unowned-table')),
            ('nested-detail', base.replace('<table><thead><tr><th>Record', '<div><table><thead><tr><th>Record').replace('</table></div></div>', '</table></div></div></div>')),
            ('unknown-detail-attr', base.replace('data-status="complete"', 'data-status="complete" data-extra="unknown"')),
            ('wrong-fact', base.replace('resource-justification', 'unowned-fact')),
            ('empty-cell', fixture(rows='<tr><td></td><td>10</td></tr>')),
            ('merged', fixture(rows='<tr><td colspan="2">Keep merged.</td></tr>')),
            ('two-paragraphs', fixture(rows='<tr><td><p>First.</p><p>Second.</p></td><td>10</td></tr>')),
            ('styled', fixture(rows='<tr><td><div custom-style="Other"><p>Keep.</p></div></td><td>10</td></tr>')),
            ('nested-table', fixture(rows='<tr><td><table><tr><td>Keep nested.</td></tr></table></td><td>10</td></tr>')),
        ]]
        def reuse(rows=data, records=1):
            table = '<table><thead><tr><th>Action</th><th>Evidence</th></tr></thead><tbody>'+rows+'</tbody></table>'
            item = '<li><div>Dataset 1</div><p class="answer-lead">Restrictions apply:</p><div class="answer-detail"><p>Original terms.</p>'+table+'</div></li>'
            return '<div id="q-copyright-ipr"><div class="answer"><div class="answer-lead"><p>Conditions:</p></div><ul>'+item*records+'</ul></div></div>'
        reuse_base = reuse()
        cases += [('reuse-single', reuse_base, 48), ('reuse-multiple', reuse(records=2), 96),
                  ('reuse-mixed', reuse(rows=mixed), 2),
                  ('reuse-neutral-label', reuse_base.replace('Dataset 1', '<span class="dataset-label" data-list-kind="reference" data-list-index="1">Reference dataset 1</span>'), 48),
                  ('reuse-literal-marker', reuse(rows='<tr><td>&lt;!--DSW:SE:authored-reuse-row:v1--&gt;</td><td>Evidence.</td></tr>'), 1)]
        cases += [('reuse-'+name, value, 0) for name,value in [
            ('other-question', reuse_base.replace('q-copyright-ipr', 'q-other')),
            ('unowned-answer', reuse_base.replace('class="answer"', 'class="unowned"')),
            ('unowned-detail', reuse_base.replace('class="answer-detail"', 'class="unowned"')),
            ('extra-detail-attr', reuse_base.replace('class="answer-detail"', 'class="answer-detail" data-extra="unknown"')),
            ('unowned-label', reuse_base.replace('<div>Dataset 1</div>', '<div class="original">Dataset 1</div>')),
            ('permission-list', reuse_base.replace('<p class="answer-lead">Restrictions apply:</p>', '<ul><li>Original permission.</li></ul>')),
            ('extra-item-block', reuse_base.replace('</div></li>', '</div><p>Original tail.</p></li>')),
            ('nested-table', reuse_base.replace('<table><thead>', '<div><table><thead>').replace('</table></div></li>', '</table></div></div></li>')),
            ('caption', reuse_base.replace('<table><thead>', '<table><caption>Original caption.</caption><thead>')),
            ('table-attr', reuse_base.replace('<table><thead>', '<table class="original"><thead>')),
            ('empty-cell', reuse(rows='<tr><td></td><td>Evidence.</td></tr>')),
            ('merged', reuse(rows='<tr><td colspan="2">Keep merged.</td></tr>')),
            ('two-paragraphs', reuse(rows='<tr><td><p>First.</p><p>Second.</p></td><td>Evidence.</td></tr>')),
            ('styled-cell', reuse(rows='<tr><td><div custom-style="Other"><p>Keep.</p></div></td><td>Evidence.</td></tr>')),
            ('code-cell', reuse(rows='<tr><td><code>Original.csv</code></td><td>Evidence.</td></tr>')),
            ('nested-cell-table', reuse(rows='<tr><td><table><tr><td>Nested.</td></tr></table></td><td>Evidence.</td></tr>')),
            ('reason-detail', reuse_base.replace('class="answer"', 'class="answer-detail"')),
            ('no-table', reuse(rows='').replace('<table><thead><tr><th>Action</th><th>Evidence</th></tr></thead><tbody></tbody></table>', '')),
        ]]
        # Exercise the real filter order in one offline container; compare the
        # complete AST, allowing only one generated marker per eligible row.
        native = RUNNER.replace('f.write_text(p["lua"])', 'f.write_text(p["lua"]);g=Path(tmp)/"before.lua";g.write_text(p["pilot"])').replace('"--lua-filter="+str(f)', '"--lua-filter="+str(g),"--lua-filter="+str(f)')
        runner = 'import contextlib,io,json,sys\np=json.load(sys.stdin)\nresults=[]\nfor source in p["sources"]:\n sys.stdin=io.StringIO(json.dumps(dict(html=p["html"],lua=source,pilot=p["pilot"])))\n out=io.StringIO()\n with contextlib.redirect_stdout(out): exec('+repr(native)+',{})\n results.append(json.loads(out.getvalue()))\nprint(json.dumps(results))'
        payload = dict(html=''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_ in cases), pilot=(ROOT/'src/word/pilot.lua').read_text(), sources=[source.replace(call, 'return div, false').replace(reuse_call, 'keep_authored_authorization_rows(div)'), source])
        raw = subprocess.check_output(['docker','run','--rm','--network','none','--log-driver','none','-i','--entrypoint','python',IMAGE,'-c',runner], input=json.dumps(payload).encode(), timeout=180)
        results = [{b['c'][0][0]:b for b in r['blocks']} for r in json.loads(raw)]
        def remove_markers(node):
            if isinstance(node, dict): return sum(remove_markers(value) for value in node.values())
            if isinstance(node, list):
                kept = [v for v in node if v not in [{'t':'RawBlock','c':['openxml',m]} for m in (marker,reuse_marker)]]
                count = len(node)-len(kept); node[:] = kept
                return count+sum(remove_markers(v) for v in node)
            return 0
        for name,_,count in cases:
            with self.subTest(case=name):
                before, after = [r['case-'+name] for r in results]
                cleaned = copy.deepcopy(after)
                self.assertEqual(remove_markers(cleaned), count)
                self.assertEqual(cleaned, before, 'All authored rows, header, paragraph styles and separator keeps must remain exact')

    def test_authored_resource_row_xml_contract_is_exact_and_fail_closed(self):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
        root = Path(__file__).resolve().parents[1]
        marker = '<!--DSW:SE:authored-resource-row:v1-->'
        cell = lambda text: '<w:tc><w:tcPr /><w:p><w:pPr><w:pStyle w:val="Compact" /></w:pPr><w:r><w:t>'+text+'</w:t></w:r></w:p></w:tc>'
        row = cell('ROW-01').replace('<w:tcPr />', '<w:tcPr />'+marker, 1)+cell('10')
        header = '<w:tr><w:trPr><w:tblHeader/></w:trPr>'+cell('Record')+cell('Retention')+'</w:tr>'
        before = '<w:document><w:body><w:tbl>'+header+'<w:tr>'+row+'</w:tr></w:tbl></w:body></w:document>'
        expected = before.replace(marker, '').replace('<w:tr>'+row.replace(marker, ''), '<w:tr><w:trPr><w:cantSplit/></w:trPr>'+row.replace(marker, ''))
        malformed = [before.replace(marker, marker*2), before.replace('</w:tr></w:tbl>', cell('Extra')+'</w:tr></w:tbl>'), before.replace('<w:tcPr />', '<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'), before.replace('<w:tcPr />', '<w:tcPr><w:vMerge/></w:tcPr>'), before.replace(marker+'<w:p>', marker+'<w:p><w:p/>'), before.replace(marker+'<w:p>', '<w:p>'+marker), before.replace('<w:tr>'+row, '<w:tr><w:trPr/>'+row), before.replace('<w:body>', '<w:body>'+marker)]
        for escape in (False, True):
            template = Environment(loader=FileSystemLoader(root),undefined=StrictUndefined,autoescape=escape).get_template('src/word/short-tables.xml')
            for current in (marker, '<!--DSW:SE:authored-reuse-row:v1-->'):
                self.assertEqual(template.render(content=before.replace(marker, current)), expected)
                literal = '&lt;!--DSW:SE:authored-reuse-row:v1--&gt;'
                self.assertEqual(template.render(content=before.replace(marker,current).replace('ROW-01',literal)), expected.replace('ROW-01',literal))
                self.assertEqual(template.render(content=before.replace(marker, '')), before.replace(marker, ''))
                for value in malformed:
                    with self.subTest(autoescape=escape, marker=current, source=value):
                        with self.assertRaises(UndefinedError): template.render(content=value.replace(marker,current))

    def test_funding_metadata_ast_is_scoped_and_preserves_authored_blocks(self):
        import copy
        from probe_budget_word import ROOT, IMAGE, RUNNER
        lua = (ROOT/'src/word/pilot.lua').read_text()
        call = '  if div.identifier == "q-required-resources" then div = keep_funding_metadata_leads(div) end'
        guard = 'if div.classes:includes("word-rich-resource-funding") then'
        self.assertEqual(lua.count(call), 1); self.assertEqual(lua.count(guard), 1)
        disabled = lua.replace(call, '').replace(guard, 'if false then')
        marker = '<!--DSW:SE:funding-metadata-row:v1-->'
        table = '<table><thead><tr><th>Funding line</th><th>Amount (TWD)</th></tr></thead><tbody><tr><td>FUND-01</td><td>10</td></tr></tbody></table>'
        def fixture(kind='funding', amount='<p>0 TWD</p>', body=None):
            body = '<div class="answer-detail"><p>Keep original '+kind+'.</p>'+table+'</div>' if body is None else body
            if kind == 'funding' and body: body = '<div class="answer-lead"><p><strong>Funding source</strong></p></div>'+body
            return '<div id="q-required-resources"><div class="answer"><h4 class="word-budget-heading">Budget</h4><div class="project-resources"><table class="word-rich-funding-metadata" data-item-id="cost-1"><thead><tr><th>Resource and purpose</th><th>Budget</th></tr></thead><tbody><tr><td><p><strong>Resource 1</strong></p></td><td>'+amount+'</td></tr></tbody></table><div class="word-rich-resource-'+kind+'" data-item-id="cost-1">'+body+'</div></div></div></div>'
        base = fixture()
        rows = [
            ('funding', base, True, True), ('purpose', fixture('purpose'), True, True),
            ('empty-budget', fixture(amount=''), True, True),
            ('other-question', base.replace('q-required-resources', 'q-other'), False, False),
            ('unowned-project', base.replace('project-resources', 'authored-content'), False, False),
            ('unowned-table', base.replace('word-rich-funding-metadata', 'authored-table'), False, False),
            ('no-id', base.replace(' data-item-id="cost-1"', ''), False, False),
            ('empty-id', base.replace('data-item-id="cost-1"', 'data-item-id=""'), False, False),
            ('wrong-id', base.replace('class="word-rich-resource-funding" data-item-id="cost-1"', 'class="word-rich-resource-funding" data-item-id="cost-2"'), False, False),
            ('empty-body', fixture(body=''), False, False),
            ('complex-metadata', fixture(amount='<ul><li>Keep this list.</li></ul>'), True, False),
            ('image-metadata', fixture(amount='<p><img src="unused.png" alt="Keep"></p>'), True, False),
            ('long-title', base.replace('Resource 1</strong>', 'X'*161+'</strong>'), True, False),
            ('long-budget', fixture(amount='<p>'+'X'*81+'</p>'), True, False),
        ]
        html = ''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_,_ in rows)
        # One container, two batched Pandoc ASTs; no native artifact rendering.
        runner = 'import contextlib,io,json,sys\npayload=json.load(sys.stdin)\nresults=[]\nfor source in payload["sources"]:\n sys.stdin=io.StringIO(json.dumps(dict(html=payload["html"],lua=source)))\n output=io.StringIO()\n with contextlib.redirect_stdout(output): exec('+repr(RUNNER)+',{})\n results.append(json.loads(output.getvalue()))\nprint(json.dumps(results))'
        raw = subprocess.check_output(['docker','run','--rm','--network','none','--log-driver','none','-i','--entrypoint','python',IMAGE,'-c',runner], input=json.dumps(dict(html=html,sources=[disabled,lua])).encode(), timeout=180)
        results = [{b['c'][0][0]:b for b in result['blocks']} for result in json.loads(raw)]
        def walk(node):
            if isinstance(node, dict):
                yield node; yield from walk(node.get('c'))
            elif isinstance(node, list):
                for child in node: yield from walk(child)
        def attach_last(blocks):
            for index in range(len(blocks)-1, -1, -1):
                block = blocks[index]
                if block['t'] in ('Para', 'Plain'):
                    blocks[index] = {'t':'Div','c':[['',[],[['custom-style','Pilot Lead']]],[{'t':'Para','c':block['c']}]]}; return True
                if block['t'] == 'Div' and attach_last(block['c'][1]): return True
            return False
        def separator(keep):
            return {'t':'RawBlock','c':['openxml','<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/><w:keepNext w:val="'+str(keep)+'"/><w:snapToGrid w:val="0"/><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr></w:p>']}
        for name,_,resized,kept in rows:
            with self.subTest(case=name):
                before, after = [result['case-'+name] for result in results]
                expected = copy.deepcopy(before)
                metadata = [n for n in walk(expected) if n['t']=='Table' and 'word-rich-funding-metadata' in n['c'][0][1]]
                for node in metadata:
                    self.assertEqual(len(node['c'][2]), 2)
                    if name not in ('other-question', 'unowned-project'):
                        self.assertEqual(node['c'][3][1][0][1][0][3], 2, 'Owned budget caption spans exactly two columns')
                        self.assertEqual([n['c'] for n in walk(node['c'][3][1][0][1][0][4]) if n['t']=='Str'], ['Budget'])
                    if resized: node['c'][2] = [[{'t':'AlignLeft'},{'t':'ColWidth','c':0.75}],[{'t':'AlignLeft'},{'t':'ColWidth','c':0.25}]]
                    cells = node['c'][4][0][3][0][1]
                    if kept:
                        for cell in cells:
                            if not attach_last(cell[4]): cell[4].append({'t':'RawBlock','c':['openxml','<w:p><w:pPr><w:keepNext/></w:pPr></w:p>']})
                        cells[0][4].insert(0, {'t':'RawBlock','c':['openxml',marker]})
                for node in list(walk(expected)):
                    if node.get('t')=='Div' and 'word-rich-resource-funding' in node['c'][0][1]:
                        node['c'][1] = [separator(1)]+node['c'][1]+[separator(0)]
                self.assertEqual(after, expected, 'Only bounded metadata keeps/widths and owned funding separators may change')
                self.assertEqual(sum(n['t']=='RawBlock' and n['c']==['openxml',marker] for n in walk(after)), int(kept))

    def test_funding_metadata_xml_contract_is_independent_and_fail_closed(self):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
        root = Path(__file__).resolve().parents[1]
        templates = [Environment(loader=FileSystemLoader(root),undefined=StrictUndefined,autoescape=escape).get_template('src/word/short-tables.xml') for escape in (False, True)]
        marker = '<!--DSW:SE:funding-metadata-row:v1-->'
        old = '<!--DSW:SE:budget-row:v1-->'
        cell = lambda text: '<w:tc><w:tcPr /><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:tc>'
        row = cell('Resource &amp; 1').replace('<w:tcPr />', '<w:tcPr />'+marker, 1)+cell('0 TWD')
        before = '<w:document><w:body><w:tbl><w:tr>'+row+'</w:tr></w:tbl></w:body></w:document>'
        expected = before.replace(marker, '').replace('<w:tr>', '<w:tr><w:trPr><w:cantSplit/></w:trPr>', 1)
        for template in templates:
            self.assertEqual(template.render(content=before), expected)
            self.assertEqual(template.render(content=before.replace(marker, '')), before.replace(marker, ''))
            three = before.replace('</w:tr>', cell('Funder')+'</w:tr>')
            old_three = three.replace(marker, old)
            self.assertEqual(template.render(content=old_three), old_three.replace(old, '').replace('<w:tr>', '<w:tr><w:trPr><w:cantSplit/></w:trPr>', 1))
            malformed = [
                three, before.replace('</w:tc>'+cell('0 TWD'), '</w:tc>'),
                before.replace('<w:tcPr />', '<w:tcPr><w:vMerge/></w:tcPr>', 1),
                before.replace('<w:tcPr />', '<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>', 1),
                before.replace(marker, marker*2), before.replace(marker, old),
                before.replace(marker, '').replace('<w:body>', '<w:body>'+marker),
                before.replace('</w:tc>', '<w:tbl><w:tr>'+cell('Nested')+'</w:tr></w:tbl></w:tc>', 1),
                before.replace('<w:tr>', '<w:tr><w:trPr><w:tblHeader/></w:trPr>', 1),
            ]
            for source in malformed:
                with self.subTest(source=source, autoescape=template.environment.autoescape):
                    with self.assertRaises(UndefinedError): template.render(content=source)

    def test_current_rich_metadata_keeps_and_separators_are_owned_and_exact(self):
        import copy
        from probe_budget_word import ROOT, IMAGE, RUNNER, ROW_CALL, ROW_MARKER, fixture
        lua = (ROOT/'src/word/pilot.lua').read_text()
        call = 'keep_rich_resource_leads(align_budget_cells('+ROW_CALL+'))'
        guard = 'if div.classes:includes("word-rich-resource-purpose") then'
        self.assertEqual(lua.count(call), 1)
        self.assertEqual(lua.count(guard), 1)
        disabled = lua.replace(call, 'align_budget_cells('+ROW_CALL+')').replace(guard, 'if false then')
        table = '<table><thead><tr><th>Record</th><th>Retention</th></tr></thead><tbody><tr><td>ROW-01</td><td>10</td></tr></tbody></table>'
        purpose = '<p>Keep <code>Cost.csv</code> and <a href="https://example.org/qa?a=1&amp;b=2">source</a>.</p>'+table
        base = fixture(rows=1).replace('<div class="answer-detail"><p>Purpose.</p></div><p>Findability.</p>', '')
        base = base.replace('class="resource-table"', 'class="resource-table word-rich-budget-metadata"')
        def owned(content):
            return base.replace('</table>', '</table><div class="word-rich-resource-purpose">'+content+'</div>')
        full = owned(purpose)
        rows = [
            ('filled', full, True, True),
            ('empty-metadata', full.replace('0 TWD', '').replace('Institute.', ''), True, True),
            ('terminal-table', owned(table), True, True),
            ('unbounded-no-marker', full.replace('Institute.', 'F'*161), False, True),
            ('other-question', full.replace('q-required-resources', 'q-other'), False, True),
            ('unowned-project', full.replace('project-resources', 'authored-content'), False, True),
            ('unowned-table', full.replace('resource-table word-rich-budget-metadata', 'resource-table'), False, True),
            ('ordinary-purpose', full.replace('word-rich-resource-purpose', 'answer-detail'), True, False),
        ]
        html = ''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_,_ in rows)
        results = []
        for source in (disabled, lua):
            raw = subprocess.check_output(['docker','run','--rm','--network','none','--log-driver','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],
                input=json.dumps(dict(html=html, lua=source)).encode(), timeout=180)
            results.append({b['c'][0][0]: b for b in json.loads(raw)['blocks']})
        def walk(node):
            if isinstance(node, dict):
                yield node
                yield from walk(node.get('c'))
            elif isinstance(node, list):
                for value in node:
                    yield from walk(value)
        def attach_last(blocks):
            for index in range(len(blocks)-1, -1, -1):
                block = blocks[index]
                if block['t'] in ('Para', 'Plain'):
                    blocks[index] = {'t':'Div','c':[['',[],[['custom-style','Pilot Lead']]],[{'t':'Para','c':block['c']}]]}
                    return True
                if block['t'] == 'Div' and attach_last(block['c'][1]):
                    return True
            return False
        def separator(keep):
            return {'t':'RawBlock','c':['openxml','<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/><w:keepNext w:val="'+str(keep)+'"/><w:snapToGrid w:val="0"/><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr></w:p>']}
        for name,_,kept,separated in rows:
            with self.subTest(case=name):
                before, after = [result['case-'+name] for result in results]
                expected = copy.deepcopy(before)
                metadata = [node for node in walk(expected) if node['t'] == 'Table' and 'word-rich-budget-metadata' in node['c'][0][1]]
                purposes = [node for node in walk(expected) if node['t'] == 'Div' and 'word-rich-resource-purpose' in node['c'][0][1]]
                self.assertEqual(len(metadata), 0 if name == 'unowned-table' else 1)
                self.assertEqual(len(purposes), int(separated))
                for node in metadata:
                    cells = node['c'][4][0][3][0][1]
                    markers = [n for n in walk(cells[0][4]) if n['t'] == 'RawBlock' and n['c'] == ['openxml', ROW_MARKER]]
                    self.assertEqual(len(markers), int(kept))
                    if kept:
                        for cell in cells:
                            if not attach_last(cell[4]):
                                cell[4].append({'t':'RawBlock','c':['openxml','<w:p><w:pPr><w:keepNext/></w:pPr></w:p>']})
                for node in purposes:
                    node['c'][1] = [separator(1)]+node['c'][1]+[separator(0)]
                self.assertEqual(after, expected, 'Only owned Pilot Lead wrappers and exact beginning/terminal separators may change')

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

    def test_current_budget_label_override_is_marked_first_paragraph_only(self):
        from jinja2 import Environment,FileSystemLoader,StrictUndefined
        from probe_budget_word import ROW_MARKER
        root=Path(__file__).resolve().parents[1]
        history='<!--DSW:SE:history-row:v1-->'
        style='<w:pPr><w:pStyle w:val="PilotBudgetLabel" /></w:pPr>'
        paragraph=lambda value,pr='': '<w:p>'+pr+'<w:r><w:t>'+value+'</w:t></w:r></w:p>'
        cell=lambda value: '<w:tc><w:tcPr />'+value+'</w:tc>'
        def row(marker=ROW_MARKER,first=None,header=False):
            first=paragraph('Resource &amp; 1',style)+paragraph('Original purpose.') if first is None else first
            return '<w:tr>'+('<w:trPr><w:tblHeader/></w:trPr>' if header else '')+cell(marker+first)+cell(paragraph('0 TWD'))+cell(paragraph('Institute.'))+'</w:tr>'
        current=row(); historical=row(history)
        controls=[row('',header=True),row(''),row('',paragraph('Long purpose. '*60,style)),
                  row(first=paragraph('Original first.')+paragraph('Later label.',style)),
                  row(first=paragraph('Different style.',style.replace('PilotBudgetLabel','PilotLabel'))),
                  row(header=True)]
        start='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>'
        before=start+current*8+historical+''.join(controls)+'</w:tbl></w:body></w:document>'
        expected_current=current.replace(ROW_MARKER,'').replace('<w:tr>','<w:tr><w:trPr><w:cantSplit/></w:trPr>',1).replace('<w:pStyle w:val="PilotBudgetLabel" />','<w:pStyle w:val="PilotBudgetLabel" /><w:keepNext w:val="0"/>',1)
        def old_output(value):
            if ROW_MARKER not in value and history not in value:return value
            value=value.replace(ROW_MARKER,'').replace(history,'')
            return value.replace('</w:trPr>','<w:cantSplit/></w:trPr>',1) if '<w:trPr>' in value else value.replace('<w:tr>','<w:tr><w:trPr><w:cantSplit/></w:trPr>',1)
        expected=start+expected_current*8+old_output(historical)+''.join(old_output(value) for value in controls)+'</w:tbl></w:body></w:document>'
        for escape in (False,True):
            template=Environment(loader=FileSystemLoader(root),undefined=StrictUndefined,autoescape=escape).get_template('src/word/short-tables.xml')
            self.assertEqual(template.render(content=before),expected)
        self.assertEqual(expected.count('<w:keepNext w:val="0"/>'),8)
        verify_row_xml(before,expected,12,current_budget_labels=True)
        with self.assertRaises(AssertionError): verify_row_xml(before,expected,12)
        historic_before=start+historical+'</w:tbl></w:body></w:document>'
        historic_after=start+old_output(historical)+'</w:tbl></w:body></w:document>'
        verify_row_xml(historic_before,historic_after,1,current_budget_labels=True)
        verify_row_xml(historic_before.replace(history,''),historic_after,1)
        tail_before,tail_after=self.tail_xml_pair()
        tail_before=tail_before.replace('<w:gridSpan w:val="3"/>','<w:gridSpan w:val="3" />')
        tail_after=tail_after.replace('<w:gridSpan w:val="3"/>','<w:gridSpan w:val="3" />')
        mixed_before=before.replace('<w:body>','<w:body>'+tail_before.split('<w:body>',1)[1].split('</w:body>',1)[0])
        mixed_after=expected.replace('<w:body>','<w:body>'+tail_after.split('<w:body>',1)[1].split('</w:body>',1)[0])
        # The prior tail capture makes content Markup under autoescape. Only
        # the fixed XML replacement may be safe, never the authored payload.
        for escape in (False,True):
            template=Environment(loader=FileSystemLoader(root),undefined=StrictUndefined,autoescape=escape).get_template('src/word/short-tables.xml')
            self.assertEqual(template.render(content=mixed_before),mixed_after)
        verify_row_xml(mixed_before,mixed_after,12,current_tail=True,current_budget_labels=True)

    def test_current_budget_label_oracle_rejects_other_keeps_and_content_changes(self):
        from probe_budget_word import ROW_MARKER
        start='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:tcPr />'
        label='<w:p><w:pPr><w:pStyle w:val="PilotBudgetLabel" /></w:pPr><w:r><w:t>Resource 1</w:t></w:r></w:p>'
        rest='<w:p><w:r><w:t>Original purpose.</w:t></w:r></w:p></w:tc><w:tc><w:tcPr /><w:p><w:r><w:t>0 TWD</w:t></w:r></w:p></w:tc><w:tc><w:tcPr /><w:p><w:r><w:t>Institute.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
        before=start+ROW_MARKER+label+rest
        after=(start+label+rest).replace('<w:tr>','<w:tr><w:trPr><w:cantSplit/></w:trPr>',1).replace('<w:pStyle w:val="PilotBudgetLabel" />','<w:pStyle w:val="PilotBudgetLabel" /><w:keepNext w:val="0"/>',1)
        verify_row_xml(before,after,1,current_budget_labels=True)
        for changed in [after.replace('0 TWD','5000 TWD'),after.replace('PilotBudgetLabel','PilotLabel'),
                        after.replace('<w:keepNext w:val="0"/>',''),after.replace('w:val="0"','w:val="1"'),
                        after.replace('<w:keepNext w:val="0"/>','<w:keepNext w:val="0"/>'*2),
                        after.replace('<w:p><w:r><w:t>Original purpose.','<w:p><w:pPr><w:keepNext w:val="0"/></w:pPr><w:r><w:t>Original purpose.'),
                        after.replace('<w:cantSplit/>','')]:
            with self.subTest(changed=changed):
                with self.assertRaises(AssertionError): verify_row_xml(before,changed,1,current_budget_labels=True)
        with self.assertRaises(AssertionError): verify_row_xml(before.replace(ROW_MARKER,''),after,1,current_budget_labels=True)
        with self.assertRaises(AssertionError): verify_row_xml(before.replace(ROW_MARKER,'<!--DSW:SE:history-row:v1-->'),after,1,current_budget_labels=True)

    def test_bounded_budget_next_row_xml_keeps_only_owned_nonfinal_paragraphs(self):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
        from lxml import etree as E
        marker = '<!--DSW:SE:bounded-budget-next-row:v1-->'
        old = '<!--DSW:SE:budget-row:v1-->'
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraph = lambda text, style='': '<w:p>'+('<w:pPr><w:pStyle w:val="'+style+'" /></w:pPr>' if style else '')+'<w:r><w:t>'+text+'</w:t></w:r></w:p>'
        cell = lambda text: '<w:tc><w:tcPr />'+text+'</w:tc>'
        row = '<w:tr>'+cell(marker+paragraph('Resource &amp; 1', 'PilotBudgetLabel')+paragraph('Original purpose.'))+cell(paragraph('0 TWD', 'BodyText'))+cell(paragraph('Institute.'))+'</w:tr>'
        last = row.replace(marker, old).replace('Resource &amp; 1', 'Resource 2')
        start = '<w:document xmlns:w="'+ns['w']+'"><w:body><w:tbl>'
        end = '</w:tbl>'+paragraph('Later content.')+'</w:body></w:document>'
        for escape in (False, True):
            template = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]), undefined=StrictUndefined, autoescape=escape).get_template('src/word/short-tables.xml')
            for count in (1, 2, 3):
                before = start+row*(count-1)+last+end
                after = template.render(content=before)
                root = E.fromstring(after.encode())
                rows = root.findall('.//w:tr', ns)
                self.assertEqual(len(rows), count)
                self.assertEqual(len(root.findall('.//w:cantSplit', ns)), count)
                for index, current in enumerate(rows):
                    paragraphs = current.findall('.//w:p', ns)
                    if index < count-1:
                        self.assertEqual(len(paragraphs), 4)
                        for p in paragraphs: self.assertEqual(E.tostring(p.find('w:pPr/w:keepNext', ns)), b'<w:keepNext xmlns:w="'+ns['w'].encode()+b'"/>')
                    else:
                        keeps = current.findall('.//w:keepNext', ns)
                        self.assertEqual([k.get('{'+ns['w']+'}val') for k in keeps], ['0'])
                self.assertIsNone(root.find('w:body/w:p/w:pPr/w:keepNext', ns))
                restored = E.fromstring(after.encode())
                for p in restored.findall('.//w:tr//w:p', ns):
                    pr = p.find('w:pPr', ns)
                    if pr is not None:
                        for keep in pr.findall('w:keepNext', ns): pr.remove(keep)
                        if len(pr) == 0: p.remove(pr)
                for pr in restored.findall('.//w:trPr', ns): pr.getparent().remove(pr)
                expected = E.fromstring(before.replace(marker, '').replace(old, '').encode())
                self.assertEqual(E.tostring(restored), E.tostring(expected), 'Only the bounded row properties may change')
            malformed = [row.replace(marker, marker*2), row.replace(marker, marker+old), row.replace('<w:tr>', '<w:tr><w:trPr><w:tblHeader/></w:trPr>'), row.replace('<w:tcPr />', '<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>', 1), row.replace('<w:p>', '<w:p/>', 1), row.replace('</w:pPr>', '<w:keepNext/></w:pPr>', 1)]
            for value in malformed:
                with self.subTest(autoescape=escape, source=value):
                    with self.assertRaises(UndefinedError): template.render(content=start+value+last+end)
            with self.assertRaises(UndefinedError): template.render(content=start+marker+last+end)

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
