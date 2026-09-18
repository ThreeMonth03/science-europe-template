"""Exact PDF-entry-only delta and independent DOM eligibility for short Q15."""
import hashlib
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup, Comment, NavigableString

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '11c05c3b77ec21fc0fa9a9d12c165876e1e78d26'
HELPER = 'src/pdf/short-resources.html.j2'
ENTRY = 'src/pdf/index.html.j2'
OPENING = '<div id="q-required-resources" class="question" data-requirement-id="SE-6b">'
HINT = '<div id="q-required-resources" class="question pdf-short-resources" style="break-inside: avoid" data-requirement-id="SE-6b">'
HOOK = "{%- set pdfDocument -%}{%- include 'src/index.html.j2' -%}{%- endset -%}\n{%- import 'src/pdf/short-resources.html.j2' as shortResources -%}\n{{- shortResources.document(pdfDocument) -}}\n"


def historical(path): return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE+':'+path])


def project_source():
    """Validate every current source byte, then expose the exact 0.3.39 input."""
    old = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
    metadata = json.loads((ROOT/'template.json').read_text())
    if metadata['version'] in ['0.3.41','0.3.42']:
        from resource_prose_contract import project_source as project_prose
        current, metadata = project_prose()
    assert set(current)-set(old) == {HELPER} and not set(old)-set(current)
    original = historical(ENTRY)
    assert current[ENTRY] == original.replace(b"{%- include 'src/index.html.j2' -%}\n", HOOK.encode())
    current.pop(HELPER); current[ENTRY] = original
    for name in old: assert current[name] == historical(name), name
    before = json.loads(historical('template.json'))
    assert metadata['version'] == '0.3.40' and before['version'] == '0.3.39'
    metadata['version'] = '0.3.39'; assert metadata == before
    assert (ROOT/'scripts/prepare_layout.py').read_bytes() == historical('scripts/prepare_layout.py')
    return current, metadata


def units(value): return sum(2 if ord(c) >= 0x2e80 else 1 for c in ' '.join(value.split()))


def project_prepared(root, hashes):
    project_source()
    assert (root/HELPER).read_bytes() == (ROOT/HELPER).read_bytes(), 'Presentation helper must not be translated'
    assert (root/ENTRY).read_bytes() == (ROOT/ENTRY).read_bytes(), 'PDF entry must remain identical'
    projected = dict(hashes)
    helper = (ROOT/HELPER).read_text()
    if json.loads((ROOT/'template.json').read_text())['version'] in ['0.3.41','0.3.42']:
        from resource_prose_contract import prior_pdf
        helper = prior_pdf(helper)
    assert projected.pop(HELPER) == hashlib.sha256(helper.encode()).hexdigest()
    projected[ENTRY] = hashlib.sha256(historical(ENTRY)).hexdigest()
    return projected


