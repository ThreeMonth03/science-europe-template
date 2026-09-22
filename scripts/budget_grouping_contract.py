"""Exact reversible 0.3.43 presentation delta; all older source gates remain."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '200fac5239051e1a877493c7d52c3a199964c718'
ENTRY = 'src/budget-reading.html.j2'
LUA = 'src/word/pilot.lua'
CSS = 'src/layout.css'
ORDINARY = '''{%- macro ordinary(header, rows) -%}
<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead>{{ header }}</thead><tbody>{% for row in rows %}{{ row.original }}{% endfor %}</tbody></table>
{%- endmacro -%}'''
SHORT = ORDINARY.replace('<table class="resource-table">', '{%- set original -%}<table class="resource-table">', 1).replace(
    '\n{%- endmacro -%}', '''{%- endset -%}
{%- import 'src/pdf/short-resource-rows.html.j2' as shortRows -%}
{{- shortRows.table(original, rows) -}}
{%- endmacro -%}''', 1)
BATCHED = SHORT.replace('{%- macro ordinary(header, rows) -%}', '''{%- macro ordinary(header, rows) -%}
{%- if rows|length > 32 -%}
  {%- for group in rows|batch(32) -%}{{ ordinary(header, group) }}{%- endfor -%}
{%- else -%}''', 1).replace('{%- endmacro -%}', '{%- endif -%}\n{%- endmacro -%}', 1)
COUNT = '{%- if rows|length <= 32 -%}{{ classify(row, result) }}{%- endif -%}'
PER_ROW = '{{ classify(row, result) }}'
BODY = '</tr></thead><tbody><tr><td colspan="3">{{ row.purpose }}'
KEPT_BODY = BODY.replace('<tbody>', '<tbody style="break-inside: avoid">', 1)
# Retain the exact tested bytes, including the original experiment's comment.
TAIL = '\n/* Local prototype: keep the final purpose fragment with its allocation. */\nhtml body .pdf-resource-reading tbody > tr > td > .answer-detail[data-fact-id="resource-justification"] { break-after: avoid; }\n'
WORD_COUNT = 'if #rows == 0 or #rows > 32 then return tbl end'
WORD_ROWS = 'if #rows == 0 then return tbl end'
WORD_PENDING = 'if not plans[index].long then pending:insert(row:clone())'
WORD_BATCHED = '''if not plans[index].long then
        if #pending == 32 then flush() end
        pending:insert(row:clone())'''


def replace_exact(source, changes):
    for before, after in changes:
        assert source.count(before) == 1, 'Missing, duplicated or modified grouping delta'
        source = source.replace(before, after, 1)
    return source


def forward_budget(source): return replace_exact(source, [(ORDINARY, BATCHED), (COUNT, PER_ROW), (BODY, KEPT_BODY)])
def prior_budget(source): return replace_exact(source, [(BATCHED, ORDINARY), (PER_ROW, COUNT), (KEPT_BODY, BODY)])
def forward_lua(source): return replace_exact(source, [(WORD_COUNT, WORD_ROWS), (WORD_PENDING, WORD_BATCHED)])
def prior_lua(source): return replace_exact(source, [(WORD_ROWS, WORD_COUNT), (WORD_BATCHED, WORD_PENDING)])
def prior_css(source): return replace_exact(source, [(TAIL, '')])


def without_grouping(source, kind):
    """Only exact reviewed bytes are removable; old hash gates detect any drift."""
    if kind == 'lua' and WORD_BATCHED in source: return prior_lua(source)
    if kind == 'css' and '/* Local prototype: keep the final purpose fragment' in source: return prior_css(source)
    return source


def historical(name): return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE + ':' + name])


def project_source():
    sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    metadata = json.loads((ROOT / 'template.json').read_text())
    if metadata['version'] in ['0.3.44', '0.3.45']:
        from submission_preview_contract import project_source as project_submission
        sources, metadata = project_submission(sources, metadata)
    previous = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    assert set(sources) == set(previous)
    for name, project in [(ENTRY, prior_budget), (LUA, prior_lua), (CSS, prior_css)]:
        sources[name] = project(sources[name].decode()).encode()
    for name in previous: assert sources[name] == historical(name), name
    assert metadata['version'] == '0.3.43'; metadata['version'] = '0.3.42'
    assert metadata == json.loads(historical('template.json'))
    assert (ROOT / 'scripts/prepare_layout.py').read_bytes() == historical('scripts/prepare_layout.py')
    return sources, metadata


def project_prepared(root, hashes):
    project_source()
    result = dict(hashes)
    for name, project in [(ENTRY, prior_budget), (LUA, prior_lua), (CSS, prior_css)]:
        assert result[name] == hashlib.sha256((root / name).read_bytes()).hexdigest()
        result[name] = hashlib.sha256(project((root / name).read_text()).encode()).hexdigest()
    return result
