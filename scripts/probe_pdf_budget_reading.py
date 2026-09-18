"""Q15 presentation oracle: original fragments, format isolation, bounded headers."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup, Tag, Comment
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from markupsafe import Markup
from generate_budget_fixtures import budget_cases
from generate_pilot_fixtures import IDS
from generate_preservation_fixtures import preservation_cases
from probe_budget_word import IMAGE, ROOT
sys.path.insert(0, str(ROOT / 'tests'))
from test_science_europe_contract import reply_path, reply_items, reply_str_value

QUESTION = 'src/questions/15-required-resources.html.j2'


def matrix():
    raw = preservation_cases('en')['preservation-complete']
    base = {p: ({'value': {'value': v['value']}} if v['type'] == 'IntegrationReply' else v['value']) for p, v in raw.items()}
    costs = next(p for p in base if p.endswith(IDS['costQUuid'])); first = costs + '.' + base[costs][0]; second = costs + '.' + base[costs][1]
    desc = '.' + IDS['costDescriptionQUuid']
    funding = '.' + IDS['costCoverQUuid'] + '.' + IDS['costCoverOtherAUuid'] + '.' + IDS['costCoverOtherHowQUuid']
    for p in list(base):
        if p.endswith(desc): base[p] = '<p>Original purpose.</p>'
        if p.endswith(funding): base[p] = '<p>Institutional funds.</p>'
    def paragraphs(n, text='Retain Original-2027.csv and the audit trail.'):
        return ''.join(f'<p>PDF-PARA-{i:03d}: {text}</p>' for i in range(1, n+1))
    def case(name, updates, eligible):
        row = copy.deepcopy(base); row.update(updates); return name, row, eligible
    long = paragraphs(60)
    cases = [case('short', {}, []), case('long', {first+desc: long}, [0]),
        case('threshold-eleven', {first+desc: paragraphs(10)}, []),
        case('threshold-twelve', {first+desc: paragraphs(11)}, [0]),
        case('chinese-purpose', {first+desc: paragraphs(60, '保留原始用途及查核紀錄。')}, [0]),
        case('links-inline', {first+desc: paragraphs(20, '<em>Keep</em> <strong>exact</strong> <code>Cost.csv</code> <a href="https://example.org/funding?a=1&amp;b=2">record</a>.')}, [0]),
        case('flat-list', {first+desc: long+'<ul><li>First.</li><li>Second.</li></ul>'}, [0]),
        case('two-long-same-title', {first+desc: long, second+desc: long, second+'.'+IDS['costTitleQUuid']: base[first+'.'+IDS['costTitleQUuid']]}, [0, 1]),
        case('complex-then-long', {first+desc: long+'<h4>Original heading</h4>', second+desc: long}, [1]),
        case('long-title', {first+desc: long, first+'.'+IDS['costTitleQUuid']: 'T'*81}, []),
        case('long-funding', {first+desc: long, first+funding: '<p>'+'F'*101+'</p>'}, []),
        case('funding-link', {first+desc: long, first+funding: '<p><a href="https://example.org/funder">Funder</a></p>'}, []),
        case('missing-amount', {first+desc: long, first+'.'+IDS['costAmountQUuid']: ''}, [0]),
        case('missing-currency', {first+desc: long, first+'.'+IDS['costCurrencyQUuid']: ''}, [0]),
        case('missing-funding', {first+desc: long, first+funding: ''}, [0]),
        case('missing-allocation', {first+desc: long, first+'.'+IDS['costAllocationQUuid']: []}, [0]),
        case('missing-amount-and-currency', {first+desc: long, first+'.'+IDS['costAmountQUuid']: '', first+'.'+IDS['costCurrencyQUuid']: ''}, [0]),
        case('zero-missing-currency', {first+desc: long, first+'.'+IDS['costAmountQUuid']: '0', first+'.'+IDS['costCurrencyQUuid']: ''}, [0]),
        case('grant-missing-number', {first+desc: long, first+'.'+IDS['costCoverQUuid']: IDS['costCoverGrantAUuid']}, [0]),
        case('unknown-gap-attributes', {first+desc: long, first+funding: '<p class="data-gap" style="height:1000px">Unknown markup.</p>'}, []),
        case('single-huge-paragraph', {first+desc: '<p>'+'Long '*1000+'</p>'}, []),
        case('wide-paragraph', {first+desc: paragraphs(20, '中'*401)}, []),
        case('too-many-paragraphs', {first+desc: paragraphs(161)}, []),
        case('forced-break', {first+desc: paragraphs(20, 'First.<br>Second.')}, []),
        case('nested-list', {first+desc: long+'<ul><li>A<ul><li>B</li></ul></li></ul>'}, []),
        case('large-list', {first+desc: long+'<ul>'+'<li>A</li>'*9+'</ul>'}, []),
        case('image', {first+desc: long+'<img src="no-fetch.png">'}, []),
        case('nested-table', {first+desc: long+'<table><tr><td>Nested</td></tr></table>'}, [])]
    for count in [8, 32, 33]:
        row = copy.deepcopy(base)
        for i in range(2, count):
            item = 'resource-'+str(i); row[costs].append(item)
            for path, value in base.items():
                if path.startswith(first+'.'): row[costs+'.'+item+path[len(first):]] = copy.deepcopy(value)
        if count != 8: row[first+desc] = long
        cases.append((f'rows-{count}', row, [0] if count == 32 else []))
    projects = next(p for p in base if p.endswith(IDS['projectsQUuid'])); project = projects+'.'+base[projects][0]
    row = copy.deepcopy(base); row[first+desc] = long; row[projects].append('second-project')
    for path, value in list(row.items()):
        if path.startswith(project+'.'): row[projects+'.second-project'+path[len(project):]] = copy.deepcopy(value)
    cases.append(('two-projects', row, [0, 2]))
    return cases


def render(root, replies, pdf=False, question=None, autoescape=False, word=False):
    loaders = ([DictLoader({QUESTION: question})] if question is not None else []) + [FileSystemLoader(root)]
    env = Environment(loader=ChoiceLoader(loaders), extensions=['jinja2.ext.do'], autoescape=autoescape)
    env.filters.update(reply_path=reply_path, reply_items=reply_items, reply_str_value=reply_str_value, markdown=lambda value: Markup(value) if autoescape else value)
    template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+QUESTION+"' %}")
    return template.render(repliesMap=replies, pdf_budget_reading=pdf, word_budget_reading=word)


def dom(node):
    if isinstance(node, Comment): return None
    if not isinstance(node, Tag): return str(node) if str(node).strip() or node.parent.name in ['p', 'strong', 'em', 'a', 'code', 'span'] else None
    return [node.name, sorted(node.attrs.items()), [value for child in node.children if (value := dom(child)) is not None]]


def normalize_owned_allocation_indent(source):
    # Translation resegmentation trims only this owned paragraph's outer source
    # indentation. Never normalize author answer-detail paragraphs or inner text.
    soup = BeautifulSoup(source, 'html.parser')
    for p in soup.select('.resource-table > tbody > tr > td:first-child > p'):
        if not p.attrs and not p.find(True) and p.get_text().strip().startswith('支援項目：'):
            p.string = p.get_text().strip()
    return str(soup)


def expected(original, eligible):
    soup = BeautifulSoup(original, 'html.parser'); index = 0
    for table in list(soup.select('.resource-table')):
        rows = table.tbody.find_all('tr', recursive=False); changes = [index+i in eligible for i in range(len(rows))]; index += len(rows)
        if not any(changes): continue
        replacement = []; pending = []
        def flush():
            if not pending: return
            ordinary = copy.deepcopy(table); ordinary.tbody.clear()
            for row in pending: ordinary.tbody.append(copy.deepcopy(row))
            replacement.append(ordinary); pending.clear()
        for row, change in zip(rows, changes):
            if not change: pending.append(row); continue
            flush(); reading = copy.deepcopy(table); reading['class'].append('pdf-resource-reading'); reading['data-item-id'] = row['data-item-id']
            identity = copy.deepcopy(row); del identity['data-item-id']
            cell = identity.find('td'); title = copy.deepcopy(cell.find('p', recursive=False)); cell.clear(); cell.append(title)
            reading.thead.append(identity); reading.tbody.clear()
            body = soup.new_tag('tr'); purpose = soup.new_tag('td', colspan='3'); original_cell = copy.deepcopy(row.find('td')); original_cell.find('p', recursive=False).extract()
            for child in list(original_cell.contents): purpose.append(child.extract())
            body.append(purpose); reading.tbody.append(body); replacement.append(reading)
        flush()
        for node in replacement: table.insert_before(node)
        table.extract()
    return soup


def check(root, prior=None):
    results = []
    for name, replies, eligible in matrix():
        original = render(root, replies); pdf = render(root, replies, True)
        if prior is not None:
            before = render(root, replies, question=prior)
            historic_original = original
            question = (root/QUESTION).read_text()
            if 'resourceOverview.original' in question:
                # Prove the old table contract on the precisely unwrapped
                # question; keep the live joined original/pdf below. The new
                # pair has its own byte-exact bilingual/native gates.
                from resource_prose_contract import prior_question
                historic_original = render(root, replies, question=prior_question(question))
            assert historic_original == before or dom(BeautifulSoup(normalize_owned_allocation_indent(historic_original), 'html.parser')) == dom(BeautifulSoup(normalize_owned_allocation_indent(before), 'html.parser')), (name, 'Non-PDF output differs from 0.3.18 after exact owned-pair projection')
        if not eligible: assert pdf == original, (name, 'Fallback/control changed')
        assert dom(BeautifulSoup(pdf, 'html.parser')) == dom(expected(original, eligible)), (name, 'Unexpected structural/content change')
        results.append({'case': name, 'expanded_rows': len(eligible), 'passed': True})
    return results


ENGINE = '''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin); d=HTML(string='<style>'+p['css']+'</style>'+p['html']).render()
pages=[''.join(b.text for b in page._page_box.descendants() if type(b).__name__=='TextBox') for page in d.pages]
compact=lambda s:re.sub(r'\\s+','',s)
pages=[compact(s) for s in pages]; locations=[]
for i in range(1,61):
    marker=f'PDF-PARA-{i:03d}:'; hits=[n for n,s in enumerate(pages) if marker in s]; assert len(hits)==1,(marker,hits)
    assert all(compact(v) in pages[hits[0]] for v in p['identity']),('Missing identity',i)
    locations.extend(hits)
assert len(set(locations))>1
widths=[b.width/page._page_box.width for page in d.pages for b in page._page_box.descendants() if type(b).__name__=='TableCellBox' and b.element.get('colspan')=='3']
assert widths and min(widths)>.9,widths
print(json.dumps({'passed':True,'weasyprint':__version__,'purpose_pages':[i+1 for i in sorted(set(locations))],'min_purpose_width_ratio':min(widths)}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source-dir', type=Path, default=ROOT)
    p.add_argument('--prior-question', type=Path); p.add_argument('--output', type=Path, required=True); p.add_argument('--engine', action='store_true'); a = p.parse_args()
    prior_path = a.prior_question or (ROOT / 'tests/fixtures/budget-0.3.18.html.j2' if a.source_dir.resolve() == ROOT else None)
    result = {'passed': True, 'release_acceptance': False, 'rows': check(a.source_dir, prior_path.read_text() if prior_path else None)}
    if a.engine:
        result['engine'] = []
        for name, replies, _ in matrix():
            if name not in ['long', 'missing-amount', 'missing-currency', 'missing-funding', 'missing-allocation', 'missing-amount-and-currency', 'zero-missing-currency', 'grant-missing-number']: continue
            html = render(a.source_dir, replies, True)
            soup = BeautifulSoup(html, 'html.parser'); identity = [n.get_text() for n in soup.select_one('.pdf-resource-reading thead').select('tr')[-1].select('td')]
            payload = {'css': (a.source_dir/'src/layout.css').read_text(), 'html': html, 'identity': identity}
            engine = json.loads(subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',ENGINE], input=json.dumps(payload).encode()))
            result['engine'].append({'case': name, **engine})
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result.update({'checker_sha256': digest(Path(__file__)), 'source_sha256': {name: digest(a.source_dir/name) for name in [QUESTION, 'src/budget-reading.html.j2', 'src/pdf/index.html.j2', 'src/layout.css']},
        'helper_sha256': {name: digest(ROOT/name) for name in ['scripts/generate_budget_fixtures.py','scripts/generate_preservation_fixtures.py','scripts/generate_pilot_fixtures.py','scripts/probe_budget_word.py','tests/test_science_europe_contract.py']},
        'prior_question_sha256': digest(prior_path) if prior_path else None,
        'limits': ['HTML-fragment adapters, not a replacement Markdown parser', 'Engine probe is not a full native DSW export', 'Only captured fragments move; authored prose is not rewritten']})
    assert not a.output.exists(); a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': len(result['rows']), 'engine': result.get('engine')}))


if __name__ == '__main__': main()
