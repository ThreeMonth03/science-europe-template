"""Pinned-engine check of the exact four-gap panel; not native DSW acceptance."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from probe_pdf_budget_reading import render
from probe_budget_word import IMAGE, ROOT

FACTS = ('specialist-expertise', 'hardware-software', 'repository-charges', 'resources-costing')
SELECTOR = 'html body #q-required-resources > .answer' + ''.join(
    ':has(> p.data-gap[data-fact-id="'+fact+'"][data-status="missing"]:'+
    ('first-child' if i == 1 else f'nth-child({i})')+(':last-child' if i == 4 else '')+')'
    for i, fact in enumerate(FACTS, 1))
BEGIN = '/* BEGIN empty-Q15 panel:'
END = '/* END empty-Q15 panel */'


def split_css(css):
    assert css.count(BEGIN) == css.count(END) == 1
    before, rest = css.split(BEGIN); panel, after = rest.split(END)
    return before+after.removeprefix('\n'), BEGIN+panel+END


def prepared_css(root):
    css=(root/'src/layout.css').read_text()
    placeholder='{{ assets("src/fonts/PilotTC.ttf").data_base64 }}'
    font=root/'src/fonts/PilotTC.ttf'
    if placeholder in css:
        assert font.is_file()
        css=css.replace(placeholder,base64.b64encode(font.read_bytes()).decode())
    assert '{{ assets(' not in css
    return css


def cases(source):
    result=[('empty',source,True)]
    def changed(name,edit):
        soup=BeautifulSoup(source,'html.parser');edit(soup)
        result.append((name,str(soup),False))
    changed('wrong-question',lambda s:s.select_one('.question').__setitem__('id','q-other'))
    changed('wrong-fact',lambda s:s.select_one('[data-fact-id="hardware-software"]').__setitem__('data-fact-id','other'))
    changed('explicit-no',lambda s:s.select_one('.data-gap').__setitem__('data-status','explicit-no'))
    changed('unrecognized-status',lambda s:s.select_one('.data-gap').__setitem__('data-status','unrecognized'))
    changed('no-gap-class',lambda s:s.select_one('.data-gap').__setitem__('class',[]))
    changed('missing-last',lambda s:s.select('.data-gap')[-1].decompose())
    changed('duplicate-last',lambda s:s.select_one('.answer').append(copy.deepcopy(s.select('.data-gap')[-1])))
    changed('wrong-order',lambda s:s.select_one('.answer').insert(0,s.select('.data-gap')[1].extract()))
    def add_author(s,before=False,long=False):
        detail=s.new_tag('div',attrs={'class':'answer-detail'})
        for i in range(60 if long else 1):
            p=s.new_tag('p');p.string=f'Original answer {i+1}.';detail.append(p)
        answer=s.select_one('.answer');answer.insert(0,detail) if before else answer.append(detail)
    changed('author-before',lambda s:add_author(s,True))
    changed('author-after',lambda s:add_author(s))
    changed('long-author',lambda s:add_author(s,long=True))
    changed('nested-answer',lambda s:s.select_one('.answer').wrap(s.new_tag('section')))
    return result


RUNNER = '''import json,sys,re
from weasyprint import HTML,__version__
from cssselect2 import ElementWrapper,compile_selector_list
p=json.load(sys.stdin);rows=[]
keys=['font_size','line_height','margin_bottom','padding_top','padding_bottom','border_top_width','border_bottom_width','border_left_width']
for case,source,eligible in p['cases']:
    print(case,file=sys.stderr,flush=True)
    snapshots=[]
    for css in [p['before'],p['after']]:
        doc=HTML(string='<style>'+css+'</style><div style="height:205mm">Before.</div>'+source).render()
        paragraphs=[b for page in doc.pages for b in page._page_box.descendants() if type(b).__name__=='BlockBox' and b.element.tag=='p']
        panels=[b for page in doc.pages for b in page._page_box.descendants() if type(b).__name__=='BlockBox' and b.element.get('class')=='answer']
        texts=[''.join(b.text for b in page._page_box.descendants() if type(b).__name__=='TextBox') for page in doc.pages]
        # Retain each document/font configuration while inspecting its boxes.
        snapshots.append((paragraphs,panels,texts,doc))
    a,b=snapshots; compact=lambda texts:re.sub(r'\\s+','',''.join(texts))
    assert compact(a[2])==compact(b[2]),(case,'text changed')
    assert len(a[0])==len(b[0]),(case,'paragraph count changed')
    if eligible:
        assert len(b[1])==1 and b[1][0].style['border_left_width']==3
        assert len(b[0])==4 and all(x.style['border_left_width']==0 for x in b[0])
        assert [x.style['font_size'] for x in a[0]]==[x.style['font_size'] for x in b[0]]
        assert [x.style['line_height'] for x in a[0]]==[x.style['line_height'] for x in b[0]]
        assert len([t for t in b[2] if '15.' in t])==1
        assert b[1][0].height<a[1][0].height
    else:
        assert [[str(x.style[k]) for k in keys] for x in a[0]+a[1]]==[[str(x.style[k]) for k in keys] for x in b[0]+b[1]],case
        assert a[2]==b[2],(case,'fallback pagination changed')
    root=ElementWrapper.from_html_root(HTML(string='<html><body>'+source+'</body></html>').etree_element)
    count=sum(compile_selector_list(p['selector'])[0].test(e) for e in root.iter_subtree())
    assert count==int(eligible),(case,count)
    rows.append({'case':case,'eligible':eligible,'passed':True,'pages':len(b[2])})
print(json.dumps({'weasyprint':__version__,'rows':rows}))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    css=prepared_css(a.source_dir);before,panel=split_css(css)
    assert panel.count(SELECTOR)==3
    payload={'cases':cases(render(a.source_dir,{},True)),'before':before,'after':css,'selector':SELECTOR}
    result=subprocess.run(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(payload).encode(),capture_output=True)
    if result.returncode:
        failure=a.output.with_suffix('.failure.json');assert not failure.exists()
        failure.write_text(json.dumps({'passed':False,'returncode':result.returncode,'stderr':result.stderr.decode(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
        raise RuntimeError('Pinned engine failed; see '+str(failure))
    report=json.loads(result.stdout)
    digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report.update(passed=True,release_acceptance=False,worker_image=IMAGE,checker_sha256=digest(Path(__file__)),css_sha256=digest(a.source_dir/'src/layout.css'))
    font=a.source_dir/'src/fonts/PilotTC.ttf'
    report['embedded_font_sha256']=digest(font) if font.is_file() else None
    assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(report['rows'])}))


if __name__=='__main__':main()
