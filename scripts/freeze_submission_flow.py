"""Freeze the exact accepted Q1 + empty-question source integration, once."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '1b0c82d9bee6984df7f11dc072ebf3c8f7726e08'
PROTOTYPE = '9847397dd1e2a7e29385c0d1f67eb4bfc0f93b4f'

def historical(name, commit=BASELINE):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])

def main():
    target = ROOT / 'requirements/submission-flow-delta.json'
    assert not target.exists()
    spec = importlib.util.spec_from_file_location('spacing', ROOT / 'experiments/empty-question-spacing/recipe.py')
    spacing = importlib.util.module_from_spec(spec); spec.loader.exec_module(spacing)
    reuse = spacing.load_reuse(); before = reuse.baseline_sources()
    recipes = {}
    for folder in ['experiments/reuse-summary', 'experiments/empty-question-spacing']:
        for p in (ROOT / folder).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.name == 'README.md': continue
            name = str(p.relative_to(ROOT)); assert p.read_bytes() == historical(name, PROTOTYPE)
            recipes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    after = spacing.overlay(reuse.overlay(before))
    current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    assert current == after
    oldmeta = json.loads(historical('template.json'))
    metadata = spacing.metadata(oldmeta); metadata['version'] = '0.3.47'
    assert metadata == json.loads((ROOT / 'template.json').read_text())
    hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n,v in sorted(values.items())}
    result = dict(baseline_commit=BASELINE, prototype_commit=PROTOTYPE,
        baseline_version='0.3.46', version='0.3.47', before=hashes(before), after=hashes(after),
        changed=sorted(n for n in before if before[n] != after[n]), added=sorted(set(after)-set(before)),
        before_metadata=oldmeta, after_metadata=metadata, prototype_recipes=recipes)
    with target.open('x') as f: f.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')

if __name__ == '__main__': main()
