"""Pinned native Pandoc regression: bounded Q15 keeps, with no DSW credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
IMAGE='datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'
HANDLER='  if div.identifier == "q-required-resources" then return keep_short_budget_overview(div) end'
RUNNER='''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/"pilot.lua";f.write_text(p["lua"])
 print(subprocess.check_output(["pandoc","--from=html","--to=json","--lua-filter="+str(f)],input=p["html"].encode()).decode())
'''


def fixture(overview='<p>Overview.</p><p>Charges apply.</p>',rows=2,cell='Purpose.',projects=1):
    table='<table class="resource-table"><thead><tr><th>Purpose</th><th>Amount</th><th>Funder</th></tr></thead><tbody>'+''.join('<tr><td><p><strong>Resource '+str(i)+'</strong></p><div class="answer-detail"><p>'+cell+'</p></div><p>Findability.</p></td><td>0 TWD</td><td>Institute.</td></tr>' for i in range(rows))+'</tbody></table>'
    return '<div id="q-required-resources"><h3>15. Resources?</h3><div class="answer">'+overview+'<h4>Budget</h4>'+('<div class="project-resources">'+table+'</div>')*projects+'</div></div>'


def cases():
    base=fixture()
    return [
        ('short',base,True),('single',fixture(rows=1),True),
        ('chinese',fixture(overview='<p>本計畫將安排培訓。</p><p>已編列預算。</p>',cell='保存資料及後設資料。'),True),
        ('flat-list',fixture(overview='<p>Overview.</p><ul><li>First.</li><li>Second.</li></ul><p>Charges.</p>'),True),
        ('emphasis',fixture(cell='<em>Original</em> <strong>wording</strong>.'),True),
        ('long-overview',fixture(overview='<p>'+'word '*210+'</p>'),False),
        ('wide-cjk',fixture(overview='<p>'+'中'*510+'</p>'),False),
        ('three-rows',fixture(rows=3),False),('two-projects',fixture(rows=1,projects=2),False),
        ('long-cell',fixture(rows=1,cell='a'*201),False),
        ('many-cell-paragraphs',fixture(cell='First.</p><p>Second.'),False),
        ('many-list-items',fixture(overview='<ul>'+'<li>Item.</li>'*4+'</ul>'),False),
        ('nested-list',fixture(overview='<ul><li>Item.<ul><li>Nested.</li></ul></li></ul>'),False),
        ('nested-table',fixture(cell='<table><tr><td>Nested.</td></tr></table>'),False),
        ('image',fixture(cell='<img src="not-fetched.png" alt="Figure">'),False),
        ('link',fixture(cell='<a href="https://example.org/budget">Original link</a>'),False),
        ('code',fixture(cell='<code>cost.csv</code>'),False),
        ('line-breaks',fixture(cell='First.<br>Second.'),False),
        ('span-cell',base.replace('<td>0 TWD</td>','<td colspan="2">0 TWD</td>'),False),
        ('other-table',base.replace('resource-table','other-table'),False),
        ('extra-heading',fixture(overview='<h4>Extra heading</h4><p>Overview.</p>'),False),
        ('trailing-prose',base.replace('</table>','</table><p>After budget.</p>'),False),
        ('no-budget',base[:base.index('<div class="project-resources">')]+'</div></div>',False),
        ('wrong-question',base.replace('q-required-resources','q-other'),False),
    ]


def allowed_changes(before,after):
    if before==after: return 0
    if isinstance(before,dict) and isinstance(after,dict):
        if before.get('t') in ['Para','Plain'] and after.get('t')=='Div':
            attr,blocks=after['c']
            assert attr in [['',[],[['custom-style','Pilot Lead']]],['',[],[['custom-style','Pilot List Lead']]]]
            assert blocks==[{'t':'Para','c':before['c']}], 'Text/inline content must not change'
            return 1
        assert before.keys()==after.keys()
        return sum(allowed_changes(before[k],after[k]) for k in before)
    if isinstance(before,list) and isinstance(after,list):
        assert len(before)==len(after)
        return sum(allowed_changes(a,b) for a,b in zip(before,after))
    raise AssertionError('Unexpected AST edit')


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--container',choices=['science-europe-pilot-docworker-1']); a=p.parse_args()
    source=ROOT/'src/word/pilot.lua'; lua=source.read_text(); assert lua.count(HANDLER)==1
    tests=cases(); html=''.join('<div id="'+name+'">'+body+'</div>' for name,body,_ in tests)
    command=['docker','exec','-i',a.container,'python'] if a.container else ['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE]
    asts=[]
    for variant in [lua.replace(HANDLER,''),lua]:
        ast=json.loads(subprocess.check_output(command+['-c',RUNNER],input=json.dumps({'lua':variant,'html':html}).encode()))
        asts.append({b['c'][0][0]:b for b in ast['blocks']})
    rows=[]
    for name,_,eligible in tests:
        before,after=[v[name] for v in asts]
        if eligible: changes=allowed_changes(before,after); assert changes>0,name
        else: assert before==after,(name,'Rejected AST must remain byte-for-byte equivalent'); changes=0
        rows.append({'case':name,'eligible':eligible,'changed_overview_paragraphs':changes,'passed':True})
    version=subprocess.check_output((['docker','exec',a.container,'pandoc'] if a.container else ['docker','run','--rm','--network','none','--entrypoint','pandoc',IMAGE])+['--version'],text=True).splitlines()[0]
    report={'passed':True,'release_acceptance':False,'rows':rows,'worker_image':IMAGE,'pandoc_version':version,
        'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'lua_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'limits':['Baseline disables only the new Q15 handler; native historic documents are compared separately','AST, not full-page or Microsoft Word acceptance']}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'pandoc':version}))


if __name__=='__main__': main()
