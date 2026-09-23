"""Prototype: only Word helpers on the exact paired 0.3.49 baseline."""
from functools import lru_cache
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = 'ff6eea886d27f5bca4682cd3f3c59e1701a83f10'
LUA = 'src/word/question-spacing.lua'
XML = 'src/word/question-spacing.xml'
CHANGED = {LUA, XML}

@lru_cache(maxsize=1)
def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {n: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + n]) for n in names}

def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact reviewed 0.3.49 inputs are accepted'
    result = dict(current)
    old = b'return {{traverse="topdown", Div=question}}\n'
    assert current[LUA].count(old) == 1 and current[LUA].endswith(old)
    result[LUA] = current[LUA].replace(old, (HERE / 'section-filter.lua').read_bytes())
    result[XML] = b'{%- set section_content -%}\n' + current[XML] + b'\n{%- endset -%}\n' + (HERE / 'section-spacing.xml').read_bytes()
    assert set(current) == set(result)
    assert {n for n in current if current[n] != result[n]} == CHANGED
    return result
