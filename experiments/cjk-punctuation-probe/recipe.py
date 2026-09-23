"""Prototype only: join owned Q3 Chinese sentences without an ASCII separator."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'a2f97d9312b4ce811b92f5943944997638cc67b8'
QUESTION = 'src/questions/03-docs-metadata.html.j2'
OLD = '<p>{{ metadataSentences|join(" ") }}</p>'
NEW = '''{# Only this list of template-owned sentences; never authored answers. #}
        {%- set metadataJoin = namespace(separator='') -%}
        {%- for metadataSentence in metadataSentences -%}
          {%- if metadataSentence is not string or not ('㐀' <= metadataSentence[:1] <= '鿿') or not metadataSentence.endswith('。') or '<' in metadataSentence or '>' in metadataSentence -%}
            {%- set metadataJoin.separator = ' ' -%}
          {%- endif -%}
        {%- endfor -%}
        <p>{{ metadataSentences|join(metadataJoin.separator) }}</p>'''


def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {n: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + n]) for n in names}


def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact 0.3.50 source inputs are accepted'
    result = dict(current)
    text = current[QUESTION].decode()
    assert text.count(OLD) == 1 and NEW not in text
    result[QUESTION] = text.replace(OLD, NEW).encode()
    assert result[QUESTION].decode().replace(NEW, OLD).encode() == current[QUESTION]
    assert {n for n in current if current[n] != result[n]} == {QUESTION}
    return result
