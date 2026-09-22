"""Pinned Pandoc checks for empty-heading markers and exact XML property edits."""
import argparse
import json
from pathlib import Path
import re
import subprocess

IMAGE = 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
RUNNER = r'''
import copy,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,UndefinedError
from xml.etree import ElementTree as etree
p=json.load(sys.stdin); root=Path('/template')
# Match the worker's autoescaped render path, including captured-include Markup.
env=Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=True)
old_xml=env.get_template('src/word/short-tables.xml'); new_xml=env.get_template('src/word/question-spacing.xml')
base=['pandoc','-f','html','--lua-filter='+str(root/'src/word/pilot.lua'),'--lua-filter='+str(root/'src/word/preservation-reading.lua'),'--lua-filter='+str(root/'src/word/short-tables.lua')]
extra='--lua-filter='+str(root/'src/word/question-spacing.lua')
rows=[]
with tempfile.TemporaryDirectory() as tmp:
 for case,html,eligible in p['cases']:
  before=json.loads(subprocess.check_output(base+['-t','json'],input=html.encode()))
  after=json.loads(subprocess.check_output(base+[extra,'-t','json'],input=html.encode()))
  def strip(value):
   if isinstance(value,list):return [strip(v) for v in value if not (isinstance(v,dict) and v.get('t')=='RawBlock' and v['c'][0]=='openxml' and 'DSW:SE:empty-question:' in v['c'][1])]
   if isinstance(value,dict):return {k:strip(v) for k,v in value.items()}
   return value
  assert strip(after)==before,(case,'AST changed beyond generated markers')
  def count_markers(value):
   if isinstance(value,dict):
    if value.get('t')=='RawBlock' and value['c']==['openxml','<!--DSW:SE:empty-question:v1:begin-->']:return 1
    return sum(count_markers(v) for v in value.values())
   if isinstance(value,list):return sum(count_markers(v) for v in value)
   return 0
  markers=count_markers(after)
  assert markers==int(eligible),(case,'marker eligibility',markers)
  for variant,args in [('old',[]),('new',[extra])]:
   target=Path(tmp)/(variant+'.docx')
   subprocess.run(base+args+['-t','docx','--reference-doc='+str(root/'src/word/reference.docx'),'-o',str(target)],input=html.encode(),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  with zipfile.ZipFile(Path(tmp)/'old.docx') as a,zipfile.ZipFile(Path(tmp)/'new.docx') as b:
   original=old_xml.render(content=a.read('word/document.xml').decode())
   marked=b.read('word/document.xml').decode(); current=new_xml.render(content=marked)
  x,y=[etree.fromstring(v.encode()) for v in [original,current]]
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
  changed=[n for n in y.findall('.//w:pPr',ns) if n.find('w:pStyle',ns) is not None and n.find('w:pStyle',ns).get('{'+ns['w']+'}val')=='Heading3' and n.find('w:keepNext',ns) is not None and n.find('w:keepNext',ns).get('{'+ns['w']+'}val')=='0']
  assert len(changed)==int(eligible),(case,'XML properties',len(changed))
  for props in changed:
   keep=props.find('w:keepNext',ns);spacing=props.find('w:spacing',ns)
   assert spacing.attrib=={'{'+ns['w']+'}before':'80','{'+ns['w']+'}after':'0'}
   props.remove(keep);props.remove(spacing)
  assert etree.tostring(x)==etree.tostring(y),(case,'Unexpected XML or authored text edit')
  assert '<!--DSW:SE:empty-question:' not in current
  if eligible:
   for mutation in [marked.replace('w:val="Heading3"','w:val="Heading2"'), marked.replace('empty-question:v1:end','empty-question:v2:end')]:
    try:new_xml.render(content=mutation)
    except UndefinedError:pass
    else:raise AssertionError('Malformed serialization accepted')
  else:assert old_xml.render(content=marked)==current
  rows.append(dict(case=case,eligible=eligible,passed=True))
print(json.dumps(dict(passed=True,rows=rows,pandoc=subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0])))
'''


def cases(source):
    result = []
    for file in sorted((source / 'src/questions').glob('*.j2')):
        text = file.read_text()
        root = re.search(r'<div id="([^"]+)" class="question"([^>]*)>', text)
        title = re.search(r'<h3>(.*?)</h3>', text, re.S)[1]
        html = '<div id="' + root[1] + '" class="question compact-empty-question"' + root[2] + '><h3>' + title + '</h3><div class="answer"></div></div>'
        result.append((root[1], html, True))
    base = next(h for name,h,_ in result if name == 'q-quality-control')
    result.extend([
        ('review-unmarked',base.replace(' compact-empty-question',''),False),
        ('wrong-requirement',base.replace('SE-2b','SE-1a'),False),
        ('wrong-id',base.replace('q-quality-control','q-other'),False),
        ('wrong-heading',base.replace('h3','h4'),False),
        ('additional-class',base.replace('compact-empty-question','compact-empty-question unexpected'),False),
        ('zero',base.replace('<div class="answer">','<div class="answer"><p>0</p>'),False),
        ('empty-authored',base.replace('<div class="answer">','<div class="answer"><div class="answer-detail"></div>'),False),
        ('authored-lookalike','<div class="answer-detail">'+base+'</div>',False),
        ('raw-text-lookalike',base.replace('<div class="answer">','<div class="answer"><p>&lt;!--DSW:SE:empty-question:v1:begin--&gt;</p>'),False),
    ])
    q5 = next(h for name,h,_ in result if name == 'q-store-backup')
    result.append(('q5-empty-skeleton',q5.replace('<div class="answer">','<div class="answer"><div class="workspace-policy dataset-policy"><div class="reading-gap"></div><div class="reading-gap"></div></div>'),True))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000','-e','XDG_CACHE_HOME=/tmp/private-cache','-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages','-i','--entrypoint','python','-v',str(a.source_dir.resolve())+':/template:ro',IMAGE,'-c',RUNNER]
    completed=subprocess.run(command,input=json.dumps({'cases':cases(a.source_dir)}).encode(),capture_output=True)
    if completed.returncode:
        a.output.with_suffix('.failure.log').write_bytes(completed.stderr)
        raise RuntimeError('Pinned engine failed; retained failure log')
    result=json.loads(completed.stdout);result['image']=IMAGE
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=len(result['rows']))))


if __name__=='__main__':main()
