"""Bounded Q1 prose prototype; exact 0.3.48, complete English branch sentences."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '678787f2fdf047a3d6cc3577d4589d64ba2cd846'
QUESTION = 'src/questions/01-how-data.html.j2'
START = '    {# Constrains - Data Harmonization #}'
END = '  {%- elif preexistingAUuid == uuids.preexistingNoAUuid -%}'
REPLACEMENTS = (
    ('We need to harmonize different sources of existing data before reusing them',
     'Before reuse, we need to harmonize existing data from different sources'),
    ('and we will make this harmonization results available to others',
     'and will make the results available to others'),
    ("but we won't make this harmonization results available to others",
     'but will not make the results available to others'),
    ('We will need to (re-)made the data into computer readable form before their using',
     'Before reuse, we will need to convert the data into a machine-readable form'),
    ('and we will make this computer readable form available to others through a standard repository',
     'and will make this version available to others through a standard repository'),
    ('and we will make this computer readable form available to others',
     'and will make this version available to others'),
    ("but we won't make this computer readable form available to others",
     'but will not make this version available to others'),
    ('We will provide machine readable, standardized metadata to others',
     'We will provide others with standardized, machine-readable metadata'),
    ('and we will use following Metadata Standards:', 'and we will use the following metadata standards:'),
)


def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {n: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + n]) for n in names}


def block(text):
    assert text.count(START) == text.count(END) == 1
    start, end = text.index(START), text.index(END)
    assert start < end
    return text[start:end]


def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact 0.3.48 source inputs are accepted'
    result = dict(current)
    text = current[QUESTION].decode()
    old = block(text)
    new = old
    for before, after in REPLACEMENTS:
        assert new.count(before) == 1
        new = new.replace(before, after)
    result[QUESTION] = text.replace(old, new).encode()
    # The first rehearsal is exactly reversible before the complete-sentence rewrite.
    restored = new
    for before, after in REPLACEMENTS:
        assert restored.count(after) == 1
        restored = restored.replace(after, before)
    assert restored == old
    marker = '    {# Constrains - (Re)made data computer readable #}'
    assert new.count(marker) == 1
    new = new[:new.index(marker)] + (Path(__file__).parent / 'computer-readable.html.j2').read_text()
    result[QUESTION] = text.replace(old, new).encode()
    assert {n for n in current if current[n] != result[n]} == {QUESTION}
    return result
