"""Pinned PDF and Pandoc regression for the bounded Q5 context unit."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from jinja2 import Environment,FileSystemLoader
from lxml import etree
from probe_budget_word import ROOT,IMAGE
from probe_q8_word import RUNNER as WORD_RUNNER
from probe_empty_pdf import prepared_css
from storage_context_contract import fragments,fragment

HANDLER='  if div.identifier == "q-store-backup" then return keep_q5_context(div) end\n'
CSS_BEGIN='/* BEGIN short Q5 context:'
CSS_END='/* END short Q5 context */\n'
LUA_BEGIN='-- BEGIN short Q5 context\n'
LUA_END='-- END short Q5 context\n\n'


def strip(source,kind):
    begin,end=(CSS_BEGIN,CSS_END) if kind=='css' else (LUA_BEGIN,LUA_END)
    assert source.count(begin)==source.count(end)==1
    a,tail=source.split(begin);block,b=tail.split(end)
    if kind=='lua':
        assert b.count(HANDLER)==1; b=b.replace(HANDLER,'')
    return a+b,begin+block+end


def word_changes(before,after,eligible):
    assert len(before)==len(after); changes=[]
    ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    for a,b in zip(before,after):
        x,y=etree.fromstring(a),etree.fromstring(b)
        if etree.tostring(x,method='c14n')==etree.tostring(y,method='c14n'):continue
        assert eligible and x.tag==y.tag==ns+'p','Unexpected Word block change'
        p,q=x.find(ns+'pPr'),y.find(ns+'pPr'); assert p is not None and q is not None
        old,new=p.find(ns+'pStyle'),q.find(ns+'pStyle'); assert old is not None and new is not None
        assert new.get(ns+'val') in ['PilotLead','PilotListLead']
        changes.append((''.join(y.itertext()),old.get(ns+'val'),new.get(ns+'val')))
        new.set(ns+'val',old.get(ns+'val'))
        assert etree.tostring(x,method='c14n')==etree.tostring(y,method='c14n'),'Word non-style XML changed'
    assert len(changes) in ([2,3] if eligible else [0]),changes
    return changes


def ast_changes(before,after):
    if before==after:return 0
    if isinstance(before,dict) and isinstance(after,dict):
        if before.get('t') in ['Para','Plain'] and after.get('t')=='Div':
            attrs,blocks=after['c']
            assert attrs in [['',[],[['custom-style','Pilot Lead']]],['',[],[['custom-style','Pilot List Lead']]]]
            assert blocks==[{'t':'Para','c':before['c']}]
            return 1
        assert before.keys()==after.keys()
        return sum(ast_changes(before[k],after[k]) for k in before)
    assert isinstance(before,list) and isinstance(after,list) and len(before)==len(after)
    return sum(ast_changes(a,b) for a,b in zip(before,after))


PDF_RUNNER='''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin);rows=[]
for name,source,eligible in p['cases']:
 for media in ['print','screen']:
  pair=[]
  for css in [p['before'],p['after']]:
   doc=HTML(string='<style>'+css+'</style><div style="height:210mm">Before.</div>'+source,media_type=media).render()
   boxes=[(i,b) for i,page in enumerate(doc.pages,1) for b in page._page_box.descendants()]
   text=''.join(b.text for i,b in boxes if type(b).__name__=='TextBox')
   paragraphs=[(i,round(b.position_y,4),round(b.height,4)) for i,b in boxes if type(b).__name__=='BlockBox' and b.element.tag in ['p','li','h3']]
   regions={i for i,b in boxes if type(b).__name__=='BlockBox' and b.element.get('class')=='answer q5-short-context'}
   pair.append((doc,text,paragraphs,regions))
  a,b=pair
  assert re.sub(r'\\s+','',''.join(a[1]))==re.sub(r'\\s+','',''.join(b[1])),(name,'text changed')
  if eligible and media=='print':
   assert len(b[3])==1,(name,'short context split',b[3])
   assert len({n for n,y,h in b[2]})==1,(name,'heading/answer not together')
  else:assert a[1:]==b[1:],(name,media,'fallback geometry changed')
  rows.append(dict(case=name,media=media,eligible=eligible,prior_pages=len(a[0].pages),pages=len(b[0].pages),passed=True))
print(json.dumps(dict(weasyprint=__version__,rows=rows)))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    helper=Environment(loader=FileSystemLoader(a.source_dir),extensions=['jinja2.ext.do']).get_template('src/storage-reading.html.j2').module
    cases=[(n,'<div id="q-store-backup"><h3>5. Storage?</h3>'+str(helper.answer(h))+'</div>',e) for n,h,e in fragments()]
    cases.append(('other-question',cases[0][1].replace('q-store-backup','q-other'),False))
    cases.append(('missing-hint',cases[0][1].replace(' q5-short-context',''),False))
    css=prepared_css(a.source_dir);prior,_=strip(css,'css')
    pdf=json.loads(subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',PDF_RUNNER],input=json.dumps(dict(cases=cases,before=prior,after=css)).encode()))
    lua=(a.source_dir/'src/word/pilot.lua').read_text();old_lua,_=strip(lua,'lua')
    # Also test forged hints on long/complex content: the actual AST must reject.
    # Pandoc discards p data-* attributes: semantic eligibility belongs to the
    # Jinja classifier. Independently recheck only length/structure retained in AST.
    word_cases=cases+[(n+'-forged-hint',h.replace('class="answer"','class="answer q5-short-context"'),False) for n,h,e in cases if not e and 'class="answer"' in h and (n.startswith(('ascii-','cjk-')) or n in ['link','strong','break','extra','archive','authored'])]
    combined=''.join('<div id="'+n+'"><h2>CASE: '+n+'</h2>'+h+'</div>' for n,h,_ in word_cases)
    results=[]
    for value in [old_lua,lua]:
        payload=dict(html=combined,lua=value,reference=base64.b64encode((a.source_dir/'src/word/reference.docx').read_bytes()).decode())
        results.append(json.loads(subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',WORD_RUNNER],input=json.dumps(payload).encode())))
    ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    def word_groups(result):
        groups={'prefix':[]};key='prefix'
        for value in result['word_blocks']:
            node=etree.fromstring(value);text=''.join(n.text or '' for n in node.iter(ns+'t'))
            if text.startswith('CASE: '):key=text[6:];groups[key]=[]
            groups[key].append(value)
        return groups
    words=[word_groups(r) for r in results];assert words[0]['prefix']==words[1]['prefix']
    asts=[{b['c'][0][0]:b for b in r['ast']['blocks']} for r in results];rows=[]
    for name,_,selected in word_cases:
        count=ast_changes(asts[0][name],asts[1][name]);assert count in ([2,3] if selected else [0]),(name,count)
        changes=word_changes(words[0][name],words[1][name],selected)
        rows.append(dict(case=name,eligible=selected,ast_changes=count,word_style_changes=len(changes),passed=True))
    report=dict(passed=True,release_acceptance=False,worker_image=IMAGE,pdf=pdf,word=rows,
                checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,pdf_checks=len(pdf['rows']),word_checks=len(rows))))


if __name__=='__main__':main()
