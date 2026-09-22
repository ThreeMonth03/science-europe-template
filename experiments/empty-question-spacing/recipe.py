"""Opt-in layout overlay on the locked reuse-summary prototype, not production."""
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTENT = 'src/content.html.j2'
HELPERS = ['src/question-spacing.html.j2', 'src/word/question-spacing.lua', 'src/word/question-spacing.xml']
CSS = b'''
/* Empty submission questions: retain original headings, not empty answer space.
   Only the conservative shared Jinja classifier can add this class. */
html body #dmp-content > .dmp-section > .question.compact-empty-question { margin-top: .5em; }
html body #dmp-content > .dmp-section > .question.compact-empty-question > h3 { margin: .4em 0 .15em; break-after: auto; }
html body #dmp-content > .dmp-section > .question.compact-empty-question > .answer { display: none; }
'''


def load_reuse(root=ROOT):
    spec = importlib.util.spec_from_file_location('reuse_spacing_baseline', root / 'experiments/reuse-summary/recipe.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def overlay(current, root=ROOT):
    reuse = load_reuse(root)
    prior = reuse.overlay(reuse.baseline_sources(root), root)
    assert current == prior, 'Expected exact English reuse-summary prototype sources'
    result = dict(current)
    text = result[CONTENT].decode()
    includes = re.findall(r'{% include "(src/questions/[^"]+)" with context %}', text)
    assert len(includes) == 15
    for filename in includes:
        ids = re.findall(r'<div id="([^"]+)" class="question"(?: data-requirement-id="[^"]+")?>', current[filename].decode())
        assert len(ids) == 1
        qid = ids[0]
        token = '{% include "' + filename + '" with context %}'
        replacement = '{% call questionSpacing.question("' + qid + '") %}' + token + '{% endcall %}'
        assert text.count(token) == 1
        text = text.replace(token, replacement, 1)
    result[CONTENT] = ("{%- import 'src/question-spacing.html.j2' as questionSpacing with context -%}" + text).encode()
    result['src/layout.css'] += CSS
    for name in HELPERS:
        assert name not in result
        result[name] = (HERE / name).read_bytes()
    assert {n for n in current if result[n] != current[n]} == {CONTENT, 'src/layout.css'}
    assert set(result) - set(current) == set(HELPERS)
    return result


def metadata(spec):
    """Only the submission Word format gains an output-specific helper."""
    import copy
    result = copy.deepcopy(spec)
    word = next(f for f in result['formats'] if f['uuid'] == '98081811-41ff-5438-b98a-0472607527c6')
    assert [s['name'] for s in word['steps']] == ['jinja', 'pandoc', 'enrich-docx']
    word['steps'][1]['options']['args'] += ' --lua-filter=src/word/question-spacing.lua'
    assert word['steps'][2]['options']['rewrite:word/document.xml'] == 'render:src/word/short-tables.xml'
    word['steps'][2]['options']['rewrite:word/document.xml'] = 'render:src/word/question-spacing.xml'
    return result