def eligible(question):
    """Separate parsed-tree oracle; reject unknown tags, attributes and nesting."""
    if question is None or question.attrs != dict(id='q-required-resources', **{'class': ['question'], 'data-requirement-id': 'SE-6b'}): return False
    children = question.find_all(recursive=False)
    if len(children) != 2 or children[0].name != 'h3' or children[0].attrs or children[1].attrs != {'class': ['answer']}: return False
    answer = children[1]
    project = answer.find_all('div', class_='project-resources', recursive=False)
    if len(project) != 1 or answer.find_all(recursive=False)[-1] is not project[0]: return False
    p = project[0]
    if set(p.attrs) != {'class', 'data-item-id'} or p['class'] != ['project-resources']: return False
    identity = lambda s: bool(s) and all(c in '0123456789abcdef-.' for c in s)
    if not identity(p['data-item-id']): return False
    table, = p.find_all(recursive=False) if len(p.find_all(recursive=False)) == 1 else [None]
    if table is None or table.name != 'table' or table.attrs != {'class': ['resource-table']}: return False
    if [c.name for c in table.find_all(recursive=False)] != ['colgroup', 'thead', 'tbody']: return False
    if [c.attrs for c in table.colgroup.find_all(recursive=False)] != [{'class': [n]} for n in ['resource-purpose','resource-budget','resource-funding']]: return False
    if len(table.thead.find_all('tr', recursive=False)) != 1 or len(table.thead.find_all('th')) != 3: return False
    rows = table.tbody.find_all(recursive=False)
    if not 1 <= len(rows) <= 2: return False
    for row in rows:
        if row.name != 'tr' or set(row.attrs) != {'data-item-id'} or not identity(row['data-item-id']): return False
        cells = row.find_all(recursive=False)
        if len(cells) != 3 or any(c.name != 'td' or c.attrs for c in cells): return False
        for cell, count, limit in zip(cells, [3,1,1], [300,40,80]):
            if len(cell.find_all('p')) != count or not 0 < units(cell.get_text()) <= limit: return False
    if len(question.find_all('p')) > 16 or len(question.find_all('ul')) > 1 or len(question.find_all('li')) > 2: return False
    if not 0 < units(question.get_text()) <= 1200: return False
    for node in question.find_all(['p', 'li']):
        if not 0 < units(node.get_text()) <= (80 if node.name == 'li' else 160): return False
    for tag, limit in [('h3',360),('h4',80),('th',40)]:
        if any(not 0 < units(n.get_text()) <= limit for n in question.find_all(tag)): return False
    facts = [dict(**{'data-requirement-id':'SE-6b','data-fact-id':f,'data-status':s})
        for f,s in [('specialist-expertise','complete'),('specialist-expertise','explicit-no'),('hardware-software','explicit-no')]]
    details = [{'class':['answer-detail']}, *[{'class':['answer-detail'],'data-fact-id':f,'data-status':'complete'}
        for f in ['specialist-expertise-detail','resource-justification']]]
    for node in question.descendants:
        if isinstance(node, Comment): return False
        if isinstance(node, NavigableString):
            if node.strip() and node.parent.name not in ['p','span','strong','em','code','li','h3','h4','th']: return False
            continue
        parent = node.parent
        if node.name == 'div':
            if node is answer or node is p: continue
            if node.attrs == {'class':['answer-lead']} or node.attrs == details[1]:
                if parent is not answer: return False
            elif node.attrs in [details[0],details[2]]:
                if parent.name != 'td': return False
            else: return False
        elif node.name in ['p','h3','h4','strong','em','code','ul','li']:
            if node.name == 'p':
                if node.attrs and node.attrs not in facts: return False
                if parent.name not in ['div','td'] or parent in [question,p]: return False
            elif node.attrs: return False
            elif node.name == 'h3' and parent is not question: return False
            elif node.name == 'h4' and parent is not answer: return False
            elif node.name in ['strong','em','code'] and parent.name not in ['p','li']: return False
            elif node.name == 'ul' and parent.attrs != details[1]: return False
            elif node.name == 'li' and parent.name != 'ul': return False
        elif node.name == 'span':
            if node.attrs != {'data-fact-id':'repository-charges','data-status':'complete'}: return False
            if parent.name != 'p' or parent.attrs != facts[2] or len(question.find_all('span')) != 1: return False
        elif node.name == 'table':
            if node is not table: return False
        elif node.name in ['colgroup','thead','tbody']:
            if parent is not table or node.attrs: return False
        elif node.name == 'col':
            if parent.name != 'colgroup' or node.attrs not in [{'class':[n]} for n in ['resource-purpose','resource-budget','resource-funding']]: return False
        elif node.name == 'tr':
            if parent.name == 'thead':
                if node.attrs: return False
            elif parent.name != 'tbody': return False
        elif node.name == 'th':
            if node.attrs != {'scope':'col'} or parent.parent.name != 'thead': return False
        elif node.name == 'td':
            if node.attrs or parent.parent.name != 'tbody': return False
        else: return False
    return len(question.find_all('h3')) == len(question.find_all('h4')) == 1


def compare(source, actual, expected):
    before = BeautifulSoup(source, 'html.parser'); q = before.find(id='q-required-resources')
    assert eligible(q) == expected, 'Fixture disagrees with independent DOM oracle'
    assert actual == (source.replace(OPENING, HINT, 1) if expected else source), 'Only the unique Q15 opening hint may change'
    after = BeautifulSoup(actual, 'html.parser')
    assert len(after.select('.pdf-short-resources')) == int(expected)
    return expected
