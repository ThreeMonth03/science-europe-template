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
    def test_q13_supplied_scalar_identifiers_have_targeted_wrapping(self):
        css = (ROOT / 'src/layout.css').read_text()
        self.assertIn('#q-persistent-identifier .primary-identifiers { overflow-wrap: anywhere; word-break: break-word; }', css)

    def test_q14_pdf_keeps_only_bounded_fixed_duty_groups(self):
        from bs4 import BeautifulSoup
        from check_responsibility_reading import DUTIES, ROLES, contributor_replies
        from current_support import PREFIX, environment
        people = [('bounded', 'Alex Chen', ROLES), ('long', 'Long actor name ' * 50, ROLES),
                  ('short', 'Robin Lin', ROLES[:2])]
        for escape in (False, True):
            for profile in ('review', 'submission'):
                template = environment(ROOT, escape).from_string(
                    PREFIX + "{% include 'src/questions/14-dm-responsible.html.j2' %}")
                soup = BeautifulSoup(template.render(repliesMap=contributor_replies(people),
                    output_profile=profile), 'html.parser')
                owners = soup.select('.person-responsibilities')
                self.assertEqual([node['data-contributor-id'] for node in owners],
                                 ['bounded', 'long', 'short'])
                self.assertEqual([node['data-contributor-id'] for node in
                    soup.select('.person-responsibilities.short-responsibility-list')], ['bounded'])
                for owner, (_, name, _) in zip(owners, people):
                    self.assertEqual(owner.select_one('.responsible-person').get_text(), name)
                for owner in owners[:2]:
                    self.assertEqual([node.get_text() for node in owner.select('ul > li')], DUTIES['en'])
                self.assertFalse(soup.select('.responsibilities-block.short-responsibility-list'))
        css = (ROOT / 'src/layout.css').read_text()
        self.assertIn('#q-dm-responsible .person-responsibilities.short-responsibility-list { break-inside: avoid; }', css)
        self.assertNotIn('.responsibilities-block { break-inside: avoid;', css)

    def test_contributor_identity_line_retains_contacts_and_role_associations(self):
        from bs4 import BeautifulSoup
        from check_responsibility_reading import CONTACT, ROLES, contributor_replies
        from current_support import PREFIX, environment, path
        people = [('both', 'Alex Chen', ROLES), ('email', 'Robin Lin', [CONTACT]),
                  ('orcid', 'Casey Wu', ROLES[:1]), ('bare', 'Morgan Huang', [])]
        replies = contributor_replies(people)
        listing = path('adminDetailsCUuid', 'contributorsQUuid')
        for item in ('both', 'email'):
            replies[path(listing, item, 'contributorEmailQUuid')] = item + '@example.org'
        integration = {'value': {'value': {'type': 'PlainType', 'value': '0000-0001-2345-6789', 'raw': None}}}
        for item in ('both', 'orcid'):
            replies[path(listing, item, 'contributorOrcidQUuid')] = integration
        dc = {'project': {'created_by': None}, 'e': {'choices': {
            role: {'label': role} for role in [*ROLES, CONTACT]}}}
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX +
                "{% include 'src/contributors.html.j2' %}")
            soup = BeautifulSoup(template.render(repliesMap=replies, dc=dc,
                output_profile='submission'), 'html.parser')
            owners = soup.select('.contributor')
            self.assertEqual([node.select_one('.name').get_text() for node in owners],
                             [name for _, name, _ in people])
            self.assertEqual([len(node.select('.contributor-contact')) for node in owners], [1, 1, 1, 0])
            for owner, (item, _, roles) in zip(owners, people):
                self.assertEqual([node.get_text() for node in owner.select('.role')], sorted(roles))
                contact = owner.select_one('.contributor-contact')
                if contact:
                    self.assertEqual(contact.find_previous_sibling().get('class'), ['name'])
                    self.assertNotIn('<br', str(contact))
                    self.assertTrue(contact.get_text().startswith(', '))
                    self.assertEqual(contact.previous_sibling.get('class'), ['name'])
                if item in ('both', 'email'):
                    self.assertEqual(owner.select_one('a[href^="mailto:"]')['href'],
                                     'mailto:' + item + '@example.org')
                if item in ('both', 'orcid'):
                    self.assertIn('0000-0001-2345-6789', owner.get_text())

    def test_q14_unmarked_duty_list_keeps_actor_not_all_items_or_next_person(self):
        from check_responsibility_reading import DUTIES, ROLES, contributor_replies
        from current_support import PREFIX, environment
        from native_support import IMAGE, RUNNER
        template = environment(ROOT, True).from_string(
            PREFIX + "{% include 'src/questions/14-dm-responsible.html.j2' %}")
        source = template.render(repliesMap=contributor_replies([('owner', 'Alex Chen', ROLES)]),
                                 output_profile='submission') + '<p>NEXT_PERSON_SENTINEL</p>'
        source = source.replace(' short-responsibility-list', '')
        raw = subprocess.check_output(['docker', 'run', '--rm', '--pull=never', '--network=none',
            '--log-driver=none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER],
            input=json.dumps(dict(lua=(ROOT / 'src/word/pilot.lua').read_text(), html=source)).encode(), timeout=120)
        ast = json.loads(raw)
        def nodes(value):
            if isinstance(value, dict):
                yield value
                for child in value.values(): yield from nodes(child)
            elif isinstance(value, list):
                for child in value: yield from nodes(child)
        owner, = [node for node in nodes(ast) if node.get('t') == 'Div' and
                  'person-responsibilities' in node['c'][0][1]]
        self.assertNotIn('short-reading-unit', owner['c'][0][1])
        actor, duties = owner['c'][1]
        self.assertEqual(actor['c'][0], ['', [], [['custom-style', 'Pilot Label']]])
        self.assertEqual(duties['t'], 'BulletList')
        self.assertEqual(len(duties['c']), 7)
        for item, expected in zip(duties['c'], DUTIES['en']):
            self.assertEqual(len(item), 1)
            self.assertEqual(item[0]['t'], 'Plain')
            self.assertEqual(''.join(' ' if inline['t'] == 'Space' else inline['c']
                                    for inline in item[0]['c']), expected)
        self.assertEqual(ast['blocks'][-1], {'t': 'Para', 'c': [{'t': 'Str', 'c': 'NEXT_PERSON_SENTINEL'}]})

    def test_q14_word_bounded_bullets_preserve_numbering_and_stop_at_each_person(self):
        import base64
        from native_support import IMAGE, WORD_RUNNER
        def person(actor='Alex Chen', duties=None, marker='short-responsibility-list', extra='', ending=''):
            duties = duties or ['Original first duty.', 'Original second duty.', 'Original final duty.']
            return ('<div class="person-responsibilities '+marker+'" data-contributor-id="owner" '
                    'data-contributor-index="1"'+extra+'><p><strong>'+actor+'</strong></p><ul>'+''.join(
                        '<li>'+duty+'</li>' for duty in duties)+'</ul>'+ending+'</div>')
        def question(body):
            return ('<div id="q-dm-responsible" class="question"><h3>14. Original question</h3>'
                    '<div class="question-guidance"><p>Original question guidance.</p></div>'
                    '<div class="answer"><div class="responsibilities-block">'+body+'</div></div></div>')
        base = question(person())
        cases = [('three', base, 3),
                 *[(str(count)+'-items', question(person(duties=['Duty '+str(i) for i in range(count)])), count)
                   for count in range(4, 8)],
                 ('cjk', question(person('範例人員', ['蒐集原始資料。', '管理資料。', '保留原始紀錄。'])), 3),
                 ('actor-boundary', question(person('x'*120)), 3),
                 ('cjk-actor-boundary', question(person('中'*60)), 3),
                 ('actor-long', question(person('x'*121)), 0),
                 ('cjk-actor-long', question(person('中'*61)), 0),
                 ('total-long', question(person(duties=['x'*901, 'Second.', 'Third.'])), 0),
                 ('two-items', question(person(duties=['First.', 'Last.'])), 0),
                 ('eight-items', question(person(duties=['Duty']*8)), 0),
                 ('rich-item', question(person(duties=['<em>Original duty.</em>', 'Second.', 'Third.'])), 0),
                 ('terminal-kept-wrapper', question(person(duties=['First.', 'Second.',
                    '<div custom-style="Pilot List Lead"><p>Original final duty.</p></div>'])), 0),
                 ('nested-list', question(person(duties=['<ul><li>Original duty.</li></ul>', 'Second.', 'Third.'])), 0),
                 ('rich-actor', question(person('<a href="https://example.org">Original owner</a>')), 0),
                 ('extra-attribute', question(person(extra=' data-extra="original"')), 0),
                 ('missing-hint', question(person(ending='<p class="data-gap">Original name hint.</p>')), 0),
                 ('unmarked', question(person(marker='')), 0),
                 ('wrong-question', base.replace('id="q-dm-responsible"', 'id="q-other"'), 0),
                 ('unknown-question-class', base.replace('class="question"', 'class="question other"'), 0),
                 ('unknown-answer', base.replace('class="answer"', 'class="answer" data-extra="original"'), 0),
                 ('unknown-block', base.replace('class="responsibilities-block"', 'class="responsibilities-block" data-extra="original"'), 0),
                 ('empty-item-id', base.replace('data-contributor-id="owner"', 'data-contributor-id=""'), 0),
                 ('invalid-index', base.replace('data-contributor-index="1"', 'data-contributor-index="0"'), 0),
                 ('authored-lookalike', question('<div class="answer-detail">'+person()+'</div>'), 0),
                 ('two-people', question(person()+person('Robin Lin')), 6)]
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        call = '  if div.identifier == "q-dm-responsible" then div = keep_short_responsibility_lists(div) or div end'
        self.assertEqual(lua.count(call), 1)
        source = ''.join('<div id="case-'+name+'">'+body+'<p>Original next record.</p></div>'
                         for name, body, _ in cases)
        payload = dict(html=source, reference=base64.b64encode((ROOT/'src/word/reference.docx').read_bytes()).decode())
        results = []
        for variant in [lua.replace(call, ''), lua]:
            payload['lua'] = variant
            results.append(json.loads(subprocess.check_output(['docker', 'run', '--rm', '--pull=never', '--network=none',
                '--log-driver=none', '-i', '--entrypoint', 'python', IMAGE, '-c', WORD_RUNNER],
                input=json.dumps(payload).encode(), timeout=180)))
        def normalize(value):
            if isinstance(value, dict):
                if value.get('t') == 'Div' and value['c'][0] in [
                    ['', [], [['custom-style', 'Pilot List Lead']]],
                    ['', [], [['custom-style', 'Pilot Responsibility Lead']]],
                    ['', [], [['custom-style', 'Pilot Responsibility Item']]]]:
                    self.assertEqual(len(value['c'][1]), 1)
                    value = value['c'][1][0]
                    return {'t': 'Plain', 'c': normalize(value['c'])}
                return {key: normalize(child) for key, child in value.items()}
            return [normalize(child) for child in value] if isinstance(value, list) else value
        self.assertEqual(normalize(results[0]['ast']), normalize(results[1]['ast']))
        for (name, _, expected), block in zip(cases, results[1]['ast']['blocks']):
            styles = json.dumps(block)
            self.assertEqual(expected, styles.count('Pilot Responsibility Lead')+styles.count('Pilot Responsibility Item'), name)
            self.assertEqual(2 if name == 'two-people' else int(bool(expected)), styles.count('Pilot Responsibility Item'), name)
            self.assertEqual(int(name not in ['wrong-question', 'unknown-question-class']),
                             styles.count('Pilot Question Guidance'), name)
        changed = 0
        self.assertEqual(len(results[0]['paragraphs']), len(results[1]['paragraphs']))
        for before, after in zip(results[0]['paragraphs'], results[1]['paragraphs']):
            self.assertEqual(before['text'], after['text'])
            self.assertEqual(before['other_xml'], after['other_xml'])
            if before['style'] != after['style']:
                self.assertIn(after['style'], ['PilotResponsibilityLead', 'PilotResponsibilityItem'])
                changed += 1
        self.assertEqual(changed, sum(expected for _, _, expected in cases))

    def test_word_separate_roster_marker_keeps_heading_and_all_records(self):
        from native_support import IMAGE, RUNNER
        def roster(count, attrs=' class="separate-roster"', identifier='dmp-contributors', item='Original owner'):
            return ('<div id="'+identifier+'"'+attrs+'><h2>People</h2><ul>'+''.join(
                '<li>'+item+' '+str(index)+'<br>Original roles.<br>Original affiliation.</li>'
                for index in range(count))+'</ul></div>')
        cases = [(roster(4), 1), (roster(5), 1), (roster(4, item='Long name '*100), 1),
                 (roster(3), 0), (roster(0), 0), (roster(4, attrs=''), 0),
                 (roster(4, identifier='other'), 0), (roster(4, attrs=' class="separate-roster other"'), 0),
                 (roster(4, attrs=' class="separate-roster" data-extra="original"'), 0)]
        marker = '<!--DSW:SE:roster-start:v1-->'
        lua = (ROOT/'src/word/pilot.lua').read_text()
        line = '    div.content:insert(1, pandoc.RawBlock("openxml", "'+marker+'"))'
        self.assertEqual(lua.count(line), 1)
        source = ''.join('<div id="case-'+str(index)+'">'+value+'</div>' for index, (value, _) in enumerate(cases))
        results = []
        for variant in (lua.replace(line, ''), lua):
            results.append(json.loads(subprocess.check_output(['docker', 'run', '--rm', '--pull=never', '--network=none',
                '--log-driver=none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(
                    dict(lua=variant, html=source)).encode(), timeout=180)))
        for (_, expected), before, after in zip(cases, results[0]['blocks'], results[1]['blocks']):
            self.assertEqual(expected, json.dumps(after).count(marker))
            if expected:
                content = after['c'][1][0]['c'][1]
                self.assertEqual(content[0], {'t': 'RawBlock', 'c': ['openxml', marker]})
                self.assertEqual(content[1]['t'], 'Header')
                self.assertEqual(content[1]['c'][0], 2)
                del content[0]
            self.assertEqual(before, after)

    def test_roster_xml_break_changes_only_the_marked_heading2(self):
        from jinja2 import UndefinedError
        marker = '<!--DSW:SE:roster-start:v1-->'
        heading = '<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr><w:r><w:t>People</w:t></w:r></w:p>'
        earlier = '<w:p><w:r><w:t>Original overview</w:t></w:r></w:p>'
        later = '<w:p><w:r><w:t>Original person</w:t></w:r></w:p>'
        for escape in (False, True):
            template = Environment(loader=FileSystemLoader(ROOT), undefined=StrictUndefined,
                autoescape=escape).get_template('src/word/short-tables.xml')
            self.assertEqual(earlier+heading+later, template.render(content=earlier+heading+later))
            self.assertEqual(earlier+heading.replace('</w:pPr>', '<w:pageBreakBefore/></w:pPr>')+later,
                             template.render(content=earlier+marker+heading+later))
            for invalid in (marker+heading+marker+heading, marker+heading.replace('Heading2', 'Heading3'),
                            marker+earlier+heading):
                with self.assertRaises(UndefinedError): template.render(content=invalid)

    def test_generated_roster_marker_requires_large_visible_chinese_roster(self):
        from bs4 import BeautifulSoup
        from check_responsibility_reading import contributor_replies
        from current_support import PREFIX, environment
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/contributors.html.j2' %}")
            for language in ('en', 'zh-Hant'):
                for profile in ('review', 'submission'):
                    for count in (0, 3, 4, 5):
                        people = [(str(index), 'Original owner '+str(index), []) for index in range(count)]
                        people.append(('blank', '', []))
                        soup = BeautifulSoup(template.render(repliesMap=contributor_replies(people),
                            dc={'project': {'created_by': None}}, output_profile=profile, document_language=language), 'html.parser')
                        self.assertEqual(int(language == 'zh-Hant' and count >= 4),
                                         len(soup.select('#dmp-contributors.separate-roster')))
                        self.assertEqual(count, len(soup.select('.contributor')))

    def test_q6_policy_keep_changes_only_bounded_metadata_not_authored_or_next_item(self):
        import base64
        from bs4 import BeautifulSoup
        from native_support import IMAGE, WORD_RUNNER
        from current_support import PREFIX, environment, path
        listing = path('adminDetailsCUuid', 'policiesProceduresQUuid')
        cases = [
            ('short-en', 'Policy <A> & B', 'https://example.org/?a=1&b=2', '<p>Original short description.</p>', 1),
            ('short-zh', 'CC BY-NC 4.0', 'https://creativecommons.org/licenses/by-nc-sa/4.0/', '<p>本資料可供非商業研究使用，引用時請註明來源。</p>', 1),
            ('name-only', 'Policy', '', '<p>Original short description.</p>', 1),
            ('url-only', '', 'https://example.org/', '<p>Original short description.</p>', 1),
            ('boundary', 'Policy', '', '<p>' + '中' * 80 + '</p>', 1),
            ('long', 'Policy', '', '<p>' + '中' * 81 + '</p>', 0),
            ('long-metadata', '中' * 81, '', '<p>Original short description.</p>', 0),
            ('rich', 'Policy', '', '<p>Keep <a href="https://example.org/">original link</a>.</p>', 0),
            ('table-first', 'Policy', '', '<table><tr><td>Original table.</td></tr></table>', 0),
            ('multiple', 'Policy', '', '<p>Original first.</p><p>Original second.</p>', 0),
            ('description-only', '', '', '<p>Original short description.</p>', 0),
            ('metadata-only', 'Policy', 'https://example.org/', '', 0),
            ('authored-item', '', '', '<div class="policy-item short-policy-item" data-item-id="fake">Fake metadata<p>Keep original.</p></div>', 0),
        ]
        bodies, expected = [], 0
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/06-access-security.html.j2' %}")
            for profile in ('review', 'submission'):
                for name, title, link, description, keeps in cases:
                    replies = {listing: ['blank-policy', 'original-policy']}
                    for field, value in [('Name', title), ('Link', link), ('Description', description)]:
                        replies[path(listing, 'original-policy', 'policiesProcedures' + field + 'QUuid')] = value
                    body = template.render(repliesMap=replies, output_profile=profile)
                    if description: self.assertIn(description, body)
                    soup = BeautifulSoup(body, 'html.parser')
                    answer = soup.select_one('.answer')
                    owners = soup.select('.answer > ul > li > .policy-item[data-item-id="original-policy"]')
                    self.assertEqual(bool(keeps), bool(owners))
                    self.assertEqual('1' if keeps else None, answer.get('data-short-policy-positions'))
                    if name == 'table-first': self.assertTrue(soup.select('.answer > ul > li > strong:first-child:has(+ table)'))
                    bodies.append(body); expected += keeps
                    if name == 'short-en':
                        bodies += [body.replace('id="q-access-security"', 'id="q-other"'),
                                   '<div class="answer-detail">' + body + '</div>']
                        replies[listing].append('other-policy')
                        for field, value in [('Name', title), ('Link', link), ('Description', description)]:
                            replies[path(listing, 'other-policy', 'policiesProcedures' + field + 'QUuid')] = value
                        pair = template.render(repliesMap=replies, output_profile=profile)
                        self.assertEqual(BeautifulSoup(pair, 'html.parser').select_one('.answer')['data-short-policy-positions'], '1 2')
                        bodies.append(pair); expected += 2
        reading = (ROOT / 'src/word/preservation-reading.lua').read_text()
        call = 'elseif id == "q-access-security" then policy(block, answer.attributes["short-policy-positions"] or "")'
        self.assertEqual(reading.count(call), 1)
        common = 'common=["pandoc","--from=html","--lua-filter="+str(f)]'
        runner = WORD_RUNNER.replace(common, 'g=Path(tmp)/"reading.lua";g.write_text(p["reading"])\n '+common[:-1]+',"--lua-filter="+str(g)]')
        results = []
        for source in (reading.replace(call, 'elseif id == "q-access-security" then -- baseline'), reading):
            raw = subprocess.check_output(['docker', 'run', '--rm', '--pull=never', '--network=none',
                '--log-driver=none', '-i', '--entrypoint', 'python', IMAGE, '-c', runner],
                input=json.dumps(dict(lua=(ROOT / 'src/word/pilot.lua').read_text(), reading=source,
                    html=''.join('<div>' + body + '</div>' for body in bodies),
                    reference=base64.b64encode((ROOT / 'src/word/reference.docx').read_bytes()).decode())).encode(), timeout=180)
            results.append(json.loads(raw)['paragraphs'])
        self.assertEqual(len(results[0]), len(results[1]))
        changed = 0
        for before, after in zip(*results):
            self.assertEqual(before['text'], after['text'])
            self.assertEqual(before['other_xml'], after['other_xml'])
            if before['style'] != after['style']:
                self.assertEqual(after['style'], 'PilotListLead')
                self.assertNotIn('Original short description.', after['text'])
                changed += 1
            elif 'Original short description.' == after['text']:
                self.assertNotIn(after['style'], ['PilotLead', 'PilotListLead'])
        self.assertEqual(changed, expected)

    def test_reading_indent_styles_only_owned_prose_not_lists_or_tables(self):
        from native_support import IMAGE, RUNNER
        def question(kind, body):
            return '<div id="'+kind+'" class="question"><h3>Original question</h3><div class="answer">'+body+'</div></div>'
        detail = '<div class="reading-detail" data-reading-detail="{}"><p>Keep <a href="#original">original text</a>.</p><ul><li>Keep list.</li></ul><table><tr><td>Keep table.</td></tr></table><div><p>Keep authored div.</p></div></div>'
        collection = ('<div class="collection-dataset reading-record" data-reading-record="collection" data-item-id="one">'
                      '<p>Original dataset: original description.</p><div class="answer-detail" data-fact-id="external-ownership">'+
                      detail.format('collection-ownership')+'</div></div>')
        formatting = ('<div class="data-formats"><div class="format-description reading-record" data-reading-record="format" data-item-id="one">'
                      '<div class="dataset-policy format-summary"><p>Original format and policy.</p></div>'
                      '<div class="answer-detail" data-fact-id="nonstandard-reason">'+detail.format('format-reason')+'</div></div></div>')
        quality = ('<div class="quality-dataset reading-record" data-reading-record="quality" data-item-id="one">'
                   '<p>Original dataset: quality checks.</p><div class="answer-detail" data-fact-id="quality-other">'+
                   detail.format('quality-other')+'</div></div>')
        naming = ('<div class="storage-conventions-policy"><div class="q3-storage-group" data-storage-group="filesystem">'
                  '<div class="dataset-policy"><div class="answer-detail short-naming-answer" data-fact-id="file-naming">'
                  '<div class="answer-lead" custom-style="Pilot Lead"><p>Original naming label:</p></div>'+
                  detail.format('file-naming')+'</div></div></div></div>')
        personal = detail.format('personal-safeguards').replace('class="reading-detail"',
            'class="answer-detail reading-detail" data-fact-id="personal-data-additional-safeguards" data-status="complete"')
        cases = [('collection', question('q-what-data', '<div><h4>Collections</h4>'+collection+'</div>'), 2),
                 ('format', question('q-what-data', formatting), 2),
                 ('quality', question('q-quality-control', quality), 2),
                 ('naming', question('q-docs-metadata', naming), 1),
                 ('personal', question('q-personal-data', personal), 1),
                 ('ethics', question('q-ethical-issues', '<p>General prose.</p><div class="answer-detail">'+detail.format('ethics-authored')+'</div>'), 1),
                 ('wrong-owner', question('q-other', collection+personal), 0),
                 ('authored-lookalike', question('q-what-data', '<div class="answer-detail">'+collection+'</div>'), 0),
                 ('unmarked', question('q-quality-control', quality.replace(' reading-record','')), 0),
                 ('wrong-role', question('q-quality-control', quality.replace('data-reading-record="quality"','data-reading-record="format"')), 0)]
        script = '''import contextlib,io,json,sys
p=json.load(sys.stdin);results=[]
for lua in ['',p['lua']]:
 sys.stdin=io.StringIO(json.dumps(dict(lua=lua,html=p['html'])))
 out=io.StringIO()
 with contextlib.redirect_stdout(out): exec(p['runner'],{})
 results.append(json.loads(out.getvalue()))
print(json.dumps(results))
'''
        payload = dict(lua=(ROOT/'src/word/preservation-reading.lua').read_text(), runner=RUNNER,
                       html=''.join('<div id="case-'+name+'">'+body+'</div>' for name,body,_ in cases))
        before, after = json.loads(subprocess.check_output(
            ['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
             '--entrypoint','python',IMAGE,'-c',script], input=json.dumps(payload).encode(), timeout=180))
        def nodes(value, kind):
            if isinstance(value, dict):
                return ([value] if value.get('t') == kind else []) + sum((nodes(v, kind) for v in value.values()), [])
            return sum((nodes(v, kind) for v in value), []) if isinstance(value, list) else []
        for (name, _, count), left, right in zip(cases, before['blocks'], after['blocks']):
            with self.subTest(case=name):
                for kind in ('Str', 'Link', 'BulletList', 'Table'):
                    self.assertEqual(nodes(left, kind), nodes(right, kind))
                styles = [v for n in nodes(right, 'Div') for k,v in n['c'][0][2]
                          if k == 'custom-style' and v.startswith('Pilot Reading ')]
                self.assertEqual(count, len(styles))

    def test_frontmatter_question_boundary_does_not_force_a_cover_page(self):
        css = (ROOT / 'src/layout.css').read_text()
        self.assertIn('html body #dmp-content { break-before: auto; page-break-before: auto; }', css)
        self.assertNotIn('#dmp-content { break-before: page;', css)
        self.assertIn('#sec-data-collection > h2.body-start { break-before: page;', css)
        # The XML helper must accept the flowing boundary and leave authored
        # breaks intact, not turn the first section into a mandatory new page.
        bookmark = '<w:bookmarkStart w:id="1" w:name="dmp-content" />\n    '
        heading = '<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr><w:r><w:t>Original section</w:t></w:r></w:p>'
        page_break = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n    '
        for escape in (False, True):
            template = Environment(loader=FileSystemLoader(ROOT), undefined=StrictUndefined,
                autoescape=escape).get_template('src/word/short-tables.xml')
            for explicit in ('', page_break):
                with self.subTest(escape=escape, explicit_break=bool(explicit)):
                    source = bookmark + explicit + heading
                    self.assertEqual(source, template.render(content=source))
            marked = '<!--DSW:SE:body-start:v1-->' + heading
            self.assertEqual(heading.replace('</w:pPr>', '<w:pageBreakBefore/></w:pPr>'),
                             template.render(content=marked))

    def test_stock_pandoc_marks_only_the_owned_conditional_body_heading(self):
        from native_support import IMAGE, RUNNER
        section = ('<section id="sec-data-collection" class="dmp-section"><h2 class="body-start">Section 1</h2>'
                   '<div id="q-how-data" class="question"><h3>1. One</h3></div>'
                   '<div id="q-what-data" class="question"><h3>2. Two</h3></div></section>')
        cases = [section, section.replace(' class="body-start"', ''),
                 section.replace('sec-data-collection', 'other-section'), '<h2 class="body-start">Authored heading</h2>']
        payload = dict(lua=(ROOT/'src/word/pilot.lua').read_text(),
                       html=''.join('<div id="case-'+str(i)+'">'+value+'</div>' for i,value in enumerate(cases)))
        result = json.loads(subprocess.check_output(
            ['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
             '--entrypoint','python',IMAGE,'-c',RUNNER], input=json.dumps(payload).encode(), timeout=180))
        for index, block in enumerate(result['blocks']):
            self.assertEqual(int(index == 0), json.dumps(block).count('DSW:SE:body-start:v1'))

    def test_dataset_indent_and_bounded_keeps_preserve_text_and_links(self):
        from native_support import IMAGE, RUNNER
        def record(body, marked=True, q='q-data-preservation'):
            return ('<div id="'+q+'" class="question"><h3>Original question</h3><div class="answer">'
                    '<div class="dataset-section'+(' short-dataset-record' if marked else '')+'" data-item-id="dataset">'
                    '<h5>Original dataset</h5>'+body+'</div></div></div>')
        short = ('<div class="answer-detail"><p>Keep original description.</p></div>'
                 '<div class="dataset-policy"><p>See <a href="#policy">policy</a>.</p></div>'
                 '<div class="repository-destinations short-repository-list"><ul><li>Institutional repository.</li></ul></div>')
        cases = [('short', record(short), True), ('unmarked', record(short, False), False),
                 ('long', record(short.replace('Keep original description.', '中'*181)), False),
                 ('table', record(short.replace('Keep original description.', '<table><tr><td>Keep table.</td></tr></table>')), False),
                 ('authored-list', record(short.replace('<p>Keep original description.</p>', '<ul><li>Keep authored list.</li></ul>')), False),
                 ('fixed-tail', record('<p>'+'Original opening. '*30+'</p><div class="distribution-section"><p>'+'Fixed policy. '*30+'</p></div><div class="qualified-reference-tail"><p>No qualified references.</p></div>', False, 'q-share-restrictions'), True),
                 ('authored-tail', record('<div class="answer-detail"><p>Keep authored text.</p></div><div class="qualified-reference-tail"><p>No qualified references.</p></div>', False, 'q-share-restrictions'), False),
                 ('wrong-owner', record(short, q='q-other'), False)]
        script = '''import contextlib,io,json,sys
p=json.load(sys.stdin);results=[]
for lua in ['',p['lua']]:
 sys.stdin=io.StringIO(json.dumps(dict(lua=lua,html=p['html'])))
 out=io.StringIO()
 with contextlib.redirect_stdout(out): exec(p['runner'],{})
 results.append(json.loads(out.getvalue()))
print(json.dumps(results))
'''
        payload = dict(lua=(ROOT/'src/word/preservation-reading.lua').read_text(), runner=RUNNER,
                       html=''.join('<div id="case-'+name+'">'+html+'</div>' for name,html,_ in cases))
        before, after = json.loads(subprocess.check_output(
            ['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
             '--entrypoint','python',IMAGE,'-c',script], input=json.dumps(payload).encode(), timeout=180))
        def values(node, kind):
            if isinstance(node, dict):
                own = [node['c']] if node.get('t') == kind else []
                return own + sum((values(value, kind) for value in node.values()), [])
            return sum((values(value, kind) for value in node), []) if isinstance(node, list) else []
        for (name, _, bounded), left, right in zip(cases, before['blocks'], after['blocks']):
            with self.subTest(case=name):
                self.assertEqual(values(left, 'Str'), values(right, 'Str'))
                self.assertEqual(values(left, 'Link'), values(right, 'Link'))
                self.assertEqual(int(bounded), json.dumps(right).count('Pilot Dataset Terminal'))
                self.assertEqual(name != 'wrong-owner', 'Pilot Dataset Detail' in json.dumps(right))

    def test_short_dataset_html_hint_rejects_unknown_or_tall_authored_markup(self):
        import sys
        sys.path.insert(0, str(ROOT/'scripts'))
        from current_support import environment
        template = environment(ROOT, False).from_string(
            "{% import 'src/macros.html.j2' as m %}{{ m.shortDatasetRecord(value) }}")
        for value, expected in [('<p>Keep <a href="#policy">policy</a>.</p>', '1'),
                                ('<div><p>'+'中'*300+'</p></div>', '1'),
                                ('<p>'+'a'*301+'</p>', ''), ('<IMG src="large.png">', ''),
                                ('<svg></svg>', ''), ('<table><tr><td>Keep.</td></tr></table>', ''),
                                ('<p\nstyle = "font-size:100pt">Keep.</p>', ''),
                                ('<div><blockquote>Keep.</blockquote></div>', '')]:
            with self.subTest(value=value[:40]):
                self.assertEqual(expected, template.render(value=value))
        self.assertEqual('', template.render(value='<p>x</p>'*20))
        labeled = environment(ROOT, False).from_string(
            "{% import 'src/macros.html.j2' as m %}{{ m.shortDatasetRecord(value, label) }}")
        self.assertEqual('', labeled.render(value='<p>Keep.</p>', label='x'*1000))
        self.assertEqual('', labeled.render(value='<p>'+'中'*295+'</p>', label='Long dataset name'))

    def test_dataset_secondary_type_is_scoped_to_the_owned_attribute_label(self):
        from native_support import IMAGE, RUNNER
        body = ('<div id="q-how-data" class="question"><div class="answer"><div class="dataset-list">'
                '<div class="dataset-section" data-item-id="dataset"><h5>Dataset</h5>'
                '<div class="answer-detail" data-fact-id="reuse-rightsholder">'
                '<div custom-style="Pilot Label"><p><strong>Owned attribute</strong></p></div>'
                '<div custom-style="Pilot Label"><p><strong>Authored emphasis</strong></p></div>'
                '</div></div></div></div></div>')
        result = subprocess.check_output(
            ['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
             '--entrypoint','python',IMAGE,'-c',RUNNER],
            input=json.dumps(dict(lua=(ROOT/'src/word/preservation-reading.lua').read_text(), html=body)).encode(), timeout=180).decode()
        self.assertEqual(1, result.count('Pilot Dataset Attribute'))
        self.assertEqual(1, result.count('Pilot Dataset Label'))

    def test_flowing_word_root_still_classifies_only_owned_empty_sections(self):
        from native_support import IMAGE
        sections = [
            ('sec-data-collection', ['q-how-data', 'q-what-data']),
            ('sec-docs-metadata', ['q-docs-metadata', 'q-quality-control']),
            ('sec-storage-backup', ['q-store-backup', 'q-access-security']),
            ('sec-ethics-legal', ['q-personal-data', 'q-copyright-ipr', 'q-ethical-issues']),
            ('sec-sharing-preservation', ['q-share-restrictions', 'q-data-preservation', 'q-access-data', 'q-persistent-identifier']),
            ('sec-responsibilities-resources', ['q-dm-responsible', 'q-required-resources']),
        ]
        policy = '<div class="workspace-policy dataset-policy"><div class="reading-gap"></div><div class="reading-gap"></div></div>'
        parts = ['<section id="' + sid + '" class="dmp-section"><h2>Original section</h2>' +
            ''.join('<div id="' + qid + '" class="question compact-empty-question"><h3>Original question</h3>'
                '<div class="answer">' + (policy if qid == 'q-store-backup' else '') + '</div></div>'
                for qid in questions) + '</section>' for sid, questions in sections]
        content = ''.join(parts)
        cases = [
            ('all-empty', content, 6, ''),
            ('answered-first', content.replace('<div class="answer"></div>', '<div class="answer"><p>Original answer.</p></div>', 1), 5, ''),
            ('authored-prefix', '<p>Original prefix.</p>' + content, 0, ''),
            ('reordered', parts[1] + parts[0] + ''.join(parts[2:]), 0, ''),
            ('unowned-root', content, 0, ' class="other"'),
            ('authored-policy', content.replace(policy, policy.replace('<div class="reading-gap"></div>', '<div class="reading-gap"><p>Original policy.</p></div>', 1)), 5, ''),
        ]
        runner = '''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin); results=[]
with tempfile.TemporaryDirectory() as tmp:
 for mode in ['json','docx']:
  args=['pandoc','--from=html','--to=json']
  for name in ['pilot','spacing']:
   f=Path(tmp)/(name+'.lua');f.write_text('FORMAT="'+mode+'"\\n'+p[name]);args.append('--lua-filter='+str(f))
  for name,content,count,attrs in p['cases']:
   source='<div id="dmp-content"'+attrs+'>'+content+'</div>'
   results.append([mode,name,count,json.loads(subprocess.check_output(args,input=source.encode()))])
print(json.dumps(results))
'''
        payload = {'pilot': (ROOT / 'src/word/pilot.lua').read_text(),
            'spacing': (ROOT / 'src/word/question-spacing.lua').read_text(), 'cases': cases}
        result = json.loads(subprocess.check_output(
            ['docker', 'run', '--rm', '--pull=never', '--network=none', '--log-driver=none', '-i',
             '--entrypoint', 'python', IMAGE, '-c', runner], input=json.dumps(payload).encode(), timeout=180))
        for mode, name, count, document in result:
            with self.subTest(mode=mode, case=name):
                serialized = json.dumps(document)
                self.assertEqual(count, serialized.count('DSW:SE:empty-section:v1:begin'))
                self.assertEqual(15, serialized.count('"Header", "c": [3,'))
                self.assertEqual(15, serialized.count('"Str", "c": "question"'))
                self.assertNotIn('w:type=\\"page\\"', serialized)
                if name == 'answered-first': self.assertIn('answer.', serialized)
                if name == 'authored-prefix': self.assertIn('prefix.', serialized)
                if name == 'authored-policy': self.assertIn('policy.', serialized)

    def test_word_marked_iso_dates_bind_every_character_without_touching_other_text(self):
        import base64
        from native_support import IMAGE, WORD_RUNNER
        date = '2027-12-31'
        bound = '\u2060'.join(date.replace('-', '\u2011'))
        cases = [
            ('Before <span class="date-value">' + date + '</span> after.', 'Before ' + bound + ' after.'),
            ('計畫將於<span class="date-value">' + date + '</span>結束。', '計畫將於' + bound + '結束。'),
            ('Unmarked ' + date + '.', 'Unmarked ' + date + '.'),
            ('<span class="other">' + date + '</span>', date),
            ('Original prose: 2027-12-31 and station_20271231.csv.', 'Original prose: 2027-12-31 and station_20271231.csv.'),
            ('<a href="https://example.org/' + date + '">https://example.org/' + date + '</a>', 'https://example.org/' + date),
        ]
        for malformed in ('2027-12', '2027-1-31', '2027-12-31-extra', '31/12/2027', '2027–12–31'):
            cases.append(('<span class="date-value">' + malformed + '</span>', malformed))
        result = json.loads(subprocess.check_output(
            ['docker', 'run', '--rm', '--pull=never', '--network=none', '--log-driver=none', '-i',
             '--entrypoint', 'python', IMAGE, '-c', WORD_RUNNER],
            input=json.dumps(dict(lua=(ROOT / 'src/word/pilot.lua').read_text(),
                html=''.join('<p>' + source + '</p>' for source, _ in cases),
                reference=base64.b64encode((ROOT / 'src/word/reference.docx').read_bytes()).decode())).encode(),
            timeout=180))
        # Read the emitted DOCX paragraphs, not just the filtered Pandoc AST.
        self.assertEqual([expected for _, expected in cases], [p['text'] for p in result['paragraphs']])
        self.assertEqual(9, bound.count('\u2060'))
        self.assertFalse(bound.startswith('\u2060') or bound.endswith('\u2060'))
        self.assertFalse(any('\u2060' in p['text'] for p in result['paragraphs'][2:]))

    def test_word_binds_only_the_eight_owned_funding_status_labels(self):
        from native_support import IMAGE, RUNNER
        labels = ['(planned)', '(applied)', '(granted)', '(rejected)', '（規劃中）', '（已申請）', '（已核准）', '（未核准）']
        body = ''.join('<p><span class="funding-status">'+label+'</span></p>' for label in labels)
        body += '<p>（已核准）</p><p><span class="funding-status">Other answer</span></p>'
        result = subprocess.check_output(
            ['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
             '--entrypoint','python',IMAGE,'-c',RUNNER],
            input=json.dumps(dict(lua=(ROOT/'src/word/pilot.lua').read_text(), html=body)).encode(), timeout=180).decode()
        document = json.loads(result)
        for index, label in enumerate(labels):
            self.assertIn(chr(0x2060).join(label), json.dumps(document['blocks'][index], ensure_ascii=False))
        self.assertNotIn('\\u2060', json.dumps(document['blocks'][8:]))

    def test_q13_single_repository_subject_preserves_other_arrangements_and_authored_uses(self):
        import itertools
        import sys
        from lxml import html
        sys.path.insert(0, str(ROOT / 'scripts'))
        from current_support import PREFIX, IDS, environment, identifier_replies
        from check_access_reading import COMPOUND, REPOSITORY_SUBJECTS, repository_policy, reuse_replies, reuse_schema
        authored = '<p>Use stationA_YYYYMMDD.csv.</p><ul><li>Keep the original record.</li></ul><p>Keep this paragraph.</p>'
        for escape, profile in itertools.product((False, True), ('review', 'submission')):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/13-persistent-identifier.html.j2' %}")
            def render(replies):
                return html.fragment_fromstring(template.render(repliesMap=replies, output_profile=profile, km=reuse_schema()), create_parent=True)
            for kind, resolves in itertools.product(REPOSITORY_SUBJECTS['en'], ('Yes', 'No', '', 'unknown')):
                with self.subTest(escape=escape, profile=profile, kind=kind, resolves=resolves):
                    replies = identifier_replies(repository=kind, resolves=resolves, count=1)
                    reuse, _ = reuse_replies(detail=authored); replies.update(reuse)
                    document = render(replies)
                    distribution = document.xpath('.//div[@class="distribution-section"]')[0]
                    self.assertEqual(distribution.get('data-item-id'), 'distro-0')
                    self.assertFalse(distribution.xpath('.//div[@class="identifier-heading"]'))
                    policy = distribution.xpath('.//div[@class="identifier-arrangement dataset-policy"]')[0]
                    self.assertEqual(' '.join(''.join(policy.itertext()).split()), repository_policy('en', kind, resolves))
                    status = policy.xpath('.//*[@data-fact-id="identifier-resolution"]/@data-status')
                    self.assertEqual(status, ['complete' if resolves == 'Yes' else 'explicit-no'] if resolves in ('Yes', 'No') else [])
                    detail = document.xpath('.//div[@data-fact-id="measured-data-reuse-uses"]')[0]
                    self.assertEqual([node.tag for node in detail], ['p', 'ul', 'p'])
                    self.assertEqual(''.join(detail.itertext()), 'Use stationA_YYYYMMDD.csv.Keep the original record.Keep this paragraph.')
            for actor in ('ProjectDataSteward', 'InstitDataSteward', '', 'unknown'):
                document = render(identifier_replies(assigns=actor, count=1))
                self.assertEqual(len(document.xpath('.//div[@class="identifier-heading"]')), 1)
                self.assertNotIn('The institutional repository will assign', ''.join(document.itertext()))
            for parent in ('No', '', 'unknown'):
                document = render(identifier_replies(identifier=parent, count=1))
                self.assertFalse(document.xpath('.//*[@data-fact-id="identifier-assigner"]'))
                if parent == 'No': self.assertIn('identifiers will not be applied.', ''.join(document.itertext()))
            for kind in ('', 'unknown'):
                document = render(identifier_replies(repository=kind, count=1))
                self.assertIn(COMPOUND['en']['Yes'], ' '.join(''.join(document.itertext()).split()))
            replies = identifier_replies(count=2)
            for key in replies:
                if 'distro-1' in key and key.endswith(IDS['publishedDataIdentifierResolvableQUuid']):
                    replies[key] = IDS['publishedDataIdentifierResolvableNoAUuid']
                elif 'distro-1' in key and key.endswith(IDS['publishedDataRepositoryKindQUuid']):
                    replies[key] = IDS['publishedDataRepositoryNationalAUuid']
            document = render(replies)
            distributions = document.xpath('.//div[@class="distribution-section"]')
            self.assertEqual([node.get('data-item-id') for node in distributions], ['distro-0', 'distro-1'])
            for index, node in enumerate(distributions):
                heading = node.xpath('./div[@class="identifier-heading"]')[0]
                self.assertIn('Distribution ' + str(index + 1), ''.join(heading.itertext()))
                self.assertIn('Institutional repository' if index == 0 else 'National repository', ''.join(heading.itertext()))
                policy = node.xpath('.//div[@class="identifier-arrangement dataset-policy"]')[0]
                self.assertEqual(' '.join(''.join(policy.itertext()).split()), COMPOUND['en']['Yes' if index == 0 else 'No'])

    def test_short_naming_answers_keep_only_the_marked_paragraph_chain(self):
        from native_support import IMAGE, RUNNER
        body = ('<div class="answer-lead"><p>File naming conventions:</p></div>'
                '<p>Keep station_YYYYMMDD.csv.</p><p>Keep the separate paragraph.</p>'
                '<ul><li>Keep the original record.</li><li>Record each correction.</li></ul>')
        def naming(fact='file-naming', marked=True, value=body):
            return '<div class="answer-detail' + (' short-naming-answer' if marked else '') + '" data-fact-id="' + fact + '">' + value + '</div>'
        wrapped = body.replace('<p>Keep station_', '<div class="reading-detail" data-reading-detail="file-naming"><p>Keep station_') + '</div>'
        cases = [('file', naming(), 2), ('object', naming('object-naming'), 2),
                 ('owned-wrapper', naming(value=wrapped), 2),
                 ('wrong-wrapper', naming(value=wrapped.replace('data-reading-detail="file-naming"', 'data-reading-detail="other"')), 0),
                 ('unmarked', naming(marked=False), 0), ('wrong-owner', naming('other'), 0),
                 ('long', naming(value=body.replace('Keep station_YYYYMMDD.csv.', '中' * 81)), 0)]
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        guard = 'if #div.classes == 2 and div.classes:includes("answer-detail") and'
        self.assertEqual(1, lua.count(guard))
        fixture = ''.join('<div id="case-' + name + '">' + value + '</div>' for name, value, _ in cases)
        results = []
        for source in (lua.replace(guard, 'if false and #div.classes == 2 and div.classes:includes("answer-detail") and'), lua):
            results.append(json.loads(subprocess.check_output(
                ['docker', 'run', '--rm', '--pull=never', '--network=none', '--log-driver=none', '-i',
                 '--entrypoint', 'python', IMAGE, '-c', RUNNER],
                input=json.dumps(dict(lua=source, html=fixture)).encode(), timeout=180)))
        def styles(value):
            if isinstance(value, dict):
                return int(value.get('t') == 'Div' and ['custom-style', 'Pilot Lead'] in value['c'][0][2]) + sum(styles(v) for v in value.values())
            return sum(styles(v) for v in value) if isinstance(value, list) else 0
        def words(value):
            if isinstance(value, dict):
                if value.get('t') == 'Str': return [value['c']]
                return sum((words(v) for v in value.values()), [])
            return sum((words(v) for v in value), []) if isinstance(value, list) else []
        for (name, _, count), before, after in zip(cases, results[0]['blocks'], results[1]['blocks']):
            with self.subTest(case=name):
                self.assertEqual(words(before), words(after))
                self.assertEqual(count, styles(after) - styles(before))
                self.assertFalse(after['c'][0][2], 'Do not keep the outer owner as a whole')

    def test_question_guidance_is_owned_bounded_and_keeps_no_whole_answer(self):
        from native_support import IMAGE, RUNNER
        guidance = '<div class="question-guidance"><p>Fixed explanation.</p></div>'
        def question(qid, guide=guidance, body='<p>Original answer.</p>'):
            return '<div id="' + qid + '" class="question"><h3>Original heading</h3>' + guide + '<div class="answer">' + body + '</div></div>'
        cases = [(qid, question(qid), True) for qid in
                 ('q-persistent-identifier', 'q-dm-responsible', 'q-required-resources')]
        cases += [('chinese', question('q-persistent-identifier', guidance.replace('Fixed explanation.', '例如數位物件識別碼 DOI。')), True)]
        cases += [(name, question('q-persistent-identifier', value), False) for name, value in [
            ('extra-attribute', guidance.replace('question-guidance"', 'question-guidance" data-extra="x"')),
            ('extra-class', guidance.replace('question-guidance"', 'question-guidance other"')),
            ('rich', guidance.replace('Fixed explanation.', '<em>Fixed explanation.</em>')),
            ('nested', '<div>' + guidance + '</div>'),
            ('two-paragraphs', guidance.replace('</p>', '</p><p>Another.</p>')),
            ('empty', guidance.replace('Fixed explanation.', '')),
            ('long', guidance.replace('Fixed explanation.', 'x' * 501)),
        ]]
        cases.append(('wrong-question', question('q-how-data'), False))
        gaps = ('<p>Original answer.</p><div class="q15-terminal-gap" data-fact-id="repository-charges" data-status="missing"><p>First missing fact.</p></div>'
                '<div class="q15-terminal-gap" data-fact-id="resources-costing" data-status="missing"><p>Second missing fact.</p></div>')
        cases.append(('q15-review-gaps', question('q-required-resources', body=gaps), True))
        lua = (ROOT / 'src/word/pilot.lua').read_text()
        html = ''.join('<div id="case-' + name + '">' + text + '</div>' for name, text, _ in cases)
        data = json.loads(subprocess.check_output(
            ['docker', 'run', '--rm', '--pull=never', '--network=none', '--log-driver=none', '-i',
             '--entrypoint', 'python', IMAGE, '-c', RUNNER],
            input=json.dumps({'lua': lua, 'html': html}).encode(), timeout=180))
        def all_divs(value):
            if isinstance(value, dict):
                if value.get('t') == 'Div': yield value
                for child in value.values(): yield from all_divs(child)
            elif isinstance(value, list):
                for child in value: yield from all_divs(child)
        for (name, original, expected), result in zip(cases, data['blocks']):
            with self.subTest(case=name):
                styled = [div for div in all_divs(result)
                    if ['custom-style', 'Pilot Question Guidance'] in div['c'][0][2]]
                self.assertEqual(int(expected), len(styled))
                if styled:
                    self.assertEqual(['question-guidance'], styled[0]['c'][0][1])
                    self.assertEqual(1, len(styled[0]['c'][1]))
                    self.assertEqual('Para', styled[0]['c'][1][0]['t'])
                question_node = result['c'][1][0]
                self.assertFalse(question_node['c'][0][2], 'Never style or keep the whole question')
                answer = question_node['c'][1][-1]
                self.assertEqual(['answer'], answer['c'][0][1])
                self.assertFalse(answer['c'][0][2], 'Never style or keep the whole answer')
                self.assertIn("'Original'", str(result)); self.assertIn("'answer.'", str(result))
                if name == 'q15-review-gaps':
                    terminal = [div for div in all_divs(result) if 'q15-terminal-gap' in div['c'][0][1]]
                    self.assertEqual(1, len(terminal))
                    self.assertIn("'First'", str(terminal)); self.assertIn("'Second'", str(terminal))

    def test_word_empty_guidance_markers_require_the_owned_question_shape(self):
        from native_support import IMAGE
        guide = '<div class="question-guidance"><p>A fixed example.</p></div>'
        def question(qid, guidance=guide, answer=''):
            return '<div id="' + qid + '" class="question compact-empty-question"><h3>Original heading</h3>' + guidance + '<div class="answer">' + answer + '</div></div>'
        cases = [(qid, question(qid), True) for qid in ('q-persistent-identifier', 'q-dm-responsible', 'q-required-resources')]
        cases += [('wrong-question', question('q-how-data'), False),
            ('extra-attribute', question('q-persistent-identifier', guide.replace('question-guidance"', 'question-guidance" data-extra="x"')), False),
            ('rich', question('q-persistent-identifier', guide.replace('A fixed example.', '<em>Original emphasis</em>')), False),
            ('authored-empty-block', question('q-persistent-identifier', answer='<div class="original"></div>'), False),
            ('authored-answer', question('q-persistent-identifier', answer='<p>Original answer.</p>'), False)]
        runner = '''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as tmp:
 args=['pandoc','--from=html','--to=json']
 for name in ['pilot','spacing']:
  f=Path(tmp)/(name+'.lua');f.write_text(p[name]);args.append('--lua-filter='+str(f))
 print(subprocess.check_output(args,input=p['html'].encode()).decode())
'''
        payload = {'pilot': (ROOT/'src/word/pilot.lua').read_text(),
                   'spacing': (ROOT/'src/word/question-spacing.lua').read_text(),
                   'html': ''.join('<div id="case-' + name + '">' + value + '</div>' for name, value, _ in cases)}
        result = json.loads(subprocess.check_output(['docker','run','--rm','--pull=never','--network=none','--log-driver=none','-i',
            '--entrypoint','python',IMAGE,'-c',runner],input=json.dumps(payload).encode(),timeout=180))
        for (name, original, eligible), block in zip(cases, result['blocks']):
            with self.subTest(case=name):
                self.assertEqual(2 if eligible else 0, str(block).count('DSW:SE:empty-question:v1:'))
                if eligible:
                    self.assertIn('Pilot Question Guidance', str(block))
                if name == 'authored-answer': self.assertIn("'answer.'", str(block))

    def test_guided_empty_question_xml_releases_only_its_final_paragraph(self):
        from jinja2 import DictLoader, ChoiceLoader
        heading = '<w:p><w:pPr><w:pStyle w:val="Heading3" /></w:pPr><w:r><w:t>Original heading</w:t></w:r></w:p>'
        guide = '<w:p><w:pPr><w:pStyle w:val="PilotQuestionGuidance" /></w:pPr><w:r><w:t>Original guidance</w:t></w:r></w:p>'
        begin, end = '<!--DSW:SE:empty-question:v1:begin-->\n    ', '\n    <!--DSW:SE:empty-question:v1:end-->'
        link_begin, link_end = '<!--DSW:SE:empty-section-link:v1:begin-->\n    ', '\n    <!--DSW:SE:empty-section-link:v1:end-->'
        for linked in (False, True):
            source = begin + heading + guide + end
            if linked: source = link_begin + source + link_end
            source += '<w:p><w:r><w:t>Original later text</w:t></w:r></w:p>'
            env = Environment(loader=ChoiceLoader([DictLoader({'src/word/short-tables.xml': source}),
                FileSystemLoader(ROOT)]), undefined=StrictUndefined)
            output = env.get_template('src/word/question-spacing.xml').render()
            self.assertNotIn('DSW:SE:', output)
            self.assertEqual(2, output.count('<w:keepNext'))
            self.assertIn('<w:pStyle w:val="Heading3" /><w:keepNext w:val="1"/>', output)
            self.assertIn('<w:pStyle w:val="PilotQuestionGuidance" /><w:keepNext w:val="' + str(int(linked)) + '"/>', output)
            self.assertTrue(output.endswith('<w:p><w:r><w:t>Original later text</w:t></w:r></w:p>'))
            for value in ('Original heading', 'Original guidance', 'Original later text'):
                self.assertEqual(1, output.count(value))

    def test_word_terminal_budget_and_single_person_keeps_are_bounded(self):
        import copy
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from native_support import RUNNER
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
        training = ('<div class="answer-detail" data-fact-id="specialist-expertise-detail" data-status="complete">'
                    '<p>Complete training before publication.</p><ul><li>Metadata checks.</li>'
                    '<li>Version control and provenance.</li></ul></div>')
        trained = lambda value=training, source=base: source.replace('<p>Earlier overview.</p>', value)
        bridges = {'budget-training-en', 'budget-training-zh', 'budget-training-one-item'}
        cases += [('budget-training-en', trained(), 'Pilot Lead'),
                  ('budget-training-zh', trained(training.replace('Complete training before publication.', '發布前完成培訓。')
                      .replace('Metadata checks.', '後設資料品質檢核。').replace('Version control and provenance.', '版本控制與資料溯源。')), 'Pilot Lead'),
                  ('budget-training-one-item', trained(training.replace('<li>Metadata checks.</li>', '')), 'Pilot Lead')]
        cases += [('budget-training-'+name, trained(value), 'Pilot Lead') for name, value in [
            ('long', training.replace('Complete training before publication.', 'x' * 161)),
            ('long-item', training.replace('Metadata checks.', '中' * 41)),
            ('three-items', training.replace('</ul>', '<li>Keep this third item.</li></ul>')),
            ('nested', training.replace('Metadata checks.', '<ul><li>Keep nested training.</li></ul>')),
            ('linked', training.replace('Metadata checks.', '<a href="https://example.org">Keep link.</a>')),
            ('unowned', training.replace('specialist-expertise-detail', 'unowned-detail')),
            ('unknown-attribute', training.replace('data-status="complete"', 'data-status="complete" data-extra="unknown"')),
        ]]
        cases += [('budget-training-wide-funding', trained(source=base.replace('Institute.', '中' * 81)), None),
                  ('budget-training-three-rows', trained(source=budget(rows=3)), 'Pilot Lead'),
                  ('budget-training-two-projects', trained(source=base.replace('</table></div>',
                      '</table></div><div class="project-resources"><p>Other project.</p></div>')), None)]
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
        def person(text='Responsibilities: managing data; authorship of the data management plan.',
                   actor='<strong>A. Example</strong>', ending='', attrs=''):
            return ('<div class="person-responsibilities short-reading-unit" data-contributor-id="person" '
                    'data-contributor-index="2"'+attrs+'><p>'+actor+'</p><p>'+text+'</p>'+ending+'</div>')
        cases += [('person-en', person(), 'Pilot Responsibility Summary'),
                  ('person-zh', person('職責：資料管理；資料管理方案的撰寫。', '<strong>範例團隊</strong>'), 'Pilot Responsibility Summary'),
                  ('person-escaped-actor', person(actor='<strong>&lt;Owner&gt; &amp; Team</strong>'), 'Pilot Responsibility Summary'),
                  ('person-later-bold', person('Responsibilities: managing <strong>data</strong>.'), None),
                  ('person-rich-actor', person(actor='<strong><a href="https://example.org">A. Example</a></strong>'), None),
                  ('person-boundary', person('x'*499, '<strong>A</strong>'), 'Pilot Responsibility Summary'),
                  ('person-long', person('x'*501), None),
                  ('person-missing-name-hint', person(ending='<p class="data-gap">Please provide the name.</p>'), None),
                  ('person-link', person('<a href="https://example.org">A. Example</a> manages data.'), None),
                  ('person-no-anchor', person(actor='A. Example'), None),
                  ('person-extra-attribute', person(attrs=' data-extra="original"'), None),
                  ('person-unmarked', person().replace(' short-reading-unit', ''), None),
                  ('person-invalid-index', person().replace('contributor-index="2"', 'contributor-index="0"'), None)]
        lua = (ROOT/'src/word/pilot.lua').read_text()
        call = '  if div.identifier == "q-required-resources" then div = keep_short_budget_narrative(div) end'
        guard = '#div.content == 2 and div.content[2].t == "Para"'
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
        def only_wrapper(left, right, style, bridge=False):
            if left == right: return 0
            if isinstance(left, dict) and isinstance(right, dict):
                if left.get('t') == 'Para' and right.get('t') == 'Div':
                    self.assertIn(right['c'][0], [['',[],[['custom-style',value]]]
                        for value in ([style, 'Pilot List Lead'] if bridge else [style])])
                    self.assertEqual(right['c'][1], [left])
                    return 1
                if bridge and left.get('t') == 'Plain' and right.get('t') == 'Div':
                    self.assertEqual(right['c'], [['',[],[['custom-style','Pilot List Lead']]],[dict(t='Para', c=left['c'])]])
                    return 1
                self.assertEqual(left.keys(), right.keys())
                return sum(only_wrapper(left[k], right[k], style, bridge) for k in left)
            self.assertIsInstance(left, list); self.assertIsInstance(right, list)
            self.assertEqual(len(left), len(right))
            return sum(only_wrapper(a,b,style,bridge) for a,b in zip(left,right))
        self.assertEqual(len(cases), len(old['blocks'])); self.assertEqual(len(cases), len(new['blocks']))
        for (name, _, style), left, right in zip(cases, old['blocks'], new['blocks']):
            with self.subTest(case=name):
                right = copy.deepcopy(right)
                rows = 1 if name == 'budget-one' else 3 if name in ('budget-three', 'budget-training-three-rows') else 2
                self.assertEqual(restore_row_markers(right), rows - 1 if name.startswith('budget-') and style else 0)
                if style is None:
                    self.assertEqual(left, right)
                    if name in ('person-long', 'person-unmarked'):
                        person_blocks = right['c'][1][0]['c'][1]
                        self.assertEqual(person_blocks[0]['c'][0][2], [['custom-style', 'Pilot Label']])
                        self.assertEqual(person_blocks[1]['t'], 'Para')
                else:
                    self.assertEqual(only_wrapper(left,right,style,name in bridges), 2 if name in bridges else 1)
                    if name.startswith('person-'):
                        # Para() already owns the name's all-bold label in both
                        # versions. Q14 adds only the bounded duty paragraph.
                        person_blocks = right['c'][1][0]['c'][1]
                        self.assertEqual(person_blocks[0]['c'][0][2], [['custom-style', 'Pilot Label']])
                        self.assertEqual(person_blocks[1]['c'][0][2], [['custom-style', 'Pilot Responsibility Summary']])
                    if name in bridges:
                        detail = right['c'][1][0]['c'][1][1]['c'][1][0]
                        self.assertEqual(detail['c'][0][2], [['fact-id', 'specialist-expertise-detail'], ['status', 'complete']])
                        self.assertEqual(detail['c'][1][1]['c'][-1][0]['c'][0], ['', [], [['custom-style', 'Pilot List Lead']]])

    def test_short_sources_references_and_contributors_change_only_owned_styles(self):
        from native_support import IMAGE
        source = '<p>Source: <a href="https://example.org/a">https://example.org/a</a></p>'
        def q1(lead='Fixed decision.', location=source, kind='nonreuse', marked=True):
            return ('<div id="q-how-data" class="question" data-requirement-id="SE-1a"><h3>1. Data?</h3>'
                '<div class="answer"><div class="dataset-list"><div class="dataset-section" data-item-id="a">'
                '<h5>Dataset</h5><div class="dataset-source-context' + (' short-dataset-source' if marked else '') +
                '" data-source-kind="' + kind + '"><p>' + lead + '</p>' + location + '</div></div></div></div></div>')
        reference = ('<div class="security-answer-reference short-security-reference"><p>'
            '<a href="#q-store-backup">See question 5.</a></p></div>')
        def q6(tail='<p>Fixed security fact.</p>', ref=reference):
            return ('<div id="q-access-security" class="question"><h3>6. Security?</h3>'
                '<div class="answer short-security-reference-tail"><p>Earlier fact.</p>' + tail + ref + '</div></div>')
        def people(body='<span class="name"><strong>範例人員</strong></span><br><a href="mailto:a@example.org">a@example.org</a><br>Roles: Researcher<br>Affiliation: Institute.'):
            return '<div id="dmp-contributors"><h2>People</h2><ul><li>' + body + '</li></ul></div>'
        def reference_source(body='<p><strong>Data rights holder and contact information</strong></p><p>Contact <a href="https://example.org/contact?a=1&amp;b=2">Original owner</a>.</p>', location=source):
            return ('<div id="q-how-data" class="question" data-requirement-id="SE-1a"><h3>1. Data?</h3>'
                '<div class="answer"><div class="dataset-list"><div class="dataset-section" data-item-id="a"><h5>Dataset</h5>'
                '<div class="answer-detail" data-fact-id="reuse-rightsholder" data-status="complete">' + body + '</div>'
                '<div data-fact-id="reuse-decision" data-status="complete"><div class="dataset-source-context short-dataset-source" '
                'data-source-kind="reference">' + location + '</div><p>Original later policy.</p></div></div></div></div></div>')
        cases = [(q1(), 1), (q1('固定決策。'), 1), (q1('x'*240, '<p>'+'y'*160+'</p>'), 1),
            (q1('中'*120, '<p>'+'文'*80+'</p>'), 1), (q1('x'*241), 0),
            (q1(location='<p>'+'中'*81+'</p>'), 0), (q1(marked=False), 0),
            (q1('<em>Authored decision.</em>'), 0), (q1(kind='unknown'), 0),
            (q1().replace('q-how-data', 'q-other'), 0),
            (q6(), 1), (q6('<p>匿名蒐集資料。</p>'), 1), (q6('<p>'+'中'*80+'</p>'), 1),
            (q6('<p>'+'中'*81+'</p>'), 0), (q6('<div class="answer-detail"><p>Authored.</p></div>'), 0),
            (q6('<p><em>Authored.</em></p>'), 0), (q6(ref=reference.replace('#q-store-backup', '#other')), 0),
            (people(), 1), (people('x'*600), 1), (people('中'*300), 1),
            (people('x'*601), 0), (people('中'*301), 0), (people('a<br>b<br>c<br>d<br>e'), 0),
            (people('<span>a<br>b<br>c<br>d<br>e</span>'), 0),
            (people('<em>Authored emphasis.</em>'), 0), (people().replace('dmp-contributors', 'other'), 0)]
        reference_cases = [(reference_source(), 1), (reference_source('<p>聯絡<a href="mailto:a@example.org">原始權利人</a>。</p>'), 1),
            (reference_source('<p>'+'x'*240+'</p>', '<p>'+'y'*160+'</p>'), 1),
            (reference_source('<p>'+'中'*120+'</p>', '<p>'+'文'*80+'</p>'), 1),
            (reference_source('<p>'+'Earlier authored prose. '*100+'</p><p>Original short final paragraph.</p>'), 1),
            (reference_source('<div custom-style="Pilot Lead"><p>Already kept.</p></div>'), 0),
            (reference_source('<p>'+'x'*241+'</p>'), 0), (reference_source('<p>'+'中'*121+'</p>'), 0),
            (reference_source('<p><em>Original rich paragraph.</em></p>'), 0),
            (reference_source('<p><a href="https://example.org"><em>Original rich link.</em></a></p>'), 0),
            (reference_source('<div><p>Original nested paragraph.</p></div>'), 0),
            (reference_source('<ul><li>Original list.</li></ul>'), 0),
            (reference_source('<table><tr><td>Original table.</td></tr></table>'), 0),
            (reference_source().replace('reuse-rightsholder', 'other-owner'), 0),
            (reference_source().replace('data-fact-id="reuse-decision"', 'class="unknown" data-fact-id="reuse-decision"'), 0),
            (reference_source().replace('data-fact-id="reuse-rightsholder"', 'data-extra="x" data-fact-id="reuse-rightsholder"'), 0),
            (reference_source().replace('data-source-kind="reference"', 'data-source-kind="non-reference"'), 0),
            (reference_source().replace('short-dataset-source', 'unmarked'), 0),
            (reference_source(location='<p>'+'中'*81+'</p>'), 0),
            (reference_source().replace('<div class="dataset-source-context', '<p>Intervening paragraph.</p><div class="dataset-source-context'), 0)]
        reference_start = len(cases)
        cases += reference_cases
        lua = (ROOT/'src/word/pilot.lua').read_text()
        calls = ['  if div.identifier == "q-how-data" then return keep_short_dataset_sources(div) end',
                 '  if div.identifier == "q-access-security" then return keep_short_security_reference(div) end',
                 '  if div.identifier == "dmp-contributors" then return keep_short_contributors(div) end']
        before = lua
        for call in calls:
            self.assertEqual(1, lua.count(call)); before = before.replace(call, '')
        runner = '''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin); result=[]
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'pilot.lua'
 for mode in ['json','docx']:
  for lua in p['variants']:
   f.write_text('FORMAT="'+mode+'"\\n'+lua)
   result.append(json.loads(subprocess.check_output(['pandoc','--from=html','--to=json','--lua-filter='+str(f)],input=p['html'].encode())))
print(json.dumps(result))'''
        results = json.loads(subprocess.check_output(['docker','run','--rm','--pull=never','--network=none',
            '--log-driver=none','-i','--entrypoint','python',IMAGE,'-c',runner], input=json.dumps({
                'variants':[before,lua], 'html':''.join('<div id="case-'+str(i)+'">'+html+'</div>' for i,(html,_) in enumerate(cases))}).encode(), timeout=180))
        owned = {'Pilot Lead', 'Pilot Contributor Summary'}
        def count(value):
            if isinstance(value, dict):
                return int(value.get('t') == 'Div' and any(['custom-style',s] in value['c'][0][2] for s in owned)) + sum(count(v) for v in value.values())
            return sum(count(v) for v in value) if isinstance(value, list) else 0
        def normalize(value):
            if isinstance(value, dict):
                if value.get('t') == 'Div' and any(value['c'][0] == ['',[],[['custom-style',s]]] for s in owned):
                    self.assertEqual(1, len(value['c'][1])); return normalize(value['c'][1][0])
                return {k:('Para' if k=='t' and v=='Plain' else normalize(v)) for k,v in value.items()}
            return [normalize(v) for v in value] if isinstance(value, list) else value
        def rights_holder(value):
            if isinstance(value, dict):
                if value.get('t') == 'Div' and ['fact-id', 'reuse-rightsholder'] in value['c'][0][2]: return value
                for child in value.values():
                    found = rights_holder(child)
                    if found is not None: return found
            elif isinstance(value, list):
                for child in value:
                    found = rights_holder(child)
                    if found is not None: return found
        for mode, old, new in [('json',*results[:2]), ('docx',*results[2:])]:
            self.assertEqual(len(cases), len(new['blocks']))
            for i, ((_, expected), left, right) in enumerate(zip(cases,old['blocks'],new['blocks'])):
                with self.subTest(mode=mode, case=i):
                    self.assertEqual(expected, count(right)-count(left))
                    self.assertEqual(normalize(left), normalize(right))
                    if not expected: self.assertEqual(left,right)
                    elif i >= reference_start:
                        before_holder, after_holder = rights_holder(left), rights_holder(right)
                        self.assertEqual(before_holder['c'][1][:-1], after_holder['c'][1][:-1])
                        self.assertEqual(after_holder['c'][1][-1], {'t':'Div', 'c':[
                            ['',[],[['custom-style','Pilot Lead']]], [before_holder['c'][1][-1]]]})

    def test_question_hierarchy_is_scoped_without_smaller_body_text(self):
        css = (ROOT/'src/layout.css').read_text()
        self.assertIn('html body .question > h3 { font-size: 11.5pt; font-weight: bold; color: #000; }', css)
        self.assertIn('html body { font-size: 10.5pt; line-height: 1.5; color: #222; }', css)
        self.assertIn('html body .dataset-list h5 { font-size: 11pt;', css)

    def test_review_diagnostic_and_restricted_permission_keep_only_their_leads(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from native_support import IMAGE, RUNNER
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
        from current_support import environment
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        env = environment(ROOT, True)
        env.filters['datetime_format'] = lambda value, fmt: '2026-09-22'
        provenance = env.from_string("{% import 'src/macros.html.j2' as macros with context %}"
            "{% include 'src/document-provenance.html.j2' %}").render(dc=dict(
            project=dict(name='Workspace label'), document=dict(created_at=''),
            pkg=dict(name='Coastal KM', version='2.7.0', organization_id='dsw', km_id='root'),
            config=dict(service_name='DMP service', service_url='https://example.org/?a=1&b=2')),
            ctx=dict(project={}, phaseUuid=None), km={}, output_profile='review')
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
            ('real-include-three', owned(provenance), True),
            ('current-three', owned(current(['Project: Original workspace',
                'Knowledge model: Coastal KM', 'Generated with '+final_link+'.'])), True),
            ('current-five', owned(current_five), True),
            ('current-chinese', owned(current(['文件名稱：原始名稱', '文件建立日期：2026-09-22',
                '計畫階段：規劃', '問卷知識模型：沿岸觀測', '本文件由 '+final_link+' 產生。'])), True),
            ('current-paragraph-boundary', owned(current(['x'*320, 'Date', 'KM', final_link])), True),
            ('current-cjk-boundary', owned(current(['中'*160, '日期', '模型', final_link])), True),
            ('current-total-boundary', owned(current(['x'*300, 'y'*300, 'z'*299, final_link])), True),
            ('current-paragraph-too-long', owned(current(['x'*321, 'Date', 'KM', final_link])), False),
            ('current-cjk-too-wide', owned(current(['中'*161, '日期', '模型', final_link])), False),
            ('current-total-too-long', owned(current(['x'*300, 'y'*300, 'z'*300, final_link])), False),
            # Pandoc drops the empty HTML paragraph before this Lua guard.
            ('current-empty-html-paragraph-dropped', owned(current(['', 'Date', 'KM', final_link])), True),
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
                if name == 'current-empty-html-paragraph-dropped':
                    self.assertEqual(3, len(old_target['c'][1]))
                    self.assertTrue(all(p['t'] == 'Para' and p['c'] for p in old_target['c'][1]))
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

    def test_pdf_review_provenance_boundary_keeps_tail_and_allows_long_content(self):
        import os
        css = (ROOT / 'src/layout.css').read_text()
        rule = ('html body article.dmp.pdf-flow-layout > aside.document-provenance.pdf-short-provenance '
                '{ break-before: avoid; }')
        self.assertEqual(css.count(rule), 1)
        images = [
            ('69.0', 'datastewardshipwizard/document-worker@sha256:06707194979a80981b1308f618716bc3a6640c4ff1039d85e5971690d51606a2'),
            ('70.0', 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'),
        ]
        runner = '''import json,sys,weasyprint
from weasyprint import HTML
p=json.load(sys.stdin)
assert weasyprint.__version__==p['version']
before=p['css'].replace(p['rule'],'',1)
facts=['specialist-expertise','hardware-software','repository-charges','resources-costing']
gaps=''.join('<p class="data-gap" data-fact-id="'+fact+'" data-status="missing">Q15 '+fact+' missing.</p>' for fact in facts)
metadata='<aside class="document-provenance pdf-short-provenance">'+''.join('<p>Metadata '+value+'.</p>' for value in ['project','phase','model','<a href="https://example.org/">service</a>'])+'</aside>'
def body(answer=gaps,trace=metadata,marker=' pdf-flow-layout',height=210):
 return ('<article class="dmp'+marker+'"><div id="dmp-content"><div style="height:'+str(height)+'mm"></div>'
   '<section class="dmp-section"><div id="q-required-resources" class="question"><h3>15. Tail resources?</h3>'
   '<div class="answer">'+answer+'</div></div></section></div>'+trace+'</article>')
def inspect(source,css):
 doc=HTML(string='<html><head><style>'+css+'</style></head><body>'+source+'</body></html>').render()
 rows=[]
 for page_index,page in enumerate(doc.pages):
  for box in page._page_box.descendants():
   if type(box).__name__=='TextBox':
    left=page._page_box.content_box_x(); right=left+page._page_box.width
    assert box.position_x>=left-1 and box.position_x+box.width<=right+1,('overflow',box.text)
    rows.append((page_index,box.text,box.position_x,box.position_y,box.width,box.height))
 return len(doc.pages),rows
def text(rows): return ''.join(''.join(row[1] for row in rows).split())
def paired(source,name):
 old=inspect(source,before); new=inspect(source,p['css'])
 assert text(old[1])==text(new[1]),(name,'original text changed')
 assert new[0]<=old[0],(name,'page count increased',old[0],new[0])
 return old,new
found=None
for height in range(200,241):
 old=inspect(body(height=height),before)
 last=' '.join(row[1] for row in old[1] if row[0]==old[0]-1)
 if old[0]>1 and 'Metadata' in last and 'Q15' not in last and 'Tail resources' not in last:
  found=height; break
assert found is not None,'no metadata-only control near the page boundary'
old,new=paired(body(height=found),'short-tail')
last=' '.join(row[1] for row in new[1] if row[0]==new[0]-1)
assert 'Metadata' in last and 'Q15' in last,('metadata-only tail persists',last)
for name,source in [('unmarked',body(marker='',height=found)),('submission',body(trace='',height=found))]:
 old,new=paired(source,name)
 assert old==new,(name,'ordinary layout changed')
paragraphs=''.join('<p>Authored paragraph '+str(i)+' retains the original answer and continues naturally across pages.</p>' for i in range(48))
table='<table><tbody>'+''.join('<tr><td>Original table row '+str(i)+'</td><td>Original allocation.</td></tr>' for i in range(48))+'</tbody></table>'
oversized='<aside class="document-provenance">'+''.join('<p>Metadata overflow row '+str(i)+' retains the original value.</p>' for i in range(80))+'</aside>'
for name,source,token in [
 ('long-answer',body(answer=paragraphs,height=found),'Authored paragraph'),
 ('terminal-table',body(answer=table,height=found),'Original table row')]:
 old,new=paired(source,name)
 assert len({row[0] for row in new[1] if token in row[1]})>1,(name,'unbounded content was kept whole')
# True Jinja classifier tests separately prove these long traces never get the marker.
long_value='<p>'+('Long metadata value '*300)+'</p>'
for name,trace,token in [('many-paragraphs',oversized,'Metadata overflow row')]+[
 ('long-'+str(count)+'-paragraphs','<aside class="document-provenance">'+long_value+'<p>Short metadata.</p>'*(count-1)+'</aside>','Long metadata value') for count in (3,4)]:
 assert 'pdf-short-provenance' not in trace
 old,new=paired(body(trace=trace,height=found),name)
 assert old==new,(name,'unmarked long metadata layout changed')
 assert len({row[0] for row in new[1] if token in row[1]})>1,(name,'long metadata did not flow')
print(json.dumps({'passed':True,'cases':8,'boundary_spacer_mm':found}))
'''
        for version, image in images:
            with self.subTest(image=image):
                command = ['docker', 'run', '--rm', '--pull=never', '--network=none', '--read-only',
                    '--cap-drop=ALL', '--security-opt=no-new-privileges', '--log-driver=none',
                    '--tmpfs', '/tmp:rw,size=768m', '--user', f'{os.getuid()}:{os.getgid()}',
                    '-e', 'PYTHONDONTWRITEBYTECODE=1',
                    '-e', 'PYTHONPATH=/home/user/.local/lib/python3.14/site-packages:/usr/local/lib/python3.14/site-packages',
                    '-i', '--entrypoint', 'python', image, '-B', '-c', runner]
                raw = subprocess.check_output(command, input=json.dumps(
                    dict(css=css, rule=rule, version=version)).encode(), timeout=240)
                result = json.loads(raw)
                self.assertTrue(result['passed'])
                self.assertEqual(8, result['cases'])
                self.assertIn(result['boundary_spacer_mm'], range(200, 241))

    def test_fixed_list_leads_keep_only_the_intro_without_changing_list_xml(self):
        import base64
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from native_support import IMAGE, WORD_RUNNER as RUNNER
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
            self.assertEqual(1, source.count('<div class="answer-lead"><p>{{ pgettext("questions/' + filename + '", "' + english + '") }}</p></div>'))
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
        from native_support import IMAGE, WORD_RUNNER as RUNNER
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
        guard = 'return display_width(block) <= 160'
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
        from native_support import IMAGE
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
        import native_support as worker
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
        import native_support as worker
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        from current_support import install_i18n
        install_i18n(env, ROOT)
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
        import native_support as worker
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        from current_support import install_i18n
        install_i18n(env, ROOT)
        env.filters['datetime_format'] = lambda value, fmt: '30 Sep 2026'
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% include 'src/versions.html.j2' %}{% include 'src/document-provenance.html.j2' %}")
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
            cases.append(dict(name=name, html=template.render(dc=dc, km={}, ctx=dict(phaseUuid=None),
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
                self.assertEqual(20, document.styles["Heading 1"].font.size.pt)
                self.assertEqual(25, title.line_spacing.pt)
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
                guidance = document.styles['Pilot Question Guidance']
                self.assertEqual('Pilot Provenance', guidance.base_style.name)
                self.assertEqual(10, guidance.font.size.pt)
                self.assertTrue(guidance.paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Label"].paragraph_format.keep_with_next)
                budget_label = document.styles["Pilot Budget Label"]
                self.assertEqual('Body Text', budget_label.base_style.name)
                self.assertTrue(budget_label.paragraph_format.keep_with_next)
                self.assertEqual(0, budget_label.paragraph_format.space_before.pt)
                self.assertEqual(3, budget_label.paragraph_format.space_after.pt)
                self.assertIsNone(budget_label.paragraph_format.line_spacing)
                self.assertEqual(4, document.styles["Pilot Label"].paragraph_format.space_before.pt)
                self.assertTrue(document.styles["Pilot Lead"].paragraph_format.keep_with_next)
                for mode in ('Detail', 'Record'):
                    for suffix in ('', ' Lead', ' Label'):
                        style = document.styles['Pilot Reading ' + mode + suffix]
                        self.assertAlmostEqual(4, style.paragraph_format.left_indent.mm, places=2)
                        self.assertAlmostEqual(-4 if mode == 'Record' else 0,
                                               style.paragraph_format.first_line_indent.mm, places=2)
                        self.assertIsNone(style.paragraph_format.keep_together)
                self.assertTrue(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_together)
                self.assertFalse(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_with_next)
                self.assertEqual('Body Text', document.styles["Pilot Responsibility Summary"].base_style.name)
                for name, keep_next in [('Pilot Responsibility Lead', True), ('Pilot Responsibility Item', False)]:
                    self.assertEqual('Compact', document.styles[name].base_style.name)
                    self.assertEqual(keep_next, document.styles[name].paragraph_format.keep_with_next)
                    self.assertTrue(document.styles[name].paragraph_format.keep_together)
                    self.assertEqual(0, document.styles[name].paragraph_format.space_before.pt)
                    self.assertEqual(0, document.styles[name].paragraph_format.space_after.pt)
                    self.assertIsNone(document.styles[name].paragraph_format.line_spacing)
                    self.assertIsNone(document.styles[name].font.size)
                self.assertEqual('Compact', document.styles["Pilot Contributor Summary"].base_style.name)
                self.assertTrue(document.styles["Pilot Contributor Summary"].paragraph_format.keep_together)
                self.assertFalse(document.styles["Pilot Contributor Summary"].paragraph_format.keep_with_next)
                self.assertNotIn('Pilot Contributor Compact', document.styles)
                self.assertTrue(document.styles["Pilot List Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_together)
                self.assertTrue(document.styles["Pilot Repository Lead"].paragraph_format.keep_with_next)
                self.assertFalse(document.styles["Pilot Repository Item"].paragraph_format.keep_with_next)
                for name in ["Pilot Repository Lead", "Pilot Repository Item"]:
                    self.assertTrue(document.styles[name].paragraph_format.keep_together)
                    self.assertEqual('Compact', document.styles[name].base_style.name)
                self.assertFalse(document.styles["Heading 4"].font.italic)
                for name in ("Hyperlink", "FollowedHyperlink"):
                    self.assertEqual('185778', str(document.styles[name].font.color.rgb))
                question = document.styles["Heading 3"]
                self.assertEqual(11.5, question.font.size.pt)
                self.assertTrue(question.font.bold)
                self.assertEqual('000000', str(question.font.color.rgb))
                self.assertEqual(0, document.styles["Body Text"].paragraph_format.space_before)
                for style_name in ("Normal", "Body Text", "First Paragraph", "Compact"):
                    item = document.styles[style_name]
                    self.assertEqual(10.5, item.font.size.pt)
                    self.assertEqual(14.5, item.paragraph_format.line_spacing.pt)
                    self.assertEqual(WD_LINE_SPACING.AT_LEAST, item.paragraph_format.line_spacing_rule)
                    lang = item.element.rPr.find(qn('w:lang'))
                    self.assertEqual('en-GB', lang.get(qn('w:val')))
                    self.assertEqual('zh-TW', lang.get(qn('w:eastAsia')))
                    self.assertEqual(2 if style_name == "Compact" else 4, item.paragraph_format.space_after.pt)
                    self.assertTrue(item.paragraph_format.widow_control)
                for level in range(1, 6):
                    item = document.styles[f"Heading {level}"].paragraph_format
                    self.assertEqual((25, 18.75, 14.5, 14, 13.5)[level - 1], item.line_spacing.pt)
                    self.assertEqual(WD_LINE_SPACING.AT_LEAST, item.line_spacing_rule)
                    self.assertEqual(12 if level == 1 or level >= 4 else 14, item.space_before.pt)
                    self.assertEqual(2 if level >= 4 else 3 if level == 3 else 5 if level == 2 else 6, item.space_after.pt)
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
                self.assertEqual(14.5, d.styles[name].paragraph_format.line_spacing.pt)
                self.assertEqual(WD_LINE_SPACING.AT_LEAST, d.styles[name].paragraph_format.line_spacing_rule)
                self.assertEqual(10.5, d.styles[name].font.size.pt)
            self.assertEqual('en-GB', d.styles['Normal'].element.rPr.find(qn('w:lang')).get(qn('w:val')))
            self.assertIsNone(d.styles['Pilot Contributor Summary'].paragraph_format.line_spacing)

    def test_runtime_locale_styles_match_prepared_reference(self):
        import base64
        from xml.etree import ElementTree as E
        from native_support import IMAGE
        references = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            font = root / 'font.ttf'; font.write_bytes(b'fixture font asset')
            for language in ('en', 'zh-Hant'):
                folder = root / language
                (folder / 'src/word').mkdir(parents=True)
                for relative in ('src/layout.css', 'src/word/reference.docx'):
                    shutil.copyfile(ROOT / relative, folder / relative)
                module.prepare_layout(folder, font, language)
                references.append(base64.b64encode((folder / 'src/word/reference.docx').read_bytes()).decode())
        runner = '''import base64,json,sys,tempfile,subprocess,zipfile
from pathlib import Path
styles=[]
with tempfile.TemporaryDirectory() as tmp:
 ref=Path(tmp)/'reference.docx';out=Path(tmp)/'test.docx'
 for value in json.load(sys.stdin):
  ref.write_bytes(base64.b64decode(value))
  subprocess.run(['pandoc','--from=html','--to=docx','--reference-doc='+str(ref),'-o',str(out)],input=b'<h1>Title</h1><p>Mixed English and Chinese.</p>',check=True)
  with zipfile.ZipFile(out) as z: styles.append(z.read('word/styles.xml').decode())
print(json.dumps(styles))
'''
        english, chinese = json.loads(subprocess.check_output(
            ['docker', 'run', '--rm', '--pull=never', '--network=none', '--log-driver=none', '-i',
             '--entrypoint', 'python', IMAGE, '-c', runner], input=json.dumps(references).encode(), timeout=180))
        # A Pandoc/author-added style must survive, including its own language.
        custom = '<w:style w:type="paragraph" w:styleId="CustomAuthor"><w:rPr><w:lang w:val="fr-FR" /></w:rPr></w:style>'
        english = english.replace('</w:styles>', custom + '</w:styles>')
        chinese = chinese.replace('</w:styles>', custom + '</w:styles>')
        for escape in (False, True):
            template = Environment(loader=FileSystemLoader(ROOT), undefined=StrictUndefined,
                autoescape=escape).get_template('src/word/locale-styles.xml.j2')
            for language in ('en', 'zh-Hant'):
                rendered = template.render(content=english, ctx={'document': {'language': language}})
                self.assertIn(custom, rendered)
                self.assertEqual(english, rendered)
                self.assertEqual(E.canonicalize(chinese), E.canonicalize(rendered))
            # With no locale rewrite, even renamed/author-modified styles must
            # survive. There is no serializer-dependent spacing to validate.
            for authored in (english.replace('w:styleId="Normal"', 'w:styleId="RenamedNormal"'),
                             english.replace('w:line="290"', 'w:line="295"')):
                for language in ('en', 'zh-Hant'):
                    self.assertEqual(authored, template.render(content=authored,
                        ctx={'document': {'language': language}}))
