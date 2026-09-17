"""Independent bounded Q5 layout oracle; all prose/attributes are retained."""
import copy
import json
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from probe_pdf_budget_reading import dom

QUESTION = 'src/questions/05-store-backup.html.j2'
FACTS = {'working-storage-arrangement', 'backup-reliability', 'workspace-management', 'storage-capacity', 'loss-prevention', 'backup-arrangement'}


def without_reviewed_context(source,kind):
    import hashlib
    from probe_storage_context import strip
    if kind == 'css' and '/* BEGIN metadata gap panel:' in source:
        from metadata_gap_panel_contract import prior_css
        source = prior_css(source)
    if kind == 'lua' and '-- BEGIN joined Q5 Word lead' in source:
        from q5_word_join_contract import prior_lua
        source = prior_lua(source)
    prior,block=strip(source,kind)
    delta=json.loads((Path(__file__).resolve().parents[1]/'docs/storage-context-style-delta.json').read_text())[kind]
    assert hashlib.sha256(block.encode()).hexdigest()==delta['block_sha256'], 'Unreviewed Q5 style block'
    assert hashlib.sha256(prior.encode()).hexdigest()==delta['baseline_sha256'], 'Unreviewed non-Q5 style change'
    return prior


def units(text): return sum(2 if ord(c)>=0x2e80 else 1 for c in text)


def eligible(answer):
    children = answer.find_all(recursive=False)
    if len(children)!=2: return False
    policy, limits = children
    if policy.name!='div' or policy.get('class')!=['workspace-policy','dataset-policy']: return False
    if limits.name!='div' or limits.get('class')!=['data-gap','template-gap','storage-detail-limits']: return False
    paragraphs=policy.find_all(recursive=False)
    if not 1<=len(paragraphs)<=5: return False
    if any(p.name!='p' or p.find(True) or p.get('data-fact-id') not in FACTS or p.get('data-status') not in ['complete','explicit-no'] for p in paragraphs): return False
    contents=limits.find_all(recursive=False)
    if len(contents)!=2 or [n.name for n in contents]!=['p','ul'] or contents[0].attrs or contents[0].find(True): return False
    items=contents[1].find_all(recursive=False)
    if len(items)!=2: return False
    for node,fact in zip(items,['storage-location','backup-frequency']):
        if node.name!='li' or node.find(True) or node.attrs!={'data-requirement-id':'SE-3a','data-fact-id':fact,'data-status':'unmapped'}: return False
    values=[' '.join(n.get_text().split()) for n in paragraphs+[contents[0]]+items]
    return all(values) and units(' '.join(values))<=900


def compare(before,after):
    result=copy.deepcopy(before); answer=result.select_one('#q-store-backup > .answer')
    selected=eligible(answer)
    if selected: answer['class'].append('q5-short-context')
    assert dom(result)==dom(after), 'Unexpected prose, fact, markup or non-Q5 change'
    return selected


def check_roots(root,fixtures,frozen):
    import test_science_europe_contract as adapter
    rows=[]
    wrapper="{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+QUESTION+"' %}"
    for escape in [False,True]:
        env=Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=escape)
        env.filters.update(reply_path=adapter.reply_path,reply_items=adapter.reply_items,reply_str_value=adapter.reply_str_value,markdown=lambda v:v,any=any)
        env.tests['true']=lambda v:v is True
        prior=env.overlay(loader=ChoiceLoader([DictLoader({QUESTION:frozen.read_text()}),env.loader]))
        templates=[prior.from_string(wrapper),env.from_string(wrapper)]
        for file in sorted(fixtures.glob('*.events.json')):
            replies={e['path']:e['value']['value'] for e in json.loads(file.read_text())}
            soups=[BeautifulSoup(t.render(repliesMap=replies),'html.parser') for t in templates]
            selected=compare(*soups)
            assert not soups[1].select('p p,p div,p ul,p table')
            rows.append(dict(case=file.stem,autoescape=escape,eligible=selected))
    return rows


def fragment(policy='Policy.',intro='Limitations:',first='Location unknown.',last='Schedule unknown.'):
    return '<div class="workspace-policy dataset-policy"><p data-requirement-id="SE-3a" data-fact-id="working-storage-arrangement" data-status="complete">'+policy+'</p></div><div class="data-gap template-gap storage-detail-limits"><p>'+intro+'</p><ul><li data-requirement-id="SE-3a" data-fact-id="storage-location" data-status="unmapped">'+first+'</li><li data-requirement-id="SE-3a" data-fact-id="backup-frequency" data-status="unmapped">'+last+'</li></ul></div>'


def fragments():
    base=fragment(); overhead=units(' '.join(['','Limitations:','Location unknown.','Schedule unknown.']))
    cases=[('plain',base,True),('chinese',fragment('計畫資料。','限制：','地點未定。','排程未定。'),True)]
    for length in [900-overhead,901-overhead,3000]:cases.append(('ascii-'+str(length),fragment('x'*length),length==900-overhead))
    for length in [200,450,1500]:cases.append(('cjk-'+str(length),fragment('中'*length),length==200))
    for name,old,new in [
        ('missing','data-status="complete"','data-status="missing"'),('unknown-fact','working-storage-arrangement','other'),
        ('style','<p>','<p style="height:2000px">'),('link','Policy.','<a href="https://example.org">Policy.</a>'),
        ('strong','Policy.','<strong>Policy.</strong>'),('break','Policy.','First<br>Second'),
        ('extra','</ul>','<li>Extra.</li></ul>'),('archive','</div><div class="data-gap','</div><h4>Archive</h4><div class="data-gap'),
        ('authored','Policy.','<span data-author="original">Original.csv</span>')]:cases.append((name,base.replace(old,new),False))
    return cases
