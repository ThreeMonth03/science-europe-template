"""Pinned Pandoc: only trusted empty-section Heading2 spacing may change."""
import argparse, json, re, subprocess
from pathlib import Path

IMAGE='datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'
GROUPS=[['q-how-data','q-what-data'],['q-docs-metadata','q-quality-control'],
    ['q-store-backup','q-access-security'],['q-personal-data','q-copyright-ipr','q-ethical-issues'],
    ['q-share-restrictions','q-data-preservation','q-access-data','q-persistent-identifier'],
    ['q-dm-responsible','q-required-resources']]
IDS=['sec-data-collection','sec-docs-metadata','sec-storage-backup','sec-ethics-legal','sec-sharing-preservation','sec-responsibilities-resources']

def cases(source):
    questions={}
    for path in (source/'src/questions').glob('*.j2'):
        text=path.read_text(); root=re.search(r'<div id="([^"]+)" class="question"([^>]*)>',text)
        title=re.search(r'<h3>(.*?)</h3>',text,re.S)[1]
        questions[root[1]]='<div id="'+root[1]+'" class="question compact-empty-question"'+root[2]+'><h3>'+title+'</h3><div class="answer"></div></div>'
    titles=re.findall(r'<h2>(.*?)</h2>',(source/'src/content.html.j2').read_text(),re.S)
    assert len(titles)==6
    sections=['<section id="'+id+'" class="dmp-section"><h2>'+titles[i]+'</h2>'+''.join(questions[q] for q in GROUPS[i])+'</section>' for i,id in enumerate(IDS)]
    def wrap(parts):return '<div id="dmp-content">'+''.join(parts)+'</div>'
    base=wrap(sections); rows=[('all-empty',base,6),('review',base.replace(' compact-empty-question',''),0)]
    for i,group in enumerate(GROUPS):
        for j,q in enumerate(group):
            original=questions[q]; changed=original.replace('<div class="answer">','<div class="answer"><p>0 &amp; original。</p>')
            rows.append((f'nonempty-{q}',base.replace(original,changed),5))
        original=sections[i]
        changes={
            'section-wrong-element':original.replace('<section ','<div ').replace('</section>','</div>'),
            'section-class':original.replace('class="dmp-section"','class="dmp-section unexpected"'),
            'section-attribute':original.replace('class="dmp-section"','class="dmp-section" data-extra="1"'),
            'section-extra-child':original.replace('</section>','<p>Original.</p></section>'),
            'section-rich-heading':original.replace('<h2>','<h2><em>').replace('</h2>','</em></h2>'),
            'section-wrong-level':original.replace('h2>','h1>'),
            'question-extra-class':original.replace('compact-empty-question','compact-empty-question unexpected',1),
            'question-rich-heading':original.replace('<h3>','<h3><strong>',1).replace('</h3>','</strong></h3>',1),
            'question-unmarked':original.replace(' compact-empty-question','',1),
            'question-wrong-id':original.replace(group[0],'unknown-question',1),
            'question-attribute':original.replace('class="question compact-empty-question"','class="question compact-empty-question" data-other="1"',1),
            # The shared Jinja classifier does not mark authored empty <p>.
            # Pandoc discards that paragraph, so do not fabricate a trusted marker.
            'empty-authored-paragraph':original.replace(' compact-empty-question','',1).replace('<div class="answer">','<div class="answer"><p></p>',1),
            'empty-authored-container':original.replace('<div class="answer">','<div class="answer"><div class="answer-detail"></div>',1),
            'authored-table':original.replace('<div class="answer">','<div class="answer"><table><tr><td>Original</td></tr></table>',1),
            'question-reordered':original.replace(questions[group[0]]+questions[group[1]],questions[group[1]]+questions[group[0]],1)
        }
        for name,changed in changes.items():rows.append((f'{i+1}-{name}',base.replace(original,changed),5))
    rows.extend([
        ('wrong-root-id',base.replace('id="dmp-content"','id="other"'),0),
        ('root-class',base.replace('id="dmp-content"','id="dmp-content" class="other"'),0),
        ('root-attribute',base.replace('id="dmp-content"','id="dmp-content" data-other="1"'),0),
        ('root-leading-prose',base.replace('<div id="dmp-content">','<div id="dmp-content"><p>Original prefix.</p>'),0),
        ('root-missing-section',wrap(sections[:-1]),0),
        ('root-extra-section',wrap(sections+[sections[-1]]),0),
        ('root-reordered',wrap([sections[1],sections[0],*sections[2:]]),0),
        ('root-wrong-section-id',base.replace(IDS[0],'unknown-section',1),0),
        ('standalone-section',sections[0],0),
    ])
    for cls in ['answer','answer-detail','abstract']:rows.append(('authored-'+cls,'<div class="'+cls+'">'+base+'</div>',0))
    q5=questions['q-store-backup']
    skeleton='<div class="workspace-policy dataset-policy"><div class="reading-gap"></div><div class="reading-gap"></div></div>'
    rows.append(('q5-known-empty-skeleton',base.replace(q5,q5.replace('<div class="answer">','<div class="answer">'+skeleton)),6))
    rows.append(('q5-unknown-empty-skeleton',base.replace(q5,q5.replace('<div class="answer">','<div class="answer">'+skeleton.replace('reading-gap','other-gap'))),5))
    return rows

