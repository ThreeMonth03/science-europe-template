"""Bounded Q1 experiment against exact 0.3.46; no production source edits."""
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = '1b0c82d9bee6984df7f11dc072ebf3c8f7726e08'
QUESTION = 'src/questions/01-how-data.html.j2'
HELPER = 'src/reuse-summary.html.j2'
START = '          {# Which part of the non-reference data we will use #}'
END = '          {# Personal Data #}'


def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {n: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + n]) for n in names}


def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact 0.3.46 source inputs are accepted'
    result = dict(current)
    text = result[QUESTION].decode()
    assert text.count(START) == text.count(END) == 1
    start, end = text.index(START), text.index(END)
    assert start < end
    result[QUESTION] = (text[:start] + "          {% include 'src/reuse-summary.html.j2' with context %}\n\n" + text[end:]).encode()
    result[HELPER] = (HERE / 'src/reuse-summary.html.j2').read_bytes()
    assert {n for n in current if current[n] != result[n]} == {QUESTION}
    assert set(result) - set(current) == {HELPER}
    return result
