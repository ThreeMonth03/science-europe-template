"""Validate the exact reviewed 0.3.50 Word overlay before a 0.3.49 test view."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import subprocess
from current_repairs_contract import historical_version

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'ff6eea886d27f5bca4682cd3f3c59e1701a83f10'
PROTOTYPE = '2f63e964c481d08b949ec4663209f3d2e0f1b8e4'

@lru_cache(maxsize=None)
def historical(name, commit=BASELINE):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])

def load(name):
    folder = ROOT / 'experiments/word-empty-section-spacing'
    for file in ['recipe.py', 'engine.py', 'section-filter.lua', 'section-spacing.xml']:
        path = folder / file
        assert path.read_bytes() == historical(str(path.relative_to(ROOT)), PROTOTYPE), 'Frozen Word prototype changed'
    spec = importlib.util.spec_from_file_location('integrated_word_sections_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def project_source(sources=None, metadata=None):
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    if metadata is None:
        metadata = json.loads((ROOT / 'template.json').read_text())
    if historical_version(metadata['version']) == '0.3.51':
        from q3_policy_prose_contract import project_source as before_q3
        sources, metadata = before_q3(sources, metadata)
    recipe = load('recipe'); before = recipe.baseline_sources(ROOT)
    assert sources == recipe.overlay(before, ROOT), 'Unreviewed 0.3.50 source, inventory or asset'
    previous = json.loads(historical('template.json'))
    assert metadata == dict(previous, version='0.3.50'), 'Unreviewed identity or conversion step'
    from current_repairs_contract import project_support
    for name in ['scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE']:
        assert project_support(name) == historical(name), name
    return dict(before), previous
