"""Discovered by make check; the same registry is used for bilingual CI."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from check_current import SUITES, run_suite
from current_support import environment


class CurrentI18nTests(unittest.TestCase):
    def catalog_root(self, parent, language='zh-Hant'):
        import polib
        root = Path(parent)
        target = root / 'src/i18n/zh-Hant/LC_MESSAGES/dsw.mo'
        target.parent.mkdir(parents=True)
        catalog = polib.POFile()
        catalog.metadata = {'Language': language, 'Content-Type': 'text/plain; charset=UTF-8'}
        catalog.append(polib.POEntry(msgctxt='example', msgid='Hello world', msgstr='世界，你好'))
        catalog.append(polib.POEntry(msgctxt='example', msgid='<strong>Hello</strong> %(who)s',
                                    msgstr='<strong>你好</strong> %(who)s'))
        target.write_bytes(catalog.to_binary())
        return root

    def test_default_null_english_is_explicit_and_ignores_embedded_chinese(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            root = self.catalog_root(folder)
            env = environment(root)
            self.assertEqual('en', env.globals['document_language'])
            self.assertEqual(env.from_string("{{ pgettext('example', 'Hello world') }}").render(),
                             'Hello world')
            self.assertEqual(env.from_string('{% trans %}Missing English key{% endtrans %}').render(),
                             'Missing English key')

    def test_embedded_mo_context_trimmed_policy_and_escaping(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            root = self.catalog_root(folder)
            for escape in (False, True):
                env = environment(root, escape, language='zh-Hant')
                self.assertEqual('zh-Hant', env.globals['document_language'])
                self.assertEqual(env.from_string("{% trans 'example' %}Hello\n  world{% endtrans %}").render(),
                                 '世界，你好')
                actual = env.from_string(
                    "{{ pgettext('example', '<strong>Hello</strong> %(who)s', who=who) }}").render(who='<A&B>')
                self.assertEqual(actual, '<strong>你好</strong> ' + ('&lt;A&amp;B&gt;' if escape else '<A&B>'))
                self.assertNotIn('&amp;lt;', actual)

    def test_missing_catalog_or_key_never_falls_back_to_english(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                environment(folder, language='zh-Hant')
            env = environment(self.catalog_root(folder), language='zh-Hant')
            for source in ("{{ pgettext('wrong-context', 'Hello world') }}",
                           "{{ pgettext('example', 'Missing key') }}", "{{ gettext('Hello world') }}"):
                with self.assertRaises(LookupError):
                    env.from_string(source).render()

    def test_unknown_language_and_wrong_catalog_language_are_rejected(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            root = self.catalog_root(folder, language='en')
            with self.assertRaises(ValueError):
                environment(root, language='zh-Hant')
            for language in ('', 'zh', 'zh-TW', 'unknown'):
                with self.assertRaises(ValueError):
                    environment(root, language=language)


class CurrentBudgetLayoutTests(unittest.TestCase):
    def test_funding_tables_are_full_width_owned_and_preserve_exact_fragments(self):
        from lxml import html
        from markupsafe import Markup
        header = Markup('<tr><th>Resource</th><th>Budget</th><th>Funding</th></tr>')
        metadata = Markup('<th>Resource</th><th>Budget</th>')
        funding = Markup('<p>Original funding.</p><table><tbody><tr><td>FUND-01</td><td>10</td></tr></tbody></table><p>Original tail.</p>')
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/budget-reading.html.j2').module
            for word in [False, True]:
                render = helper.word_table if word else helper.render
                for purpose in ['', '<p>Keep data.</p>', '<p><img src="diagram.png" alt="Allocation chart"></p>',
                                '<table><tbody><tr><td>ROW-01</td><td>10</td></tr></tbody></table>']:
                    first = dict(id='original-first', title=Markup('<p>Resource 1</p>'),
                                 purpose=Markup(purpose), budget=Markup(''), funding=funding)
                    second = dict(id='original-second', title=Markup('<p>A&lt;B&amp;C&gt;D</p>'),
                                  purpose=Markup('<ul><li>Original purpose.</li></ul>'),
                                  budget=Markup('<p>0 TWD</p>'), funding=Markup('<p>Institution.</p>'))
                    second['original'] = Markup('<tr data-item-id="original-second"><td>'+str(second['title'])+str(second['purpose'])+'</td><td>'+str(second['budget'])+'</td><td>'+str(second['funding'])+'</td></tr>')
                    markup = str(render(Markup('must not use nested original'), header,
                                        [first, second], metadata, Markup('Funding')))
                    document = html.fragment_fromstring(markup, create_parent=True)
                    self.assertEqual([n.tag for n in document], ['table']+(['div'] if purpose else [])+['div','table'])
                    table = document[0]
                    self.assertEqual(table.get('class'), ('word' if word else 'pdf')+'-rich-funding-metadata')
                    self.assertEqual(table.xpath('./tbody/tr/@data-item-id'), ['original-first'])
                    self.assertEqual(table.xpath('./thead/tr/th/text()'), ['Resource','Budget'])
                    cells = table.xpath('./tbody/tr/td')
                    self.assertEqual(len(cells), 2)
                    self.assertEqual(''.join(html.tostring(n, encoding='unicode') for n in cells[0]), str(first['title']))
                    self.assertFalse(''.join(cells[1].itertext()))
                    if purpose:
                        self.assertEqual(document[1].get('data-item-id'), 'original-first')
                        self.assertEqual(''.join(html.tostring(n, encoding='unicode') for n in document[1]), purpose)
                    detail = document[-2]
                    self.assertEqual(detail.get('data-item-id'), 'original-first')
                    self.assertEqual(detail.get('class'), 'word-rich-resource-funding' if word else 'pdf-rich-funding-detail')
                    self.assertEqual(''.join(html.tostring(n, encoding='unicode') for n in list(detail)[1:]), str(funding))
                    self.assertEqual(document[-1].xpath('./tbody/tr/@data-item-id'), ['original-second'])
                    for cell, fragment in zip(document[-1].xpath('./tbody/tr/td'),
                                              [str(second['title'])+str(second['purpose']), str(second['budget']), str(second['funding'])]):
                        self.assertEqual(''.join(html.tostring(n, encoding='unicode') for n in cell), fragment)

    def test_added_labels_leave_all_non_funding_table_routes_byte_exact(self):
        from markupsafe import Markup
        header = Markup('<tr><th>Resource</th><th>Budget</th><th>Funding</th></tr>')
        original = Markup('<table class="resource-table"><tbody><tr><td>Original exact output.</td></tr></tbody></table>')
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/budget-reading.html.j2').module
            for purpose in ['', '<p>Keep data.</p>', '<table><tbody><tr><td>ROW-01</td><td>10</td></tr></tbody></table>', '<p>Keep data.</p>'*20]:
                row = dict(id='original-id', title=Markup('<p>Resource 1</p>'),
                           purpose=Markup(purpose), budget=Markup('<p>0 TWD</p>'),
                           funding=Markup('<p>Literal &lt;table&gt; text.</p>'), original=Markup('<tr><td>Exact row.</td></tr>'))
                for render in [helper.word_table, helper.render]:
                    self.assertEqual(str(render(original, header, [row], Markup('<th>Resource</th><th>Budget</th>'), Markup('Funding'))),
                                     str(render(original, header, [row])))

    def test_word_without_authored_table_keeps_exact_existing_fallback(self):
        from markupsafe import Markup
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/budget-reading.html.j2').module
            for purpose in ['', '<p>Keep data.</p>', '<p>&lt;table&gt; is literal text.</p>',
                            '<ul><li>Keep data</li></ul>', '<p>' + 'Long text. ' * 100 + '</p>']:
                row = dict(id='original-id', title=Markup('<p>Resource 1</p>'),
                           purpose=Markup(purpose), budget=Markup(''), funding=Markup(''))
                original = Markup('<table class="resource-table"><tbody><tr><td>Unchanged</td></tr></tbody></table>')
                self.assertEqual(str(helper.word_table(original, Markup(''), [row])),
                                 str(helper.short_table(original, [row], True)))
            self.assertEqual(str(helper.word_table(Markup('unchanged'), Markup(''), [])), 'unchanged')

    def test_word_authored_table_keeps_every_resource_fragment_and_identity(self):
        from lxml import html
        from markupsafe import Markup
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/budget-reading.html.j2').module
            rows = [dict(id='first', title=Markup('<p>Resource 1</p>'),
                         purpose=Markup('<table><tbody><tr><td>A&lt;B&amp;C&gt;D</td></tr></tbody></table>'),
                         budget=Markup(''), funding=Markup('')),
                    dict(id='second', title=Markup('<p>Named resource</p>'),
                         purpose=Markup('<ol><li>Keep original</li></ol>'),
                         budget=Markup('<p>0 TWD</p>'), funding=Markup('<p>Institution</p>'))]
            header = Markup('<tr><th>Resource</th><th>Budget</th><th>Funding</th></tr>')
            document = html.fragment_fromstring(str(helper.word_table(Markup('old table'), header, rows)), create_parent=True)
            self.assertEqual([node.tag for node in document], ['table', 'div', 'table', 'div'])
            for index, row in enumerate(rows):
                table, purpose = document[index * 2:index * 2 + 2]
                self.assertEqual(table.xpath('./tbody/tr/@data-item-id'), [row['id']])
                self.assertEqual(purpose.get('data-item-id'), row['id'])
                self.assertEqual(table.xpath('./thead/tr/th/text()'), ['Resource', 'Budget', 'Funding'])
                for cell, key in zip(table.xpath('./tbody/tr/td'), ['title', 'budget', 'funding']):
                    self.assertEqual(''.join(html.tostring(child, encoding='unicode') for child in cell), str(row[key]))
                self.assertEqual(''.join(html.tostring(child, encoding='unicode') for child in purpose), str(row['purpose']))

    def test_bounded_table_hint_preserves_question_grouping_and_rejections(self):
        from markupsafe import Markup
        from short_resources_cases import cases
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/pdf/short-resources.html.j2').module
            for name, original, _ in cases():
                marked = original.replace('class="resource-table"', 'class="resource-table pdf-bounded-budget"')
                actual = str(helper.document(Markup(marked))).replace('class="resource-table pdf-bounded-budget"', 'class="resource-table"')
                self.assertEqual(actual, str(helper.document(Markup(original))), name)

    def test_owned_row_hint_keeps_only_the_existing_short_question_grammar(self):
        import re
        from markupsafe import Markup
        from short_resources_cases import cases, fragment
        from short_resources_cases import OPENING, HINT
        suffix = ' class="pdf-short-resource-row" style="break-inside: avoid"'
        marked = lambda value: re.sub(r'(<tr data-item-id="[^"]+")>', r'\1' + suffix + '>', value)
        rows = [(name, marked(original), selected) for name, original, selected in cases()]
        base = marked(fragment())
        rows += [(name, source, False) for name, source in [
            ('unknown-row-class', base.replace('pdf-short-resource-row', 'unknown-row')),
            ('unknown-row-style', base.replace('style="break-inside: avoid"', 'style="break-inside: auto"')),
            ('extra-row-attribute', base.replace(suffix, ' data-extra="unknown"' + suffix)),
            ('invalid-row-identity', base.replace('data-item-id="aa.0"', 'data-item-id="not-owned"')),
            ('long-training', base.replace('Training details.', 'x' * 161)),
            ('wide-funding', base.replace('Funds.', '中' * 41)),
        ]]
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/pdf/short-resources.html.j2').module
            for name, source, selected in rows:
                with self.subTest(autoescape=escape, case=name):
                    self.assertEqual(str(helper.document(Markup(source))),
                                     source.replace(OPENING, HINT, 1) if selected else source)

    def test_only_bounded_content_gets_whole_table_keep(self):
        from markupsafe import Markup
        original = Markup('<table class="resource-table"><tbody><tr><td>Unchanged</td></tr></tbody></table>')
        row = dict(title='<p>Storage</p>', purpose='<p>Retain data.</p>',
                   budget='<p>100 TWD</p>', funding='<p>Institution</p>')
        for escape in [False, True]:
            template = environment(ROOT, escape).from_string(
                "{% import 'src/budget-reading.html.j2' as budget %}{{ budget.short_table(original, rows, word) }}")
            for word in [False, True]:
                for rows, bounded in [([row], True), ([row] * 3, True), ([row] * 4, False),
                        ([dict(row, budget='', funding='  \n')], True),
                        ([row, dict(row, funding='')], True),
                        ([dict(row, title='')], False), ([dict(row, purpose='')], False),
                        ([dict(row, funding='<p></p>')], False),
                        ([dict(row, budget='<p style="height:1000px">0</p>')], False),
                        ([dict(row, purpose='<p>' + 'Long description. ' * 100 + '</p>')], False),
                        ([dict(row, purpose='<p>Paragraph</p>' * 16)], False),
                        ([dict(row, purpose='<p><img src="chart.png"></p>')], False)]:
                    expected = str(original)
                    if bounded and not word:
                        expected = expected.replace('class="resource-table"', 'class="resource-table pdf-bounded-budget"')
                    self.assertEqual(template.render(original=original, rows=rows, word=word), expected)


class CurrentResponsibilityAnchorTests(unittest.TestCase):
    def test_one_owned_actor_anchor_keeps_every_selected_duty(self):
        from lxml import html
        from check_responsibility_reading import ROLES, contributor_replies, responsibility_summary
        from current_support import PREFIX

        cases = [
            [('first-role-' + str(index), 'Owner', ROLES[index:])]
            for index in range(len(ROLES))
        ] + [
            [('same-a', 'Same Name', ROLES), ('same-b', 'Same Name', ROLES[1:])],
            [('prose', 'data', ROLES)],
            [('markup', '<strong>Owner</strong> & "Team" <script>x</script>', ROLES)],
            [('roles', 'Owner', list(reversed(ROLES)) + [ROLES[0]])],
            [('blank', ' \n ', ROLES), ('missing', None, ROLES[2:])],
        ]
        for escape in [False, True]:
            template = environment(ROOT, escape).from_string(
                PREFIX + "{% include 'src/questions/14-dm-responsible.html.j2' %}")
            for profile in ['review', 'submission']:
                for people in cases:
                    with self.subTest(autoescape=escape, profile=profile, people=people):
                        document = html.fragment_fromstring(template.render(
                            repliesMap=contributor_replies(people), output_profile=profile), create_parent=True)
                        nodes = document.xpath('.//div[contains(concat(" ", @class, " "), " person-responsibilities ")]')
                        self.assertEqual(len(nodes), len(people))
                        for index, (node, (item, name, roles)) in enumerate(zip(nodes, people), 1):
                            actor = name if name and name.strip() else 'Contributor ' + str(index)
                            summary, = node.xpath('./p[@class="responsibility-summary"]')
                            actor_label, = node.xpath('./p[@class="responsible-person"]')
                            owner, = actor_label.xpath('./strong')
                            self.assertEqual(list(actor_label), [owner])
                            self.assertFalse(actor_label.text)
                            self.assertEqual(''.join(owner.itertext()), actor)
                            self.assertFalse(list(owner))
                            self.assertFalse(list(summary))
                            self.assertEqual(''.join(summary.itertext()), responsibility_summary(roles, 'en'))
                            self.assertEqual(summary.get('data-role-uuids').split(),
                                             [role for role in ROLES if role in roles])
                            self.assertEqual(node.get('data-contributor-id'), item)
                            self.assertEqual(len(node.xpath('./p[@class="data-gap"]')),
                                             int(profile == 'review' and not (name and name.strip())))
                        self.assertFalse(document.xpath('.//script | .//img'))

    def test_contributor_keep_hint_accepts_only_bounded_scalar_records(self):
        from lxml import html
        from check_responsibility_reading import contributor_replies
        from current_support import PREFIX, path

        filename = 'src/contributors.html.j2'
        source = (ROOT / filename).read_text()
        self.assertEqual(1, source.count(' short-contributor'))
        cases = [
            ('plain', 'Original Institute.', True),
            ('linked', '<a href="https://example.org/?a=1&amp;b=2">Original Institute.</a>', True),
            ('inline', '<span><strong>Original Institute.</strong></span>', True),
            ('three-breaks', 'Original<br>Institute<br>Division', True),
            ('affiliation-list', '<ul>' + ''.join('<li>Original ' + str(i) + '</li>' for i in range(30)) + '</ul>', False),
            ('ordered-list', '<ol><li>Original Institute.</li></ol>', False),
            ('paragraph', '<div><p>Original paragraph.</p></div>', False),
            ('pre', '<pre>Original\ncode.</pre>', False),
            ('image', '<img src="unfetched.png" alt="Original diagram">', False),
            ('long-latin', 'x' * 601, False),
            ('long-cjk', '中' * 301, False),
            ('four-breaks', 'Original<br>Institute<br>Division<br>Team', False),
        ]
        for escape in [False, True]:
            templates = [environment(ROOT, escape, overrides).from_string(PREFIX + "{% include '" + filename + "' %}")
                         for overrides in [None, {filename: source.replace(' short-contributor', '', 1)}]]
            for name, affiliation, selected in cases:
                with self.subTest(autoescape=escape, case=name):
                    replies = contributor_replies([('person', 'Original person', [])])
                    replies[path('adminDetailsCUuid', 'contributorsQUuid', 'person', 'contributorAffiliationQUuid')] = {
                        'value': {'value': {'type': 'IntegrationType', 'value': affiliation, 'raw': None}}}
                    context = dict(repliesMap=replies, output_profile='review',
                                   dc={'project': {'created_by': None}, 'e': {'choices': {}}})
                    actual, baseline = [template.render(**context) for template in templates]
                    self.assertEqual(baseline, actual.replace(' short-contributor', ''))
                    document = html.fragment_fromstring(actual, create_parent=True)
                    record, = document.xpath('.//div[@id="dmp-contributors"]/ul/li')
                    self.assertEqual(selected, 'short-contributor' in record.get('class').split())
                    self.assertIn('Original person', ''.join(record.itertext()))


class CurrentBehaviorTests(unittest.TestCase):
    pass




def test_suite(name):
    def test(self):
        run_suite(name, ROOT, 'en')
    return test


for name in SUITES:
    setattr(CurrentBehaviorTests, 'test_' + name, test_suite(name))


if __name__ == '__main__': unittest.main()
