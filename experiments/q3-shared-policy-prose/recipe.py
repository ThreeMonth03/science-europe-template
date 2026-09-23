"""Exactly one Q3 capture plus a renderer-neutral helper on 0.3.50."""
from functools import lru_cache
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = 'a2f97d9312b4ce811b92f5943944997638cc67b8'
QUESTION = 'src/questions/03-docs-metadata.html.j2'
HELPER = 'src/metadata-prose.html.j2'
CHANGED = {QUESTION, HELPER}
OPEN = '<div class="dataset-policy metadata-policy">'
END = '</div>\n\n  {# Storage and file conventions #}'
CAPTURE = '{% set metadataPolicyOriginal %}'
RENDER = "{% endset %}{% import 'src/metadata-prose.html.j2' as metadataProse %}{{ metadataProse.render(metadataPolicyOriginal) }}"


@lru_cache(maxsize=1)
def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {n: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + n]) for n in names}


def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact 0.3.50 source inputs are accepted'
    assert HELPER not in current
    result = dict(current); old = current[QUESTION].decode()
    assert old.count(OPEN) == old.count(END) == 1 and CAPTURE not in old and RENDER not in old
    new = old.replace(OPEN, OPEN + CAPTURE).replace(END, RENDER + END)
    assert new.replace(CAPTURE, '').replace(RENDER, '') == old
    result[QUESTION] = new.encode(); result[HELPER] = (HERE/'metadata-prose.html.j2').read_bytes()
    assert set(result) - set(current) == {HELPER}
    assert {n for n in current if current[n] != result[n]} == {QUESTION}
    return result
