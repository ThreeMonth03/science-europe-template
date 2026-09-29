"""Exact development delta projected to the committed 0.3.51 historical view.

This is provenance plumbing, not a release approval or a fuzzy hash exception.
Every current source byte, path, support file and the unchanged package identity
must match before an older contract receives the committed baseline bytes.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'requirements/current-repairs-delta.json').read_text())


def sha(value):
    return hashlib.sha256(value).hexdigest()


def tree_sha(values):
    digest = hashlib.sha256()
    for name, value in sorted(values.items()):
        digest.update(name.encode())
        digest.update(b'\0')
        digest.update(value)
    return digest.hexdigest()


@lru_cache(maxsize=None)
def historical(name):
    return subprocess.check_output([
        'git', '-C', str(ROOT), 'show', CONTRACT['baseline_commit'] + ':' + name
    ])


def source_tree(root=ROOT):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in (root / 'src').rglob('*') if path.is_file()}


@lru_cache(maxsize=1)
def baseline_tree():
    names = subprocess.check_output([
        'git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
        CONTRACT['baseline_commit'], 'src'
    ], text=True).splitlines()
    return {name: historical(name) for name in names}


def verify_support(name):
    expected = CONTRACT['support'][name]
    current = (ROOT / name).read_bytes()
    before = historical(name)
    assert sha(current) == expected['after_sha256'], ('Unreviewed candidate support change', name)
    assert sha(before) == expected['before_sha256'], ('Baseline support changed', name)
    return before


def _verify(sources, metadata):
    assert CONTRACT['release_approved'] is False, 'Development contract cannot approve release'
    before = dict(baseline_tree())
    assert tree_sha(before) == CONTRACT['baseline_tree_sha256'], 'Committed baseline source changed'
    assert tree_sha(sources) == CONTRACT['candidate_tree_sha256'], 'Unreviewed candidate source, inventory or asset'
    current_names, old_names = set(sources), set(before)
    assert sorted(current_names - old_names) == CONTRACT['added'], 'Unexpected added source'
    assert sorted(old_names - current_names) == CONTRACT['deleted'], 'Unexpected deleted source'
    changed = sorted(name for name in current_names & old_names if sources[name] != before[name])
    assert changed == CONTRACT['changed'], 'Unexpected changed source scope'
    for name in (current_names & old_names) - set(changed):
        assert sources[name] == before[name]

    current_metadata = json.loads((ROOT / 'template.json').read_text())
    baseline_metadata = json.loads(verify_support('template.json'))
    assert metadata == current_metadata == baseline_metadata, 'Candidate identity or format step changed'
    assert metadata['version'] == CONTRACT['candidate_version'] == CONTRACT['baseline_version']
    for name in ('scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE'):
        verify_support(name)
    return before, baseline_metadata


@lru_cache(maxsize=1)
def verified_current():
    return _verify(source_tree(), json.loads((ROOT / 'template.json').read_text()))


def project_source(sources=None, metadata=None):
    if sources is None and metadata is None:
        before, prior = verified_current()
        return dict(before), dict(prior)
    if sources is None:
        sources = source_tree()
    if metadata is None:
        metadata = json.loads((ROOT / 'template.json').read_text())
    return _verify(sources, metadata)


def project_support(name):
    """Return the committed support file only after its current byte check."""
    return verify_support(name)


def project_embedded_text(value, name):
    """Replace one exact current CSS/Lua payload inside a historical probe.

    Prefixes/suffixes are retained for the older gate to validate. Mutated or
    duplicated current payloads are deliberately left untouched and then fail.
    """
    project_source()
    current = (ROOT / name).read_text()
    if value.count(current) == 1:
        return value.replace(current, historical(name).decode(), 1)
    return value
