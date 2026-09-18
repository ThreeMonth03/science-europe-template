"""Bounded Q15 PDF-entry hint: independent grammar and pinned layout checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from bs4 import BeautifulSoup
from short_resources_contract import ROOT, HELPER, OPENING, HINT, compare, eligible, units
from probe_budget_word import IMAGE
from probe_empty_pdf import prepared_css


def fragment(rows=2, language='en'):
    words = ['15. Resources?', 'Training.', 'Prepare.', 'Files.', 'Budget', 'Funding', 'Resource', 'Purpose.', 'FAIR.', 'Funds.']
    if language != 'en': words = ['15. 資源？', '培訓。', '準備。', '資料。', '預算', '經費', '資源', '用途。', '管理。', '經費。']
    q,training,one,two,budget,funding,name,purpose,fair,funds = words
    row = lambda i: '<tr data-item-id="aa.'+str(i)+'"><td><p><strong>'+name+str(i)+'</strong></p><div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>'+purpose+'</p></div><p>'+fair+'</p></td><td><p>0 TWD</p></td><td><div class="answer-detail"><p>'+funds+'</p></div></td></tr>'
    return ('<section>'+OPENING+'<h3>'+q+'</h3><div class="answer"><div class="answer-lead"><p data-requirement-id="SE-6b" data-fact-id="specialist-expertise" data-status="complete">'+training+'</p></div>'
        '<div class="answer-detail" data-fact-id="specialist-expertise-detail" data-status="complete"><p>Training details.</p><ul><li>'+one+'</li><li>'+two+'</li></ul></div>'
        '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="explicit-no">No equipment.</p><p>Charges.</p><h4>'+budget+'</h4><div class="project-resources" data-item-id="aa">'
        '<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead><tr><th scope="col">'+name+'</th><th scope="col">'+budget+'</th><th scope="col">'+funding+'</th></tr></thead><tbody>'
        +''.join(row(i) for i in range(rows))+'</tbody></table></div></div></div></section>')


def cases():
    base = fragment(); rows = [('english',base,True), ('chinese',fragment(language='zh'),True)]
    for n in (0,1,3,8): rows.append(('rows-'+str(n),fragment(rows=n),n==1))
    def change(name,old,new,expected=False): rows.append((name,base.replace(old,new),expected))
    for name,old,new in [
        ('unknown-status','data-status="complete"','data-status="unknown"'),
        ('missing-fact','data-status="complete"','data-status="missing"'),
        ('missing-class','<p>Charges.</p>','<p class="data-gap">Missing.</p>'),
        ('unknown-div','class="answer-lead"','class="unknown"'),
        ('author-style','<p>Purpose.</p>','<p style="height:1000px">Purpose.</p>'),
        ('link','Purpose.','<a href="https://example.org">Original</a>'),
        ('image','Purpose.','<img src="not-fetched.png" alt="Original">'),
        ('break','Purpose.','First<br>Second'),
        ('nested-table','Purpose.','<table><tr><td>Original</td></tr></table>'),
        ('nested-list','<li>Prepare.</li>','<li>Prepare.<ul><li>Nested.</li></ul></li>'),
        ('extra-list-item','</ul>','<li>Extra.</li></ul>'),
        ('extra-paragraph','Purpose.','Purpose.</p><p>Extra.'),
        ('after-budget','</table>','</table><p>More facts.</p>'),
        ('unknown-attribute','data-item-id="aa"','data-item-id="aa" data-extra="yes"'),
        ('bad-id','data-item-id="aa"','data-item-id="not-an-item"'),
        ('unbalanced-div','</table>','</table></div>'),
        ('unknown-void','Purpose.','<hr>Purpose.'),
        ('comment','Purpose.','<!-- comment -->Purpose.'),
        ('empty-paragraph','Purpose.',''),
        ('extra-col','</colgroup>','<col class="resource-funding"></colgroup>'),
        ('extra-cell','</tr></tbody>','<td><p>0</p></td></tr></tbody>'),
        ('wrong-question','q-required-resources','q-other'),
        ('unknown-root-class','class="question"','class="question unknown"')]:
        change(name,old,new)
    change('inline','Purpose.','<strong>Original.</strong> <em>Text.</em> <code>0.csv</code>',True)
    change('authored-warning','Purpose.','Information not provided: keep Original.csv.',True)
    change('chinese-authored-warning','Purpose.','尚待補充：保留 Original.csv。',True)
    for field,old,limit in [('paragraph','Purpose.',160),('funding','Funds.',80),('amount','0 TWD',40),('list','Prepare.',80),('heading','15. Resources?',360)]:
        for n in (limit,limit+1): change(field+'-'+str(n),old,'x'*n,n==limit)
        change(field+'-cjk-boundary',old,'中'*(limit//2),True)
        change(field+'-cjk-over',old,'中'*(limit//2+1))
    rows.append(('duplicate-question',base+base,False))
    rows.append(('authored-lookalike',base.replace('Purpose.',base),False))
    rows.append(('two-projects',base.replace('</table></div>','</table></div><div class="project-resources" data-item-id="bb">'+base.split('<table',1)[1].split('</table>',1)[0].join(['<table','</table>'])+'</div>',1),False))
    # A worst-case short unit, with independent whole-question boundary math.
    large = base.replace('Purpose.','p'*150).replace('FAIR.','f'*100).replace('Funds.','u'*80).replace('0 TWD','0'*40)
    large = large.replace('Training.','t'*150).replace('No equipment.','e'*150).replace('Charges.','c'*30)
    current = units(BeautifulSoup(large,'html.parser').find(id='q-required-resources').get_text())
    needed = 1200-current+len('Training details.'); assert 0 < needed <= 160
    for n in (needed,needed+1):
        source = large.replace('Training details.','v'*n)
        rows.append(('whole-'+str(1200+n-needed),source,n==needed))
    return rows


RUNNER = '''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin);rows=[]
for name,before,after,selected in p['cases']:
 for media in ['print','screen']:
  pair=[]
  for source in [before,after]:
   doc=HTML(string='<style>'+p['css']+'</style><div style="height:210mm">Prefix.</div>'+source,media_type=media).render()
   boxes=[(i,b) for i,page in enumerate(doc.pages,1) for b in page._page_box.descendants()]
   text=[b.text for i,b in boxes if type(b).__name__=='TextBox']
   geometry=[(i,round(b.position_x,4),round(b.position_y,4),round(b.width,4),round(b.height,4),b.text) for i,b in boxes if type(b).__name__=='TextBox']
   regions=[(i,b.height) for i,b in boxes if type(b).__name__=='BlockBox' and b.element.get('id')=='q-required-resources']
   pair.append((doc,text,geometry,regions))
  a,b=pair
  assert ''.join(a[1])==''.join(b[1]),(name,media,'Text changed')
  assert len(b[0].pages)<=len(a[0].pages),(name,media,'Page count grew')
  if selected:
   assert len(b[3])==1 and b[3][0][1]<650,(name,media,'Unit does not fit',b[3])
  else:assert a[2:]==b[2:],(name,media,'Fallback changed')
  rows.append(dict(case=name,media=media,selected=selected,prior_pages=len(a[0].pages),pages=len(b[0].pages),regions=b[3]))
print(json.dumps(dict(weasyprint=__version__,rows=rows)))
'''


def check(root):
    rows = []
    for escaped in (False,True):
        helper = Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=escaped).get_template(HELPER).module
        for name,source,selected in cases():
            actual = str(helper.document(Markup(source) if escaped else source))
            if name not in ('wrong-question','unknown-root-class','duplicate-question','authored-lookalike','unbalanced-div'):
                try: compare(source,actual,selected)
                except AssertionError as error: raise AssertionError((name,escaped,str(error))) from error
            else: assert actual == source
            rows.append(dict(case=name,autoescape=escaped,selected=selected,before=source,after=actual))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',action='store_true');a=p.parse_args();assert not a.output.exists()
    report=dict(passed=False,release_acceptance=False,rows=[],checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256((a.source_dir/HELPER).read_bytes()).hexdigest())
    try:
        rows=check(a.source_dir)
        if a.engine:
            payload=dict(css=prepared_css(a.source_dir),cases=[(r['case'],r['before'],r['after'],r['selected']) for r in rows if not r['autoescape']])
            result=subprocess.run(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(payload).encode(),capture_output=True)
            report['engine_stderr']=result.stderr.decode(); assert result.returncode==0,report['engine_stderr']
            report['engine']=json.loads(result.stdout)
        report['rows']=[{k:v for k,v in row.items() if k not in ('before','after')} for row in rows]
        report['passed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=len(rows))))


if __name__=='__main__':main()
