"""Exact 0.3.44 source provenance; historical gates never accept fuzzy removal.

The approved hashes identify the already rendered prototype in the paired
translation repository. Only after every current source byte is verified do we
expose the immutable 0.3.43 inputs to older, unchanged output oracles.
"""
import hashlib
from functools import lru_cache
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'requirements/submission-preview-delta.json').read_text())
KINDS = {'instrument': 'INSTRUMENT', 'reference': 'REFERENCE',
    'non-reference': 'NON_REFERENCE', 'non-equipment': 'NON_EQUIPMENT', 'produced': 'PRODUCED'}
CONSTANTS = ''.join('{%- set DATASET_' + variable + ' = "' + kind + '" -%}\n'
    for kind, variable in KINDS.items())


def prototype_source(name, value):
    """The only adaptation: keep machine classification out of translation units.

    Invert exact constant references, then require the approved whole-file hash.
    A changed value, missing constant or any other source edit still fails.
    """
    if name not in CONTRACT['files']:
        return value
    source = value.decode()
    assert 'macros.datasetLabel("' not in source, 'Machine classification must not enter translation units'
    if name == 'src/macros.html.j2':
        assert source.count(CONSTANTS) == 1, 'Dataset kind constants changed'
        source = source.replace(CONSTANTS, '', 1)
    for kind, variable in KINDS.items():
        source = source.replace('macros.datasetLabel(macros.DATASET_' + variable + ',',
                                'macros.datasetLabel("' + kind + '",')
    assert 'macros.datasetLabel(macros.DATASET_' not in source
    return source.encode()


@lru_cache(maxsize=None)
def historical(name):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', CONTRACT['baseline_commit'] + ':' + name])


def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None:
        metadata = json.loads((ROOT / 'template.json').read_text())
    previous = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
        CONTRACT['baseline_commit'], 'src'], text=True).splitlines()
    assert set(sources) == set(previous), 'Source inventory changed outside approved delta'
    result = {}
    for name in previous:
        old = historical(name)
        if name in CONTRACT['files']:
            expected = CONTRACT['files'][name]
            assert hashlib.sha256(old).hexdigest() == expected['before_sha256'], name
            assert hashlib.sha256(prototype_source(name, sources[name])).hexdigest() == expected['after_sha256'], name
        else:
            assert sources[name] == old, name
        result[name] = old
    before = json.loads(historical('template.json'))
    expected_metadata = dict(before, version=CONTRACT['version'])
    assert before['version'] == CONTRACT['baseline_version'] and metadata == expected_metadata
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    return result, before


def historical_overrides():
    sources, _ = project_source()
    return {name: sources[name].decode() for name in CONTRACT['files']}
