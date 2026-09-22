"""Print-only spacing for exactly shaped, wholly empty owned sections.

This prototype does not change production src/, Jinja, translations, type size,
line height, Word steps, or the conservative 0.3.47 empty-question classifier.
"""
from functools import lru_cache
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '2eebf1f783a6017fe25712c1b01c6a708adfedab'
COUNTS = {
    'sec-data-collection': 2, 'sec-docs-metadata': 2, 'sec-storage-backup': 2,
    'sec-ethics-legal': 3, 'sec-sharing-preservation': 4,
    'sec-responsibilities-resources': 2,
}
MARKER = '/* BEGIN empty section spacing v1:'

def selector(identifier, count):
    result = 'html body #dmp-content > section.dmp-section#' + identifier
    result += ':has(> h2:first-child)'
    for position in range(2, count + 2):
        result += ':has(> div.question.compact-empty-question:nth-child(' + str(position) + ')'
        result += ':last-child)' if position == count + 1 else ')'
    return result

SELECTORS = [selector(identifier, count) for identifier, count in COUNTS.items()]
CSS = ('\n' + MARKER + ''' all direct questions must carry the trusted empty marker.
   Exact section ids, child counts and heading position reject mixed/unknown
   structures. Only print margins change; retain empty answer boxes and all text.
   One-step :has predicates avoid the unmatching descendant-chain diagnostic. */
@media print {
''' + ',\n'.join(SELECTORS) + ' { margin-bottom: .8em; }\n' +
       ',\n'.join(s + ' > h2' for s in SELECTORS) +
       ' { margin-top: .9em; margin-bottom: .4em; }\n}\n/* END empty section spacing v1 */\n').encode()

@lru_cache(maxsize=2)
def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',BASELINE,'src'],text=True).splitlines()
    return {n:subprocess.check_output(['git','-C',str(root),'show',BASELINE+':'+n]) for n in names}

def overlay(current, root=ROOT):
    assert current == baseline_sources(root), 'Only exact 0.3.47 source inputs are accepted'
    assert MARKER.encode() not in current['src/layout.css']
    result = dict(current); result['src/layout.css'] += CSS
    return result

def project_prepared(before, after):
    assert set(before) == set(after), 'No source or asset may be added or removed'
    for name, content in before.items():
        assert after[name] == content + (CSS if name == 'src/layout.css' else b''), name
    return before
