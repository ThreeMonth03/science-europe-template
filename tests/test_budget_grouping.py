import hashlib
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from budget_grouping_contract import project_source, prior_budget, prior_lua, prior_css, forward_budget, forward_lua, historical, ENTRY, LUA, CSS, TAIL, KEPT_BODY, WORD_BATCHED
from probe_short_resource_rows import fixture
from probe_long_budget_word import cases


class BudgetGroupingTests(unittest.TestCase):
    def test_all_source_bytes_restore_exact_043_parent(self):
        sources, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.42')
        self.assertEqual(sources[ENTRY], historical(ENTRY))

    def test_integrated_renderers_match_the_frozen_native_trial(self):
        # Frozen 2026-09-21-large-resource-groups native package receipts.
        expected = {ENTRY:'0f20b29a988e17519b16201882e5d0a06acb002b197a4873f48061c39d0f2e9d',
                    LUA:'eb79e7cbb7a96972cc49e0e76bae462eeea66e0be911f049a259f48e8a7b0547'}
        for name, digest in expected.items(): self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(forward_budget(historical(ENTRY).decode()), (ROOT / ENTRY).read_text())
        self.assertEqual(forward_lua(historical(LUA).decode()), (ROOT / LUA).read_text())
        self.assertEqual(historical(CSS).decode() + TAIL, (ROOT / CSS).read_text())

    def test_malformed_or_duplicate_owned_deltas_are_rejected(self):
        for name, project, token in [(ENTRY, prior_budget, KEPT_BODY),
                                     (LUA, prior_lua, WORD_BATCHED), (CSS, prior_css, TAIL)]:
            source = (ROOT / name).read_text()
            with self.assertRaises(AssertionError): project(source.replace(token, token[:10] + 'CHANGED' + token[10:], 1))
            with self.assertRaises(AssertionError): project(source + source)

    def test_pdf_groups_preserve_source_rows_and_bound_each_ordinary_table(self):
        for escaping in [False, True]:
            helper = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'], autoescape=escaping).get_template(ENTRY).module
            for count in [32,33,34,64,65,66]:
                for language in ['en', 'zh']:
                    original, rows = fixture(count, language)
                    long = rows[-1]
                    prior = long['original']
                    purpose = '<div class="answer-detail" data-fact-id="resource-justification" data-status="complete">' + '<p>Keep 原文.</p>' * 20 + '</div><p>Keep allocation.</p>'
                    long['original'] = long['original'].replace(long['purpose'], purpose, 1); long['purpose'] = purpose
                    original = original.replace(prior, long['original'], 1)
                    head = original.split('<thead>', 1)[1].split('</thead>', 1)[0]
                    values = [{k: Markup(v) if k != 'id' else v for k, v in row.items()} for row in rows]
                    result = BeautifulSoup(str(helper.render(Markup(original), Markup(head), values)), 'html.parser')
                    ordinary = result.select('table:not(.pdf-resource-reading)')
                    self.assertEqual([len(t.select('tbody > tr')) for t in ordinary], [min(32,count-1-i) for i in range(0,count-1,32)])
                    self.assertEqual([r['data-item-id'] for t in ordinary for r in t.select('tbody > tr')], [r['id'] for r in rows[:-1]])
                    self.assertEqual(len(result.select('.pdf-resource-reading')), 1)
                    self.assertEqual(result.select_one('.pdf-resource-reading tbody').get_text(), BeautifulSoup(purpose, 'html.parser').get_text())

    def test_historic_word_matrix_is_retained_and_new_matrix_is_separate(self):
        self.assertEqual(len(cases()), 28)
        self.assertFalse(next(ok for name, _, ok in cases() if name == 'too-many-resources'))
        current = cases(grouped=True)
        self.assertEqual(len(current), 37)
        self.assertTrue(next(ok for name, _, ok in current if name == 'too-many-resources'))
        self.assertFalse(any(ok for name, _, ok in current if name.startswith('large-')))


if __name__ == '__main__': unittest.main()
