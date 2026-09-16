"""Bounded Q11 pairs: exact selector contracts and pinned print-engine geometry."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from probe_budget_word import ROOT,IMAGE
from probe_empty_pdf import prepared_css

BEGIN='/* BEGIN archive gap pairs:'
END='/* END archive gap pairs */'
PAIRS=[('archive-payer','archive-minimum-period'),('archive-extension-authority','archive-extension-basis'),
       ('archive-format-migration','archive-media-migration')]
BASE='html body #q-data-preservation .post-project-archive[data-scope="project"] > .dataset-policy > '


def gap(fact):
    return '.reading-gap:has(> p.data-gap[data-fact-id="'+fact+'"][data-status="missing"]:only-child:not(:has(*)))'


FIRST=[BASE+gap(a)+':has(+ '+gap(b)+')' for a,b in PAIRS]
LAST=[BASE+gap(a)+' + '+gap(b) for a,b in PAIRS]


def split_css(css):
    assert css.count(BEGIN)==css.count(END)==1
    left,rest=css.split(BEGIN);owned,right=rest.split(END)
    return left+right.removeprefix('\n'),BEGIN+owned+END


def rows(root):
    sys.path.insert(0,str(ROOT/'tests'))
    import test_science_europe_contract as adapter
    from test_preservation_coverage import plain
    from generate_pilot_fixtures import IDS
    previous=adapter.ROOT;adapter.ROOT=root
    fields=['archivedAfterPayerQUuid','archivedAfterYearsQUuid','archivedAfterExtendWhoQUuid',
            'archivedAfterExtendBasisQUuid','archivedAfterFormatsQUuid','archivedAfterMediaQUuid']
    base=plain();paths=[next(k for k in base if k.endswith(IDS[f])) for f in fields]
    try:
        for mask in range(64):
            values=copy.deepcopy(base)
            for i,k in enumerate(paths):
                if mask & (1<<i):values.pop(k)
            soup=BeautifulSoup(adapter.render_question('src/questions/11-data-preservation.html.j2',values),'html.parser')
            archive=soup.select_one('.post-project-archive')
            expected=[list(pair) for i,pair in enumerate(PAIRS) if mask & (3<<(2*i))==3<<(2*i)]
            yield 'mask-'+str(mask),'<html><body><div id="q-data-preservation">'+str(archive)+'</div></body></html>',expected
    finally:adapter.ROOT=previous


def cases(root):
    matrix=list(rows(root));result=[matrix[i] for i in [0,1,3,4,12,16,48,63]]
    original=matrix[3][1]
    def changed(name,edit):
        s=BeautifulSoup(original,'html.parser');edit(s);result.append((name,str(s),[]))
    changed('wrong-question',lambda s:s.select_one('#q-data-preservation').__setitem__('id','other'))
    changed('wrong-scope',lambda s:s.select_one('.post-project-archive').__setitem__('data-scope','dataset'))
    changed('unknown-fact',lambda s:s.select_one('.data-gap').__setitem__('data-fact-id','future-field'))
    changed('negative-state',lambda s:s.select_one('.data-gap').__setitem__('data-status','explicit-no'))
    changed('review-state',lambda s:s.select_one('.data-gap').__setitem__('data-status','needs-review'))
    changed('nested-author-content',lambda s:s.select_one('.data-gap').append(BeautifulSoup('<em>Original.csv</em>','html.parser')))
    changed('extra-child',lambda s:s.select_one('.reading-gap').append(s.new_tag('p')))
    changed('intervening-answer',lambda s:s.select_one('.reading-gap').insert_after(BeautifulSoup('<p>Already answered.</p>','html.parser')))
    changed('intervening-authored',lambda s:s.select_one('.reading-gap').insert_after(BeautifulSoup('<div class="answer-detail"><p>Keep Original.csv.</p></div>','html.parser')))
    changed('other-period-label',lambda s:s.select_one('.reading-gap').insert_after(BeautifulSoup('<div class="answer-lead"><p>Other arrangement:</p></div>','html.parser')))
    return result


RUNNER='''import json,sys
from weasyprint import HTML,__version__
p=json.load(sys.stdin);results=[]
keys=['font_size','line_height','padding_left','padding_right','border_left_width','border_right_width']
for name,source,pairs in p['cases']:
 for media in ['print','screen']:
  for near_end in [False,True] if pairs and media=='print' else [False]:
   snapshots=[]
   for css in [p['before'],p['after']]:
    prefix='<div style="height:198mm">Before.</div>' if near_end else ''
    doc=HTML(string=source.replace('<body>','<body><style>'+css+'</style>'+prefix),media_type=media).render()
    boxes={};texts=[]
    for number,page in enumerate(doc.pages,1):
     roots=[b for b in page._page_box.children if type(b).__name__=='BlockBox' and b.element.tag=='html'];assert len(roots)==1
     # Footer positions/page counts are generated, not authored body text.
     footer=[''.join(b.text for b in box.descendants() if type(b).__name__=='TextBox') for box in page._page_box.children if type(box).__name__=='MarginBox']
     assert [t for t in footer if t]==[str(number)+' / '+str(len(doc.pages))]
     texts.extend(b.text for b in roots[0].descendants() if type(b).__name__=='TextBox')
     for b in roots[0].descendants():
      if type(b).__name__=='BlockBox' and b.element.tag=='p' and b.element.get('data-fact-id'):
       key=b.element.get('data-fact-id');assert key not in boxes,(name,'split paragraph',key)
       boxes[key]=(number,b)
    snapshots.append((boxes,texts,doc))
   old,new=snapshots;assert old[1]==new[1],(name,media,'text or wrapping changed')
   assert old[0].keys()==new[0].keys()
   eligible=pairs if media=='print' else []
   selected={fact for pair in eligible for fact in pair}
   for fact,(page,b) in new[0].items():
    a=old[0][fact][1]
    assert [str(a.style[k]) for k in keys]==[str(b.style[k]) for k in keys],(name,fact,'type or side padding changed')
    if fact not in selected:
     assert [a.style[k] for k in ['padding_top','padding_bottom','border_top_width','border_bottom_width']]==[b.style[k] for k in ['padding_top','padding_bottom','border_top_width','border_bottom_width']]
   heights=[]
   for first,last in eligible:
    i,a=new[0][first];j,b=new[0][last];assert i==j,(name,'pair split')
    assert a.style['border_top_width']==1 and a.style['border_bottom_width']==0
    assert b.style['border_top_width']==0 and b.style['border_bottom_width']==1
    assert abs(a.border_box_y()+a.border_height()-b.border_box_y())<.01,(name,'pair not contiguous')
    height=b.border_box_y()+b.border_height()-a.border_box_y();assert height<200,(name,'pair no longer bounded')
    heights.append(height)
   if not eligible:
    assert [(f,i,b.position_x,b.position_y,b.width,b.height) for f,(i,b) in old[0].items()]==[(f,i,b.position_x,b.position_y,b.width,b.height) for f,(i,b) in new[0].items()],(name,'control geometry changed')
   results.append({'case':name,'media':media,'near_page_end':near_end,'pairs':eligible,'pair_heights_px':heights,'passed':True})
print(json.dumps({'weasyprint':__version__,'rows':results}))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    css=prepared_css(a.source_dir);old,panel=split_css(css)
    legacy=(a.source_dir/'src/style.css').read_text()
    payload={'cases':cases(a.source_dir),'before':legacy+old,'after':legacy+css}
    result=subprocess.run(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(payload).encode(),capture_output=True)
    if result.returncode:
        target=a.output.with_suffix('.failure.json');assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'passed':False,'stderr':result.stderr.decode()},indent=2)+'\n')
        raise RuntimeError('Pinned engine failed: '+str(target))
    report=json.loads(result.stdout)
    digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report.update(passed=True,release_acceptance=False,worker_image=IMAGE,checker_sha256=digest(Path(__file__)),
                  css_sha256=digest(a.source_dir/'src/layout.css'),
                  limits=['Exactly three named adjacent pairs; no free-answer grouping','Native DSW export and Word acceptance are separate'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':len(report['rows'])}))


if __name__=='__main__':main()
