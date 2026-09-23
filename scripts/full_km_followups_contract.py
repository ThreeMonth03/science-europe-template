"""Exact 0.3.46 source proof, then a test-only projection to immutable 0.3.45.

Projection is not rendering: current-package behavior is tested separately.
No changed file, missing helper, added asset or metadata drift is discarded.
"""
from functools import lru_cache
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'requirements/full-km-followups-delta.json').read_text())


@lru_cache(maxsize=None)
def historical(name, prototype=False):
    commit = CONTRACT['prototype_commit' if prototype else 'baseline_commit']
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])


@lru_cache(maxsize=1)
def baseline():
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
        CONTRACT['baseline_commit'], 'src'], text=True).splitlines()
    return {name: historical(name) for name in names}


@lru_cache(maxsize=1)
def identifier_css():
    tree = ast.parse(historical('experiments/full-km-followups/followup_recipe.py', True))
    return next(ast.literal_eval(node.value).decode() for node in tree.body
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == 'IDENTIFIER_CSS' for target in node.targets))


def prior_css(source):
    """Remove only the frozen identifier fix; older gates check all remaining bytes."""
    from submission_flow_contract import prior_css as before_flow
    source = before_flow(source)
    delta = identifier_css()
    if '/* Q10 identifiers:' not in source:
        return source
    assert source.count(delta) == 1 and source.count('/* Q10 identifiers:') == 1, 'Modified or duplicate identifier CSS'
    return source.replace(delta, '', 1)


def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None: metadata = json.loads((ROOT / 'template.json').read_text())
    if metadata['version'] in ['0.3.47', '0.3.48', '0.3.49', '0.3.50']:
        from submission_flow_contract import project_source as before_flow
        sources, metadata = before_flow(sources, metadata)
    hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
    assert hashes(sources) == CONTRACT['after'], 'Unreviewed 0.3.46 source or asset'
    assert metadata == CONTRACT['after_metadata'], 'Unreviewed 0.3.46 metadata or conversion change'
    previous = dict(baseline())
    assert hashes(previous) == CONTRACT['before']
    assert set(sources) - set(previous) == set(CONTRACT['added']) and not set(previous) - set(sources)
    assert {n for n in previous if sources[n] != previous[n]} == set(CONTRACT['changed'])
    prior = json.loads(historical('template.json'))
    assert prior == CONTRACT['before_metadata'] and dict(prior, version='0.3.46') == metadata
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    # Never let a mutable experiment recipe redefine the approved prototype.
    for file in (ROOT / 'experiments/full-km-followups').rglob('*'):
        if not file.is_file() or '__pycache__' in file.parts or file.name == 'README.md': continue
        name = str(file.relative_to(ROOT))
        assert file.read_bytes() == historical(name, prototype=True), name
    return previous, prior
