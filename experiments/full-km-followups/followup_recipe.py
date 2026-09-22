"""Non-release, English-source-only overlay; production sources remain untouched."""
import hashlib
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = '8c624359fcbc59ff5b364feba1fadab54a2090bf'
INSERTIONS = {
    'src/questions/03-docs-metadata.html.j2': 'src/project-file-naming.html.j2',
    'src/questions/10-share-restrictions.html.j2': 'src/reference-publication-plan.html.j2',
    'src/questions/11-data-preservation.html.j2': 'src/reference-maintenance-plan.html.j2',
}
IDENTIFIER_CSS = b'''
/* Q10 identifiers: text before strong is not counted by :first-child.
   Keep the identifier value inline with its type, not as a dataset heading.
   Direct ancestry excludes authored lists and distribution policy blocks. */
html body #q-share-restrictions > .answer > .dataset-section > ul > li > strong:first-child {
  display: inline;
  break-after: auto;
}
'''


def sha(value):
    return hashlib.sha256(value).hexdigest()


def baseline_sources(root=ROOT):
    names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    return {name: subprocess.check_output(['git', '-C', str(root), 'show', BASELINE + ':' + name]) for name in names}


def overlay(current, root=ROOT):
    """Reject all unrelated edits, including CSS, Word helpers and extra files."""
    previous = baseline_sources(root)
    assert current == previous, 'Only exact 0.3.45 source inputs are accepted'
    result = dict(current)
    for name, include in INSERTIONS.items():
        marker = b'{% set answerContent %}'
        assert result[name].count(marker) == 1
        result[name] = result[name].replace(marker, marker + ("\n    {% include '" + include + "' %}").encode(), 1)
    for source in sorted((HERE / 'src').glob('*.j2')):
        name = 'src/' + source.name
        assert name not in result
        result[name] = source.read_bytes()
    result['src/layout.css'] += IDENTIFIER_CSS
    assert set(result) - set(previous) == {'src/full-km-followups.j2', *INSERTIONS.values()}
    assert {n for n in previous if result[n] != previous[n]} == {*INSERTIONS, 'src/layout.css'}
    return result
