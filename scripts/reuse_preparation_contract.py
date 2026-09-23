"""Validate every 0.3.49 input before projecting a test-only exact 0.3.48 view."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '678787f2fdf047a3d6cc3577d4589d64ba2cd846'
PROTOTYPE = '57f79b33feaec4f3daf30a33841c59cb58d41b0e'


@lru_cache(maxsize=None)
def historical(name, commit=BASELINE):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])


def load(name):
    folder = ROOT / 'experiments/reuse-preparation-prose'
    for file in ['recipe.py', 'probe.py', 'computer-readable.html.j2']:
        path = folder / file
        assert path.read_bytes() == historical(str(path.relative_to(ROOT)), PROTOTYPE), 'Frozen prototype changed'
    spec = importlib.util.spec_from_file_location('integrated_preparation_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def baseline():
    return load('recipe').baseline_sources(ROOT)


def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None:
        metadata = json.loads((ROOT / 'template.json').read_text())
    before = baseline()
    assert sources == load('recipe').overlay(before, ROOT), 'Unreviewed 0.3.49 source, inventory or asset'
    previous = json.loads(historical('template.json'))
    assert metadata == dict(previous, version='0.3.49'), 'Unreviewed identity or conversion step'
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    return dict(before), previous
