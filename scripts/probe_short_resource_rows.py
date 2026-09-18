"""Bounded many-budget PDF rows: source-byte, independent grammar and engine checks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from bs4 import BeautifulSoup
from short_resource_rows_contract import ROOT, HELPER, eligible, project_hints
from probe_budget_word import IMAGE
from probe_empty_pdf import prepared_css

HEADER = '<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead><tr><th scope="col">Resource / 資源</th><th scope="col">Budget / 金額</th><th scope="col">Funding / 經費</th></tr></thead><tbody>'


def fixture(count=4, language='en', changes=None):
    rows = []
    for n in range(count):
        row = dict(id='1e85da40-bbfc-4180-903e-6c569ed2da38.'*5+str(n),
            title='<p><strong>Resource '+str(n)+'</strong></p>',
            purpose='<div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>Keep original files and the audit trail.</p></div><p>This resource supports management of data.</p>',
            budget='<p>0 TWD</p>', funding='<div class="answer-detail"><p>Institutional funds.</p></div>')
        if language != 'en':
            row.update(title='<p><strong>資源 '+str(n)+'</strong></p>',
                purpose='<div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>保留原始資料及查核紀錄。</p></div><p>支援項目：資料管理。</p>',
                funding='<div class="answer-detail"><p>機構經費。</p></div>')
        row.update(changes or {})
        row['original'] = '<tr data-item-id="'+row['id']+'"><td>'+row['title']+row['purpose']+'</td><td>'+row['budget']+'</td><td>'+row['funding']+'</td></tr>'
        rows.append(row)
    return HEADER+''.join(r['original'] for r in rows)+'</tbody></table>', rows


def cases():
    result = []
    def add(name, count=4, language='en', changes=None, selected=True):
        source, rows = fixture(count,language,changes)
        result.append((name,source,rows,list(range(count)) if selected and 4<=count<=32 else []))
    for n in [0,1,3,4,8,32,33]: add('rows-'+str(n),n)
    add('chinese',language='zh')
    add('inline',changes={'purpose':'<p><strong>Exact.</strong> <em>Original.</em> <code>0.csv</code></p>'})
    add('authored-warning',changes={'purpose':'<p>尚待補充：保留原文。 Information not provided: keep.</p>'})
    gap = lambda fact,text: '<p class="data-gap" data-requirement-id="SE-6b" data-fact-id="'+fact+'" data-status="missing"><strong>Information not provided:</strong> '+text+'</p>'
    add('missing-purpose',changes={'purpose':gap('resource-justification','purpose.')+gap('resource-allocation','FAIR activities.')})
    add('missing-budget',changes={'budget':gap('resource-amount','amount and currency.')})
    add('zero-missing-currency',changes={'budget':'<p data-fact-id="resource-amount-value" data-status="complete">0</p>'+gap('resource-amount','currency.')})
    add('missing-funding',changes={'funding':gap('cost-coverage','funding source.')})
    add('missing-grant',changes={'funding':'<p data-fact-id="cost-coverage" data-status="complete">Funded by a grant.</p><p class="data-gap" data-fact-id="grant-number" data-status="missing">Grant number missing.</p>'})
    for name,value in [
        ('link','<p><a href="https://example.org">Original</a></p>'),('image','<p><img src="not-fetched.png">Original</p>'),
        ('break','<p>Original<br>Text</p>'),('list','<ul><li>Original.</li></ul>'),
        ('nested-table','<table><tr><td>Original.</td></tr></table>'),('nested-inline','<p><strong><em>Original</em></strong></p>'),
        ('style','<p style="height:1000px">Original.</p>'),('unknown-status',gap('resource-justification','purpose.').replace('missing','unknown')),
        ('comment','<p><!-- comment -->Original.</p>'),('unclosed','<p>Original.'),('mismatched','<p>Original.</div>'),
        ('stray-text','Original.<p>Keep.</p>'),('empty','<p></p>'),('four-paragraphs','<p>Original.</p>'*4),
        ('long-purpose','<p>'+'Original text. '*150+'</p>')]: add(name,changes={'purpose':value},selected=False)
    for field,limit,token in [('title',80,40),('purpose',240,40),('budget',80,12),('funding',100,20)]:
        for over in [0,1]:
            # Alternating short words reaches the character limit without an unbreakable run.
            text=('a '*(limit//2))[:-1]+'b'+'c'*over
            add(field+'-units-'+str(limit+over),changes={field:'<p>'+text+'</p>'},selected=not over)
            add(field+'-cjk-'+str(limit+over*2),changes={field:'<p>'+'中'*(limit//2+over)+'</p>'},selected=not over)
            add(field+'-token-'+str(token+over),changes={field:'<p>'+'x'*(token+over)+'</p>'},selected=not over)
    for identity in ['', 'x'*257, 'bad"id', 'same-id']:
        add('id-'+str(len(identity)),changes={'id':identity},selected=False)
    source,rows=fixture(); rows[1]=copy.deepcopy(rows[0]); source=HEADER+''.join(r['original'] for r in rows)+'</tbody></table>'
    result.append(('duplicate-row',source,rows,[2,3]))
    source,rows=fixture(); other,long_rows=fixture(changes={'purpose':'<p>'+'Original text. '*150+'</p>'})
    source=source.replace(rows[1]['original'],long_rows[1]['original']);rows[1]=long_rows[1]
    result.append(('short-and-long',source,rows,[0,2,3]))
    return result


def check(root):
    results=[]
    for escaped in [False,True]:
        helper=Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=escaped).get_template(HELPER).module
        for name,source,rows,selected in cases():
            for i,row in enumerate(rows):
                if name.startswith('id-') or name=='duplicate-row': continue
                assert eligible(row)==(i in selected or len(rows) not in range(4,33)),(name,i,'Independent grammar disagrees')
            values=[{k:(Markup(v) if escaped and k!='id' else v) for k,v in r.items()} for r in rows]
            actual=str(helper.table(Markup(source) if escaped else source,values))
            expected=source
            for i in selected:
                start='<tr data-item-id="'+rows[i]['id']+'">'
                expected=expected.replace(start,start[:-1]+' class="pdf-short-resource-row" style="break-inside: avoid">',1)
            assert actual==expected,(name,escaped,'Unexpected source-byte change')
            assert project_hints(actual)==source,(name,'Projection differs')
            results.append(dict(case=name,autoescape=escaped,selected=[rows[i]['id'] for i in selected],before=source,after=actual))
    return results


RUNNER = r'''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin); rows=[]
for name,before,after,selected in p['cases']:
 for media in ['print','screen']:
  pair=[]
  for source in [before,after]:
   html=HTML(string='<style>'+p['css']+'</style><div style="height:170mm">Prefix.</div>'+source,media_type=media)
   parents={c:node for node in html.etree_element.iter() for c in node}
   doc=html.render()
   regions={};text={};geometry=[];overflow=[]
   for page_index,page in enumerate(doc.pages,1):
    for box in page._page_box.descendants():
     element=box.element
     if type(box).__name__=='TableRowBox' and element.get('data-item-id'):
      key=element.get('data-item-id');regions.setdefault(key,[]).append([page_index,round(box.height,4)])
      if box.position_y+box.height>page._page_box.content_box_y()+page._page_box.height+1:overflow.append(key)
     if type(box).__name__!='TextBox':continue
     geometry.append([page_index,round(box.position_x,4),round(box.position_y,4),round(box.width,4),round(box.height,4),box.text])
     ancestors=[element]
     while ancestors[-1] in parents:ancestors.append(parents[ancestors[-1]])
     row=next((e for e in ancestors if e.tag=='tr' and e.get('data-item-id')),None)
     if row is not None:
      cell=next(e for e in ancestors if e.tag=='td');key=row.get('data-item-id')+'|'+str(list(row).index(cell))
      text[key]=text.get(key,'')+box.text
   pair.append(dict(pages=len(doc.pages),text={k:re.sub(r'\s+','',v) for k,v in text.items()},geometry=geometry,regions=regions,overflow=overflow))
  a,b=pair
  assert a['text']==b['text'],(name,media,'Cell text changed')
  assert b['pages']<=a['pages'],(name,media,'Page count grew')
  for identity in selected:
   assert len(b['regions'][identity])==1 and b['regions'][identity][0][1]<400,(name,media,identity,b['regions'][identity])
   assert identity not in b['overflow'],(name,media,'Selected row overflow')
  if not selected:assert a==b,(name,media,'Fallback geometry changed')
  rows.append(dict(case=name,media=media,selected_count=len(selected),prior_pages=a['pages'],pages=b['pages'],
    split_before=sum(len(v)>1 for v in a['regions'].values()),split_after=sum(len(v)>1 for v in b['regions'].values()),regions=b['regions']))
assert any(r['split_before']>r['split_after'] for r in rows),'No actual split repaired in boundary fixtures'
print(json.dumps(dict(weasyprint=__version__,rows=rows)))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,default=ROOT)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',action='store_true');a=p.parse_args();assert not a.output.exists()
    rows=check(a.source_dir)
    report=dict(passed=True,release_acceptance=False,worker_image=IMAGE,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        contract_sha256=hashlib.sha256((ROOT/'scripts/short_resource_rows_contract.py').read_bytes()).hexdigest(),
        source_sha256={n:hashlib.sha256((a.source_dir/n).read_bytes()).hexdigest() for n in [HELPER,'src/budget-reading.html.j2','src/layout.css']},
        rows=[{k:v for k,v in r.items() if k not in ['before','after']} for r in rows],
        limits=['PDF-only; ordinary 4..32-row tables with no expanded long row','Unsupported rows retain prior pagination','Engine fixtures are not native DSW acceptance'])
    if a.engine:
        names=['rows-4','rows-8','chinese','missing-purpose','missing-budget','zero-missing-currency','missing-funding','missing-grant',
               'short-and-long','long-purpose','purpose-cjk-240','purpose-units-240','funding-token-21','break']
        payload=dict(css=prepared_css(a.source_dir),cases=[(r['case'],r['before'],r['after'],r['selected']) for r in rows if not r['autoescape'] and r['case'] in names])
        result=subprocess.run(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(payload).encode(),capture_output=True)
        assert result.returncode==0,result.stderr.decode()
        report['engine']=json.loads(result.stdout)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=len(rows),engine_cases=len(report.get('engine',{}).get('rows',[])))))


if __name__=='__main__':main()