RUNNER=r'''
import json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,UndefinedError
from xml.etree import ElementTree as ET
p=json.load(sys.stdin); roots=[Path('/old'),Path('/new')]
envs=[Environment(loader=FileSystemLoader(r),extensions=['jinja2.ext.do'],autoescape=True) for r in roots]
templates=[e.get_template('src/word/question-spacing.xml') for e in envs]
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}; w='{'+ns['w']+'}'
def command(root):
 return ['pandoc','-f','html',*[f'--lua-filter={root}/src/word/{n}.lua' for n in ['pilot','preservation-reading','short-tables','question-spacing']]]
def strip_sections(value):
 if isinstance(value,list):return [strip_sections(v) for v in value if not (isinstance(v,dict) and v.get('t')=='RawBlock' and v['c'][0]=='openxml' and 'DSW:SE:empty-section:' in v['c'][1])]
 if isinstance(value,dict):return {k:strip_sections(v) for k,v in value.items()}
 return value
def count(value):
 if isinstance(value,dict):
  if value.get('t')=='RawBlock' and value['c']==['openxml','<!--DSW:SE:empty-section:v1:begin-->']:return 1
  return sum(count(v) for v in value.values())
 if isinstance(value,list):return sum(count(v) for v in value)
 return 0
rows=[]
with tempfile.TemporaryDirectory() as tmp:
 for case,html,expected in p['cases']:
  ast=[json.loads(subprocess.check_output(command(r)+['-t','json'],input=html.encode())) for r in roots]
  assert strip_sections(ast[1])==ast[0],(case,'AST changed beyond section markers')
  assert count(ast[1])==expected,(case,'eligibility',count(ast[1]),expected)
  files=[]
  for i,r in enumerate(roots):
   path=Path(tmp)/f'{i}.docx'
   subprocess.run(command(r)+['-t','docx','--reference-doc='+str(r/'src/word/reference.docx'),'-o',str(path)],input=html.encode(),check=True,capture_output=True)
   files.append(path)
  with zipfile.ZipFile(files[0]) as a,zipfile.ZipFile(files[1]) as b:
   assert set(a.namelist())==set(b.namelist())
   for name in a.namelist():
    if name not in ['word/document.xml','docProps/core.xml']:assert a.read(name)==b.read(name),(case,name)
   original=templates[0].render(content=a.read('word/document.xml').decode())
   marked=b.read('word/document.xml').decode(); current=templates[1].render(content=marked)
  x,y=[ET.fromstring(s.encode()) for s in [original,current]]
  changed=[]
  for props in y.findall('.//w:pPr',ns):
   style=props.find('w:pStyle',ns); spacing=props.find('w:spacing',ns)
   if style is not None and style.get(w+'val')=='Heading2' and spacing is not None:
    assert spacing.attrib=={w+'before':'120',w+'after':'60'}
    assert props.find('w:keepNext',ns) is None
    changed.append(props);props.remove(spacing)
  assert len(changed)==expected,(case,'Word property count',len(changed),expected)
  assert ET.tostring(x)==ET.tostring(y),(case,'Unexpected XML content or property edit')
  assert '<!--DSW:SE:empty-section:' not in current and '<!--DSW:SE:empty-question:' not in current
  if not expected:assert original==current,(case,'Unmarked document changed')
  if case=='all-empty':
   for mutate in [marked.replace('w:val="Heading2"','w:val="Heading1"'),marked.replace('empty-section:v1:end','empty-section:v2:end')]:
    try:templates[1].render(content=mutate)
    except UndefinedError:pass
    else:raise AssertionError('Malformed marker accepted')
   html_output=[subprocess.check_output(command(r)+['-t','html'],input=html.encode()) for r in roots]
   assert html_output[0]==html_output[1],'Non-Word output changed'
  rows.append(dict(case=case,section_headings_changed=expected,passed=True))
print(json.dumps(dict(passed=True,rows=rows,pandoc=subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0])))
'''

def run(before,after,output):
    assert not output.exists()
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000','-e','XDG_CACHE_HOME=/tmp/private-cache',
        '-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages','-i','--entrypoint','python',
        '-v',str(before.resolve())+':/old:ro','-v',str(after.resolve())+':/new:ro',IMAGE,'-c',RUNNER]
    result=subprocess.run(command,input=json.dumps(dict(cases=cases(before))).encode(),capture_output=True)
    if result.returncode:
        output.with_suffix('.failure.log').write_bytes(result.stderr)
        raise RuntimeError('Pandoc scope check failed; inspect retained failure log')
    report=json.loads(result.stdout);report.update(image=IMAGE,release_acceptance=False)
    output.write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=run(args.before,args.after,args.output)
    print(json.dumps(dict(passed=True,cases=len(result['rows']))))
