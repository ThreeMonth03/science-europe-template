"""Exact 0.3.42 PDF-only row delta, with an independent parsed-fragment oracle."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '6ef78e859598d1c0866f9bbd71a066a4a1559341'
HELPER = 'src/pdf/short-resource-rows.html.j2'
ENTRY = 'src/budget-reading.html.j2'
OLD = '  {%- if not selection.any -%}{{ short_table(original, rows) }}{%- else -%}'
NEW = """  {%- if not selection.any -%}
    {%- import 'src/pdf/short-resource-rows.html.j2' as shortRows -%}
    {{- short_table(shortRows.table(original, rows), rows) -}}
  {%- else -%}"""
LIMITS = [(80,1,40),(240,3,40),(80,3,12),(100,3,20)]


def historical(path):
    return subprocess.check_output(['git','-C',str(ROOT),'show',BASELINE+':'+path])


def prior_entry(source):
    from budget_grouping_contract import BATCHED, prior_budget
    if BATCHED in source: source = prior_budget(source)
    assert source.count(NEW) == 1, 'Short-row hook drift'
    return source.replace(NEW, OLD, 1)


def project_source():
    current = {str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
    metadata = json.loads((ROOT/'template.json').read_text())
    if metadata['version'] == '0.3.43':
        from budget_grouping_contract import project_source as project_grouping
        current, metadata = project_grouping()
    old = subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASELINE,'src'],text=True).splitlines()
    assert set(current)-set(old) == {HELPER} and not set(old)-set(current)
    current.pop(HELPER)
    current[ENTRY] = prior_entry(current[ENTRY].decode()).encode()
    for name in old: assert current[name] == historical(name), name
    assert metadata['version'] == '0.3.42'
    metadata['version'] = '0.3.41'
    assert metadata == json.loads(historical('template.json'))
    assert (ROOT/'scripts/prepare_layout.py').read_bytes() == historical('scripts/prepare_layout.py')
    return current, metadata


def project_prepared(root, hashes):
    project_source()
    result = dict(hashes)
    assert (root/HELPER).read_bytes() == (ROOT/HELPER).read_bytes()
    assert result.pop(HELPER) == hashlib.sha256((ROOT/HELPER).read_bytes()).hexdigest()
    result[ENTRY] = hashlib.sha256(prior_entry((root/ENTRY).read_text()).encode()).hexdigest()
    return result


class Fragment(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ok = True; self.stack = []; self.paragraphs = 0; self.text = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes); parent = self.stack[-1] if self.stack else None
        if len(attrs) != len(attributes): self.ok = False
        if tag == 'div':
            self.ok &= parent is None and attrs in [
                {'class':'answer-detail'}, {'class':'answer-detail','data-fact-id':'resource-justification','data-status':'complete'}]
        elif tag == 'p':
            self.paragraphs += 1
            allowed = [{}]
            allowed += [{'class':'data-gap','data-requirement-id':'SE-6b','data-fact-id':fact,'data-status':'missing'}
                        for fact in ['resource-justification','resource-allocation','resource-amount','cost-coverage']]
            allowed += [{'data-fact-id':fact,'data-status':'complete'} for fact in ['resource-amount-value','resource-currency','cost-coverage']]
            allowed += [{'class':'data-gap','data-fact-id':'grant-number','data-status':'missing'}]
            self.ok &= parent in [None,'div'] and attrs in allowed
        elif tag in ['strong','em','code']: self.ok &= parent == 'p' and not attrs
        else: self.ok = False
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag: self.ok = False

    def handle_data(self, data):
        if data.strip() and (not self.stack or self.stack[-1] not in ['p','strong','em','code']): self.ok = False
        self.text.append(data)

    def handle_comment(self, data): self.ok = False
    def handle_decl(self, data): self.ok = False
    def handle_pi(self, data): self.ok = False


def eligible(row):
    for name,(limit,count,token_limit) in zip(['title','purpose','budget','funding'],LIMITS):
        value = row[name]; parser = Fragment(); parser.feed(value); parser.close()
        text = ' '.join(''.join(parser.text).split())
        if not parser.ok or parser.stack or not text or len(value)>3000 or not 1<=parser.paragraphs<=count: return False
        if sum(2 if ord(c)>=0x2e80 else 1 for c in text)>limit: return False
        if any(len(token)>token_limit for token in re.split(r'[\u2e80-\U0010ffff /-]',text)): return False
    return True


def row_fragments(row):
    cells = row.find_all('td',recursive=False)
    assert len(cells)==3 and not any(c.attrs for c in cells)
    title = cells[0].find('p',recursive=False); assert title is not None
    first = BeautifulSoup(str(cells[0]),'html.parser').td
    first.find('p',recursive=False).extract()
    inner = lambda n: ''.join(str(c) for c in n.contents)
    return dict(title=str(title), purpose=inner(first), budget=inner(cells[1]), funding=inner(cells[2]))


def project_hints(source):
    """Validate every new attribute before removing precisely its source bytes.

    The dedicated probe additionally checks that all eligible rows get a hint;
    this projection permits the historical long-table oracle to remain exact.
    """
    soup = BeautifulSoup(source,'html.parser')
    for row in soup.select('.pdf-short-resource-row'):
        identity = row.get('data-item-id','')
        assert re.fullmatch(r'[a-zA-Z0-9._-]{1,256}',identity)
        assert row.attrs == {'data-item-id':identity,'class':['pdf-short-resource-row'],'style':'break-inside: avoid'}
        table = row.find_parent('table')
        assert table.attrs == {'class':['resource-table']}
        assert row.parent is table.tbody and 4<=len(table.tbody.find_all('tr',recursive=False))<=32
        assert eligible(row_fragments(row)), identity
        before = '<tr data-item-id="'+identity+'" class="pdf-short-resource-row" style="break-inside: avoid">'
        assert source.count(before)==1
        source = source.replace(before,'<tr data-item-id="'+identity+'">',1)
    return source
