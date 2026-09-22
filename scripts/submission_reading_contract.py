"""Validate every 0.3.45 source byte before exposing the exact 0.3.44 baseline."""
import hashlib
from functools import lru_cache
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'requirements/submission-reading-delta.json').read_text())


@lru_cache(maxsize=None)
def historical(name):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', CONTRACT['baseline_commit'] + ':' + name])


def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None: metadata = json.loads((ROOT / 'template.json').read_text())
    digest = lambda value: hashlib.sha256(value).hexdigest()
    assert {name: digest(value) for name, value in sources.items()} == CONTRACT['after'], 'Unreviewed 0.3.45 source or asset'
    assert metadata == CONTRACT['after_metadata'], 'Unreviewed format, version or conversion change'
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
                                    CONTRACT['baseline_commit'], 'src'], text=True).splitlines()
    result = {name: historical(name) for name in names}
    assert {name: digest(value) for name, value in result.items()} == CONTRACT['before']
    assert set(CONTRACT['after']) - set(result) == set(CONTRACT['added'])
    assert {n for n in result if CONTRACT['before'][n] != CONTRACT['after'][n]} == set(CONTRACT['changed'])
    previous = json.loads(historical('template.json')); assert previous['version'] == CONTRACT['baseline_version']
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    return result, previous


def historical_overrides():
    sources, _ = project_source()
    return {name: value.decode() for name, value in sources.items() if name.endswith('.j2')}
