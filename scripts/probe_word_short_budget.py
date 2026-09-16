"""Shared short-budget selection plus pinned Pandoc AST/DOCX column oracle."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from jinja2 import Environment,FileSystemLoader
from markupsafe import Markup
from lxml import etree
from probe_q8_word import ROOT,IMAGE,RUNNER
from probe_short_budget import fragments
from probe_pdf_budget_reading import matrix,render
from generate_pilot_fixtures import IDS
from word_short_budget_contract import compare_ast,compare_blocks

HANDLER='  if div.identifier == "q-required-resources" then div = widen_short_budget_columns(div) end'


def examples(root):
    modules=[Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=a).get_template('src/budget-reading.html.j2').module for a in [False,True]]
    result=[]
    for name,rows,eligible in fragments():
        original='<table class="resource-table"><thead><tr><th>Purpose</th><th>Amount</th><th>Funder</th></tr></thead><tbody>'+''.join(
            '<tr><td>'+r['title']+r['purpose']+'</td><td>'+r['budget']+'</td><td>'+r['funding']+'</td></tr>' for r in rows)+'</tbody></table>'
        expected=original.replace('class="resource-table"','class="resource-table word-short-budget"',1) if eligible else original
        for module in modules:
            assert module.short_table(Markup(original),rows,True)==expected,(name,'Only Word class may change, including autoescape')
            assert module.short_table(Markup(original),rows)==expected.replace('word-short-budget','pdf-short-budget'),(name,'PDF behavior changed')
        result.append((name,'<div id="q-required-resources">'+expected+'</div>',int(eligible)))
    good=next(html for name,html,count in result if name=='rows-1')
    for name,html in [('unmarked',good.replace(' word-short-budget','')),
                      ('other-question',good.replace('q-required-resources','q-other')),
                      ('other-table',good.replace('resource-table','other-table')),
                      ('four-forged-rows',next(html for name,html,count in result if name=='rows-4').replace('resource-table','resource-table word-short-budget')),
                      ('spanning-cell',good.replace('<td>', '<td colspan="2">',1))]:
        result.append((name,html,0))
    _,base,_=matrix()[0]
    costs=next(p for p in base if p.endswith(IDS['costQUuid']));first=costs+'.'+base[costs][0]
    for name,updates,eligible in [('complete',{},False),('missing-currency',{first+'.'+IDS['costCurrencyQUuid']:''},True),
        ('missing-amount',{first+'.'+IDS['costAmountQUuid']:''},True),
        ('missing-both',{first+'.'+IDS['costAmountQUuid']:'',first+'.'+IDS['costCurrencyQUuid']:''},True),
        ('long-fallback',{first+'.'+IDS['costCurrencyQUuid']:'',first+'.'+IDS['costDescriptionQUuid']:'<p>'+'Long '*1000+'</p>'},False)]:
        replies=dict(base,**updates)
        for autoescape in [False,True]:
            before=render(root,replies,autoescape=autoescape);after=render(root,replies,autoescape=autoescape,word=True)
            assert after.replace('class="resource-table word-short-budget"','class="resource-table"')==before,(name,'Question output changed')
            assert len(BeautifulSoup(after,'html.parser').select('.word-short-budget'))==int(eligible)
        result.append(('question-'+name,after,int(eligible)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    source=a.source_dir/'src/word/pilot.lua';lua=source.read_text();assert lua.count(HANDLER)==1
    cases=examples(a.source_dir)
    html=''.join('<div id="'+name+'"><h2>CASE: '+name+'</h2>'+body+'</div>' for name,body,_ in cases)
    results=[]
    for variant in [lua.replace(HANDLER,''),lua]:
        raw=subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],
            input=json.dumps({'html':html,'lua':variant,'reference':base64.b64encode((a.source_dir/'src/word/reference.docx').read_bytes()).decode()}).encode())
        results.append(json.loads(raw))
    asts=[{b['c'][0][0]:b for b in r['ast']['blocks']} for r in results]
    word_changes=compare_blocks(*[[etree.fromstring(v) for v in r['word_blocks']] for r in results])
    rows=[]
    for name,html,count in cases:
        changes=compare_ast(asts[0][name],asts[1][name]);assert changes==count,(name,changes,count)
        rows.append({'case':name,'changed_tables':changes,'passed':True})
    assert word_changes==sum(row['changed_tables'] for row in rows)
    digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'passed':True,'release_acceptance':False,'rows':rows,'docx_changed_tables':word_changes,'worker_image':IMAGE,
        'checker_sha256':digest(Path(__file__)),'contract_sha256':digest(ROOT/'scripts/word_short_budget_contract.py'),
        'source_sha256':{str(f.relative_to(a.source_dir)):digest(f) for f in [source,a.source_dir/'src/budget-reading.html.j2',a.source_dir/'src/questions/15-required-resources.html.j2']},
        'limits':['Same shared selection for both languages; no prompt-text matching','AST and DOCX column grid only; not Microsoft Word visual acceptance']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'changed_tables':word_changes}))


if __name__=='__main__':main()
