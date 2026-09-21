"""Native Pandoc oracle: exact original blocks, repeating identities, bounded rows."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from probe_budget_word import IMAGE, ROOT, RUNNER, fixture

HANDLER='  if div.identifier == "q-required-resources" then div = expand_long_budget_tables(div) end'


def example(n=20,cell='Purpose.',rows=1,projects=1):
    return fixture(cell='</p><p>'.join([cell]*n),rows=rows,projects=projects)


def cases(grouped=False):
    long=example()
    mixed=fixture(rows=3).replace('Resource 1</strong></p><div class="answer-detail"><p>Purpose.',
        'Resource 1</strong></p><div class="answer-detail"><p>'+'</p><p>'.join(['Original.']*20))
    result = [
        ('long',long,True),('threshold-twelve',example(n=11),True),
        ('chinese',example(cell='保留原始用途。'),True),('two-resources',example(rows=2),True),
        ('two-projects',example(projects=2),True),
        ('short-long-short',mixed,True),
        ('duplicate-titles',example(rows=2).replace('Resource 1','Resource 0').replace('<td>0 TWD</td>','<td>5000 TWD</td>',1),True),
        ('rich-inline',example(cell='<em>Keep</em> <strong>original</strong> <code>Cost-2027.csv</code> <a href="https://example.org/fund">record</a>.'),True),
        ('flat-list',long.replace('</div><p>Findability.','<ul><li>Keep first.</li><li>Keep second.</li></ul></div><p>Findability.'),True),
        ('threshold-eleven',example(n=10),False),('short',fixture(),False),
        ('many-short',fixture(rows=8),False),('too-many-resources',example(rows=33),False),
        ('too-many-paragraphs',example(n=161),False),('wide-paragraph',example(cell='中'*401),False),
        ('long-metadata',long.replace('Institute.','中'*121),False),
        ('forced-line-breaks',example(cell='First.<br>Second.'),False),
        ('large-amount',long.replace('0 TWD','1'*81),False),
        ('long-title',long.replace('Resource 0','x'*161),False),
        ('nested-table',example(cell='<table><tr><td>Nested.</td></tr></table>'),False),
        ('image',example(cell='<img src="no-fetch.png" alt="Figure">'),False),
        ('nested-list',long.replace('</div><p>Findability.','<ul><li>A<ul><li>B</li></ul></li></ul></div><p>Findability.'),False),
        ('long-list',long.replace('</div><p>Findability.','<ul>'+'<li>A</li>'*9+'</ul></div><p>Findability.'),False),
        ('metadata-list',long.replace('Institute.','<ul><li>Funder.</li></ul>'),False),
        ('column-span',long.replace('<td>0 TWD</td>','<td colspan="2">0 TWD</td>'),False),
        ('other-table',long.replace('resource-table','other-table'),False),
        ('wrong-question',long.replace('q-required-resources','q-other'),False),
        ('extra-heading',long.replace('<p>Findability.</p>','<h4>Authored heading</h4>'),False),
    ]
    if not grouped: return result
    from bs4 import BeautifulSoup
    result = [(name, html, selected or name == 'too-many-resources') for name, html, selected in result]
    for count in [32,33,34,64,65,66]:
        soup = BeautifulSoup(fixture(rows=count), 'html.parser')
        last = soup.select('tbody tr')[-1].select_one('.answer-detail')
        for n in range(20):
            node = soup.new_tag('p'); node.string = f'Original detail [{n}].'; last.append(node)
        result.append((f'mixed-{count}', str(soup), True))
    large = next(html for name, html, _ in result if name == 'mixed-65')
    result += [('large-invalid-metadata',large.replace('Institute.','<ul><li>Funder.</li></ul>',1),False),
               ('large-invalid-purpose',large.replace('Original detail [0].','<img src="no-fetch.png" alt="Keep">'),False),
               ('large-no-long',fixture(rows=65),False)]
    return result


def units(blocks):
    """Preserve each original block plus every ancestor Div's attributes."""
    result=[]
    for block in blocks:
        if block['t']=='Div':
            for child in units(block['c'][1]): result.append({'t':'Div','c':[copy.deepcopy(block['c'][0]),[child]]})
        else: result.append(copy.deepcopy(block))
    return result


def expand_expected(table, grouped=False):
    c=table['c']; result=[]; pending=[]
    def flush():
        if pending:
            item=copy.deepcopy(table); item['c'][4][0][3]=copy.deepcopy(pending); result.append(item); pending.clear()
    for row in c[4][0][3]:
        parts=units(row[1][0][4][1:])
        if len(parts)<12:
            if grouped and len(pending)==32: flush()
            pending.append(row); continue
        flush(); item=copy.deepcopy(table); out=item['c']
        out[0][1].append('long-resource-table'); out[0][2].append(['custom-style','PilotLongBudget'])
        identity=copy.deepcopy(row); identity[1][0][4]=[copy.deepcopy(row[1][0][4][0])]
        out[3][1]=[copy.deepcopy(c[3][1][0]),identity]; out[4][0][3]=[]
        for part in parts:
            cell=copy.deepcopy(row[1][0]); cell[3]=3; cell[4]=[part]
            out[4][0][3].append([copy.deepcopy(row[0]),[cell]])
        result.append(item)
    flush(); return result


def expected(node, grouped=False):
    if isinstance(node,list):
        result=[]
        for value in node:
            if isinstance(value,dict) and value.get('t')=='Table': result.extend(expand_expected(value,grouped))
            else: result.append(expected(value,grouped))
        return result
    if isinstance(node,dict): return {k:expected(v,grouped) for k,v in node.items()}
    return node


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--container',choices=['science-europe-pilot-docworker-1']); a=p.parse_args()
    lua=(ROOT/'src/word/pilot.lua').read_text(); assert lua.count(HANDLER)==1
    from budget_grouping_contract import WORD_BATCHED
    grouped = WORD_BATCHED in lua
    tests=cases(grouped=grouped); html=''.join('<div id="'+name+'">'+body+'</div>' for name,body,_ in tests)
    command=['docker','exec','-i',a.container,'python'] if a.container else ['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE]
    results=[]
    for variant in [lua.replace(HANDLER,''),lua]:
        ast=json.loads(subprocess.check_output(command+['-c',RUNNER],input=json.dumps({'lua':variant,'html':html}).encode()))
        results.append({b['c'][0][0]:b for b in ast['blocks']})
    rows=[]
    for name,_,eligible in tests:
        before,after=[r[name] for r in results]
        assert after==(expected(before,grouped) if eligible else before),(name,'Unexpected AST change')
        assert (before!=after)==eligible,name
        rows.append({'case':name,'eligible':eligible,'passed':True})
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'passed':True,'release_acceptance':False,'rows':rows,'worker_image':IMAGE,
        'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        'checker_sha256':digest(Path(__file__)),'helper_sha256':{'scripts/probe_budget_word.py':digest(ROOT/'scripts/probe_budget_word.py')},
        'lua_sha256':digest(ROOT/'src/word/pilot.lua'),
        'limits':['Handler-disabled AST comparison, not historic native outputs','No whole-DMP or Microsoft Word acceptance']}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows)}))


if __name__=='__main__': main()
