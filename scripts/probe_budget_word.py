"""Pinned native Pandoc regression: bounded Q15 keeps, with no DSW credentials."""
import argparse
import copy
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


HEADING_CALL = 'attach_budget_headings(keep_short_budget_overview(div))'


def heading_cases():
    mark = lambda html: html.replace('<h4>Budget</h4>', '<h4 class="word-budget-heading">Budget</h4>')
    base = mark(fixture())
    multiple = mark(fixture(projects=2)).replace('<div class="project-resources">',
        '<div class="project-resources"><p><strong>Project &amp; record</strong></p>')
    return [
        ('short', base, 1), ('many', mark(fixture(rows=8)), 1),
        ('long-paragraph', mark(fixture(cell='Long purpose. '*200)), 1),
        ('expanded-long', mark(fixture(cell='</p><p>'.join(['Original purpose.']*20))), 1),
        ('chinese', base.replace('Budget</h4>', '資料管理預算</h4>').replace('Purpose.', '保留研究紀錄。'), 1),
        ('no-amount', base.replace('0 TWD','TWD'), 1), ('no-currency', base.replace('0 TWD','0'), 1),
        ('no-funding', base.replace('Institute.',''), 1), ('no-purpose', base.replace('Purpose.',''), 1),
        ('two-projects', multiple, 2),
        ('first-empty-project', multiple.replace('<div class="project-resources">',
            '<div class="project-resources"><p>No budget provided.</p></div><div class="project-resources">',1), 2),
        ('unnamed-second', 'Project 2'.join(multiple.rsplit('Project &amp; record',1)), 2),
        ('long-project-label',multiple.replace('Project &amp; record','計畫名稱'*100),0),
        ('image-project-label',multiple.replace('Project &amp; record','<img src="unused.png" alt="Keep">'),0),
        ('unmarked', fixture(), 0), ('other-question',base.replace('q-required-resources','q-other'),0),
        ('other-table',base.replace('resource-table','authored-table'),0),
        ('authored-wrapper',base.replace('project-resources','answer-detail'),0),
        ('no-table',mark(fixture(rows=0)),0),
        ('trailing-prose',base.replace('</table>','</table><p>Keep after budget.</p>'),1),
        ('intervening-prose',base.replace('<div class="project-resources">','<p>Keep here.</p><div class="project-resources">'),0),
    ]


def verify_heading_move(before, after):
    """Undo only exact block moves; all original cells/styles/order must survive."""
    restored = copy.deepcopy(after)
    def question(node):
        if isinstance(node,dict):
            if node.get('t')=='Div' and node['c'][0][0]=='q-required-resources': return node
            for value in node.values():
                found=question(value)
                if found is not None: return found
        elif isinstance(node,list):
            for value in node:
                found=question(value)
                if found is not None: return found
    old,new=question(before),question(restored)
    if old is None:
        assert before==after
        return 0
    answer=lambda q:next(b for b in q['c'][1] if b['t']=='Div' and 'answer' in b['c'][0][1])
    old,new=answer(old)['c'][1],answer(new)['c'][1]
    headers=[(i,b) for i,b in enumerate(old) if b['t']=='Header' and 'word-budget-heading' in b['c'][1][1]]
    if not headers:
        assert before==after
        return 0
    heading_index,heading=headers[0]
    projects=lambda blocks:[b for b in blocks if b['t']=='Div' and 'project-resources' in b['c'][0][1]]
    originals,changed=projects(old),projects(new)
    assert len(originals)==len(changed)
    moved=0
    for original,current in zip(originals,changed):
        tables=lambda p:[b for b in p['c'][1] if b['t']=='Table']
        a,b=tables(original),tables(current)
        assert len(a)==len(b)
        if not a or a[0]==b[0]: continue
        head=b[0]['c'][3][1]
        assert len(head)==len(a[0]['c'][3][1])+1
        row=head.pop(0)
        assert len(row[1])==1 and row[1][0][2:4]==[1,3]
        blocks=row[1][0][4]
        expected=[]
        if current is changed[0] and original is old[heading_index+1]:
            expected.append(heading)
            new.insert(heading_index,copy.deepcopy(heading))
        if original['c'][1][0]['t']!='Table':
            label=original['c'][1][0]
            expected.append(label)
            current['c'][1].insert(0,copy.deepcopy(label))
        assert blocks==expected, 'Only the original title and matching project label may move'
        if original is originals[-1] and original is old[-1] and original['c'][1][-1]['t']=='Table':
            ending=('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
                    '<w:keepNext w:val="0"/><w:snapToGrid w:val="0"/>'
                    '<w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr></w:p>')
            assert current['c'][1].pop()=={'t':'RawBlock','c':['openxml',ending]}, 'Exactly one empty table-ending paragraph'
        moved+=1
    assert restored==before, 'All original bodies, styles, identities and surrounding blocks must survive'
    return moved


def check_current_headings():
    lua=(ROOT/'src/word/pilot.lua').read_text()
    assert lua.count(HEADING_CALL)==1
    cases=heading_cases()
    html=''.join('<div id="'+name+'">'+body+'</div>' for name,body,_ in cases)
    results=[]
    for source in [lua.replace(HEADING_CALL,'keep_short_budget_overview(div)'),lua]:
        raw=subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],
            input=json.dumps(dict(html=html,lua=source)).encode())
        results.append({b['c'][0][0]:b for b in json.loads(raw)['blocks']})
    for name,_,count in cases:
        assert verify_heading_move(results[0][name],results[1][name])==count,name
    return dict(passed=True,cases=len(cases),moved_tables=sum(c for _,_,c in cases))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--container',choices=['science-europe-pilot-docworker-1']); a=p.parse_args()
    source=ROOT/'src/word/pilot.lua'
    from current_repairs_contract import project_embedded_text
    lua=project_embedded_text(source.read_text(),'src/word/pilot.lua'); assert lua.count(HANDLER)==1
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
        'current_budget_headings':check_current_headings(),
        'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'lua_sha256':hashlib.sha256(lua.encode()).hexdigest(),
        'current_lua_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'limits':['Baseline disables only the new Q15 handler; native historic documents are compared separately','AST, not full-page or Microsoft Word acceptance']}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'pandoc':version}))


if __name__=='__main__': main()
