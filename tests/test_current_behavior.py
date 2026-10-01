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
