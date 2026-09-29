"""Compilation reuse must not reuse answers, CSS variants or stale sources."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from jinja2 import TemplateSyntaxError
import test_science_europe_contract as adapter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from probe_render_cache import CACHED_RENDERER


class RenderCacheTests(unittest.TestCase):
    def test_profile_bytecode_separates_escape_and_override_versions(self):
        from output_profile_contract import environment
        for escape in [False, True, False, True]:
            for prefix in ['old', 'new', 'old']:
                env = environment(Path('.'), escape, {'example.j2': prefix + ':{{ value }}'})
                self.assertEqual(env.get_template('example.j2').render(value='<answer>'),
                                 prefix + ':' + ('&lt;answer&gt;' if escape else '<answer>'))

    def test_question_cache_keeps_answers_roots_and_source_changes_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ['one', 'two']:
                root = Path(temp) / name
                (root / 'src').mkdir(parents=True)
                for file in ['macros.html.j2', 'uuids.j2']:
                    (root / 'src' / file).write_text('')
                (root / 'question.j2').write_text(name + ':{{ repliesMap.value }}')
            with patch.object(adapter, 'QUESTION_BYTECODE', adapter.QuestionBytecodeCache()):
                for name in ['one', 'two', 'one']:
                    root = Path(temp) / name
                    with patch.object(adapter, 'ROOT', root):
                        for answer in ['A', 'B']:
                            self.assertEqual(adapter.render_question('question.j2', dict(value=answer)), name + ':' + answer)
                with patch.object(adapter, 'ROOT', root):
                    (root / 'question.j2').write_text('changed:{{ repliesMap.value }}')
                    self.assertEqual(adapter.render_question('question.j2', dict(value='C')), 'changed:C')
                    (root / 'question.j2').write_text('{% invalid_tag %}')
                    with self.assertRaises(TemplateSyntaxError): adapter.render_question('question.j2', {})

    def test_css_cache_is_per_media_and_exact_css_and_never_caches_documents(self):
        html, css, fonts = Mock(), Mock(), Mock(side_effect=object)
        css.side_effect = lambda **kwargs: object()
        modules = {'weasyprint': SimpleNamespace(HTML=html, CSS=css),
                   'weasyprint.text.fonts': SimpleNamespace(FontConfiguration=fonts)}
        scope = {}
        with patch.dict(sys.modules, modules): exec(CACHED_RENDERER, scope)
        render = scope['render_cached']
        for source, style, media in [('first', 'base', 'print'), ('second', 'base', 'print'),
                                     ('third', 'base', 'screen'), ('fourth', 'changed', 'print')]:
            render(source, style, media)
        self.assertEqual((html.call_count, html.return_value.render.call_count), (4, 4))
        self.assertEqual((css.call_count, fonts.call_count), (3, 3))
        calls = html.return_value.render.call_args_list
        self.assertEqual(calls[0], calls[1])
        self.assertIsNot(calls[0].kwargs['font_config'], calls[2].kwargs['font_config'])
        self.assertIsNot(calls[0].kwargs['font_config'], calls[3].kwargs['font_config'])


if __name__ == '__main__': unittest.main()
