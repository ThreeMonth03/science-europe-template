"""Pinned public renderer: exact selector matches and bounded style differences.

The small synthetic layout tests rule scope, not full document typography.
Full prepared fonts, private snapshots and page counts are checked separately.
"""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from bs4 import BeautifulSoup

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_budget_word import IMAGE

def load(name):
    spec=importlib.util.spec_from_file_location('sections_engine_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

BASE_CSS='''@page {size:A4; margin:20mm 19mm 22mm;}
body {font:11pt sans-serif; line-height:1.5;}
html body h2 {font-size:15pt; line-height:1.35; margin:1.3em 0 .65em;}
html body h3 {font-size:11pt; line-height:1.5; font-weight:normal; margin:.4em 0 .15em;}
html body h2,html body h3 {break-after:avoid;break-inside:avoid;}
html body section {margin-bottom:1.4em;}
html body .question {margin-top:.5em;}
html body p {margin:0 0 .5em;}
'''

RUNNER=r'''
import json,sys
from weasyprint import HTML,CSS,__version__
from cssselect2 import ElementWrapper,compile_selector_list
p=json.load(sys.stdin);rows=[];rendered=[]
selectors=[compile_selector_list(s)[0] for s in p['selectors']]
for case,source,expected in p['cases']:
 tree=ElementWrapper.from_html_root(HTML(string=source).etree_element)
 actual=[e.etree_element.get('id') for e in tree.iter_subtree() if any(s.test(e) for s in selectors)]
 assert actual==expected,(case,'selector/parsed-tree mismatch',actual,expected)
 rows.append(dict(case=case,matched=actual,passed=True))
for case,source,expected in p['render_cases']:
 for media in ['print','screen']:
  pairs=[]
  for suffix in ['',p['css']]:
   html=HTML(string=source,media_type=media)
   doc=html.render(stylesheets=[CSS(string=p['base_css']+suffix,media_type=media)])
   boxes=[(n,b) for n,page in enumerate(doc.pages,1) for b in page._page_box.descendants()]
   text=[b.text for _,b in boxes if type(b).__name__=='TextBox']
   geometry=[(n,round(b.position_x,4),round(b.position_y,4),round(b.width,4),round(b.height,4),b.text) for n,b in boxes if type(b).__name__=='TextBox']
   blocks=[b for _,b in boxes if type(b).__name__=='BlockBox' and b.element is not None]
   parents={c:node for node in html.etree_element.iter() for c in node}
   pairs.append((doc,text,geometry,blocks,parents))
  a,b=pairs;assert a[1]==b[1],(case,media,'text/order changed')
  assert len(a[3])==len(b[3]),(case,media,'block count changed')
  changed=[]
  for x,y in zip(a[3],b[3]):
   assert x.element.tag==y.element.tag and dict(x.element.attrib)==dict(y.element.attrib)
   parent=a[4].get(x.element)
   section=x.element.get('id') if x.element.tag=='section' else None
   if x.element.tag=='h2' and parent is not None and parent.tag=='section':section=parent.get('id')
   allowed={'margin_bottom'} if x.element.tag=='section' else ({'margin_top','margin_bottom'} if x.element.tag=='h2' else set())
   if media!='print' or section not in expected:allowed=set()
   keys=set(x.style)|set(y.style)
   diff={key for key in keys if str(x.style.get(key))!=str(y.style.get(key))}
   assert diff<=allowed,(case,media,x.element.tag,sorted(diff-allowed))
   if diff:changed.append((x.element.tag,section,sorted(diff)))
  if media=='screen' or not expected:assert a[2]==b[2],(case,media,'fallback geometry changed')
  else:assert changed,(case,'selector matched but no spacing changed')
  rendered.append(dict(case=case,media=media,passed=True,changed_blocks=len(changed),pages_before=len(a[0].pages),pages_after=len(b[0].pages)))
print(json.dumps(dict(passed=True,weasyprint=__version__,selector_cases=rows,render_cases=rendered)))
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    recipe=load('recipe');probe=load('probe')
    rows=[(name,source,probe.expected(BeautifulSoup(source,'html.parser'))) for name,source in probe.cases()]
    # All six shapes, mixed first/last answers, unknown/nested/authored structures.
    chosen=[r for r in rows if r[2]]
    wanted={'sec-data-collection-01','sec-data-collection-10','sec-sharing-preservation-0001',
            'sec-sharing-preservation-1000','unknown-section','wrong-parent','extra-authored-table','nested-authored-markers'}
    chosen += [r for r in rows if r[0] in wanted]
    assert len(chosen)==14
    payload=dict(css=recipe.CSS.decode(),selectors=recipe.SELECTORS,base_css=BASE_CSS,cases=rows,render_cases=chosen)
    done=subprocess.run(['docker','run','--rm','--network','none','--log-driver','none','--entrypoint','python','-i',IMAGE,'-c',RUNNER],
        input=json.dumps(payload).encode(),capture_output=True,timeout=300)
    if done.returncode:
        args.output.with_suffix('.failure.log').write_bytes(done.stderr);raise RuntimeError('Scoped engine checks failed; see failure log')
    result=json.loads(done.stdout);result.update(worker_image=IMAGE,prototype_only=True,release_acceptance=False,
        full_document_typography_checked=False,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        css_sha256=hashlib.sha256(recipe.CSS).hexdigest())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,selector_cases=len(rows),render_cases=len(result['render_cases']))))
if __name__=='__main__':main()
