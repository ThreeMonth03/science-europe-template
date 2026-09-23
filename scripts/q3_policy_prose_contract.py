"""Exact 0.3.51 Q3 overlay; historical tests receive verified 0.3.50 bytes."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'a2f97d9312b4ce811b92f5943944997638cc67b8'
PROTOTYPE = 'a0ed46715842a01c154beb430f97ac58a0549347'

@lru_cache(maxsize=None)
def historical(name, commit=BASELINE):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])

def load(name):
    folder = ROOT / 'experiments/q3-shared-policy-prose'
    for file in ['recipe.py', 'probe.py', 'metadata-prose.html.j2']:
        path = folder / file
        assert path.read_bytes() == historical(str(path.relative_to(ROOT)), PROTOTYPE), 'Frozen Q3 prototype changed'
    spec = importlib.util.spec_from_file_location('integrated_q3_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None:
        metadata = json.loads((ROOT / 'template.json').read_text())
    recipe = load('recipe'); before = recipe.baseline_sources(ROOT)
    assert sources == recipe.overlay(before, ROOT), 'Unreviewed 0.3.51 source, inventory or asset'
    previous = json.loads(historical('template.json'))
    assert metadata == dict(previous, version='0.3.51'), 'Unreviewed identity or conversion step'
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert (ROOT / name).read_bytes() == historical(name), name
    return dict(before), previous
