"""Discovered by make check; the same registry is used for bilingual CI."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from check_current import SUITES, run_suite
from current_repairs_contract import project_source, source_tree
from current_support import environment


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
                for purpose in ['', '<p>Keep data.</p>', '<table><tbody><tr><td>ROW-01</td><td>10</td></tr></tbody></table>']:
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
        from probe_short_resources import cases
        for escape in [False, True]:
            helper = environment(ROOT, escape).get_template('src/pdf/short-resources.html.j2').module
            for name, original, _ in cases():
                marked = original.replace('class="resource-table"', 'class="resource-table pdf-bounded-budget"')
                actual = str(helper.document(Markup(marked))).replace('class="resource-table pdf-bounded-budget"', 'class="resource-table"')
                self.assertEqual(actual, str(helper.document(Markup(original))), name)

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
                        ([dict(row, purpose='<p>' + 'Long description. ' * 100 + '</p>')], False),
                        ([dict(row, purpose='<p>Paragraph</p>' * 16)], False),
                        ([dict(row, purpose='<p><img src="chart.png"></p>')], False)]:
                    expected = str(original)
                    if bounded and not word:
                        expected = expected.replace('class="resource-table"', 'class="resource-table pdf-bounded-budget"')
                    self.assertEqual(template.render(original=original, rows=rows, word=word), expected)


class CurrentBehaviorTests(unittest.TestCase):
    pass


class CurrentRepairContractTests(unittest.TestCase):
    def test_registered_version_routes_without_accepting_unknown_versions(self):
        from current_repairs_contract import CONTRACT, historical_version
        self.assertEqual(CONTRACT['baseline_version'], historical_version(CONTRACT['candidate_version']))
        self.assertEqual('999.0.0', historical_version('999.0.0'))

    def test_exact_candidate_projects_and_any_source_drift_fails(self):
        import json
        current = source_tree()
        metadata = json.loads((ROOT / 'template.json').read_text())
        before, prior_metadata = project_source(current, metadata)
        self.assertEqual('0.3.51', prior_metadata['version'])
        self.assertNotIn('src/active-answer.j2', before)

        changed = dict(current)
        changed['src/questions/13-persistent-identifier.html.j2'] += b'\n'
        with self.assertRaises(AssertionError):
            project_source(changed, metadata)

        added = dict(current)
        added['src/unreviewed.j2'] = b''
        with self.assertRaises(AssertionError):
            project_source(added, metadata)

        changed_metadata = dict(metadata, version='999.0.0')
        with self.assertRaises(AssertionError):
            project_source(current, changed_metadata)

        changed_metadata = dict(metadata, name='Unreviewed template name')
        with self.assertRaises(AssertionError):
            project_source(current, changed_metadata)


def test_suite(name):
    def test(self):
        run_suite(name, ROOT, 'en')
    return test


for name in SUITES:
    setattr(CurrentBehaviorTests, 'test_' + name, test_suite(name))


if __name__ == '__main__': unittest.main()
