"""Validate every 0.3.47 byte before a test-only projection to sealed 0.3.46."""
import ast
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'requirements/submission-flow-delta.json').read_text())

@lru_cache(maxsize=None)
def historical(name, prototype=False):
    commit = CONTRACT['prototype_commit' if prototype else 'baseline_commit']
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])

@lru_cache(maxsize=1)
def baseline():
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', CONTRACT['baseline_commit'], 'src'], text=True).splitlines()
    return {n: historical(n) for n in names}

@lru_cache(maxsize=1)
def spacing_css():
    tree = ast.parse(historical('experiments/empty-question-spacing/recipe.py', True))
    return next(ast.literal_eval(n.value).decode() for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'CSS' for t in n.targets))

def prior_css(source):
    from empty_section_spacing_contract import prior_css as before_sections
    source = before_sections(source)
    marker = '/* Empty submission questions:'
    if marker not in source: return source
    delta = spacing_css()
    assert source.count(delta) == 1 and source.count(marker) == 1, 'Modified or duplicate empty-question CSS'
    return source.replace(delta, '', 1)

def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None: metadata = json.loads((ROOT / 'template.json').read_text())
    if metadata['version'] == '0.3.48':
        from empty_section_spacing_contract import project_source as before_sections
        sources, metadata = before_sections(sources, metadata)
    hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n,v in values.items()}
    assert hashes(sources) == CONTRACT['after'], 'Unreviewed 0.3.47 source or asset'
    assert metadata == CONTRACT['after_metadata'], 'Unreviewed 0.3.47 identity or conversion step'
    before = dict(baseline()); assert hashes(before) == CONTRACT['before']
    assert set(sources) - set(before) == set(CONTRACT['added']) and not set(before) - set(sources)
    assert {n for n in before if before[n] != sources[n]} == set(CONTRACT['changed'])
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    for name,digest in CONTRACT['prototype_recipes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
        assert (ROOT/name).read_bytes() == historical(name, True), name
    previous = json.loads(historical('template.json')); assert previous == CONTRACT['before_metadata']
    return before, previous
