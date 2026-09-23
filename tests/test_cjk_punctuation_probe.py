"""A punctuation experiment must not edit production or normalize user text."""
import importlib.util
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('cjk_' + name, ROOT / 'experiments/cjk-punctuation-probe' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class CjkPunctuationProbeTests(unittest.TestCase):
    def test_exact_scope_and_english_answer_matrix(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        self.assertEqual(current, before)
        rows = load('probe').check(ROOT, before, recipe.overlay(before))
        self.assertEqual(396, sum(r['case'].startswith('fixture-') for r in rows))
        self.assertGreater(len(rows), 6000)
        self.assertFalse(any(r['removed_owned_separators'] for r in rows))

    def test_source_drift_fails_closed(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        before['src/layout.css'] += b'/* unrelated change */'
        with self.assertRaises(AssertionError): recipe.overlay(before)

    def test_conservative_sentence_separator_not_text_cleanup(self):
        recipe = load('recipe')
        env = Environment(extensions=['jinja2.ext.do'])
        template = env.from_string(recipe.NEW)
        for values, expected in [
            (['第一句。', '第二句。'], '第一句。第二句。'),
            (['First sentence.', 'Second sentence.'], 'First sentence. Second sentence.'),
            (['第一句。', 'Second sentence.'], '第一句。 Second sentence.'),
            (['First sentence.', '第二句。'], 'First sentence. 第二句。'),
            (['第一句。', ' 第二句。'], '第一句。  第二句。'),
            (['第一句。', ''], '第一句。 '),
            (['第一句。', '第二句'], '第一句。 第二句'),
            (['第一句。', '<em>第二句</em>。'], '第一句。 <em>第二句</em>。'),
            (['第一句。', '第二句  v1.25。'], '第一句。第二句  v1.25。'),
            (['單句）。'], '單句）。'),
        ]:
            self.assertEqual(template.render(metadataSentences=values), '<p>'+expected+'</p>')

    def test_projection_protects_authored_and_other_paragraphs(self):
        probe = load('probe')
        old, new = next(iter(probe.ALLOWED.items()))
        html = '<div id="q-docs-metadata"><div class="answer"><div class="metadata-policy"><p>'+old+'</p><p data-fact-id="metadata-dictionary">另段。 下一句。</p></div><div class="answer-detail"><p>'+old+'</p></div></div></div>'
        before = BeautifulSoup(html, 'html.parser')
        after = probe.project(before, 'chinese')
        probe.compare(before, after, 'chinese')
        self.assertEqual(after.select_one('.answer-detail p').get_text(), old)
        for mutation in [str(after).replace('另段。 下一句。', '另段。下一句。'),
                         str(after).replace('<div class="answer-detail"><p>'+old, '<div class="answer-detail"><p>'+new),
                         str(after).replace('Dublin Core', 'DublinCore'),
                         str(after).replace('。', '.', 1)]:
            if mutation == str(after): continue
            with self.assertRaises(AssertionError): probe.compare(before, BeautifulSoup(mutation, 'html.parser'), 'chinese')
        with self.assertRaises(AssertionError): probe.compare(before, after, 'english')


if __name__ == '__main__': unittest.main()
