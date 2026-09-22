"""Independent parsed-tree scope oracle and unchanged Jinja output checks."""
import copy,importlib.util,itertools,json
from pathlib import Path
import sys
from bs4 import BeautifulSoup,Tag

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'scripts'),str(ROOT/'tests')]
_spec=importlib.util.spec_from_file_location('empty_sections_recipe',HERE/'recipe.py')
recipe=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(recipe)
from output_profile_contract import environment,WRAPPER

def expected(page):
    selected=[]
    for section in page.select('html > body #dmp-content > section.dmp-section'):
        count=recipe.COUNTS.get(section.get('id'))
        if count is None:continue
        children=[c for c in section.children if isinstance(c,Tag)]
        if len(children)!=count+1 or children[0].name!='h2':continue
        if all(c.name=='div' and {'question','compact-empty-question'}<=set(c.get('class',[])) for c in children[1:]):
            selected.append(section['id'])
    return selected

def document(section='sec-data-collection', filled=(), extra=''):
    count=recipe.COUNTS.get(section,2)
    body='<h2>Section heading</h2>'
    for i in range(count):
        classes='question'+('' if i in filled else ' compact-empty-question')
        body+='<div class="'+classes+'"><h3>'+str(i+1)+'. Original question?</h3><div class="answer">'
        body+='<p>Original answer 0; retain punctuation。</p>' if i in filled else ''
        body+='</div></div>'
    return '<html><body><div id="dmp-content"><section class="dmp-section" id="'+section+'">'+body+extra+'</section></div></body></html>'

def cases():
    rows=[]
    for section,count in recipe.COUNTS.items():
        for choices in itertools.product([False,True],repeat=count):
            filled=[i for i,value in enumerate(choices) if value]
            rows.append((section+'-'+''.join(map(lambda v:str(int(v)),choices)),document(section,filled)))
    base=document()
    def changed(name,edit):
        soup=BeautifulSoup(base,'html.parser');edit(soup);rows.append((name,str(soup)))
    changed('unknown-section',lambda s:s.section.__setitem__('id','sec-authored'))
    changed('wrong-parent',lambda s:s.select_one('#dmp-content').__setitem__('id','authored'))
    changed('nested-owned-section',lambda s:s.section.wrap(s.new_tag('div')))
    changed('extra-heading',lambda s:s.section.append(s.new_tag('h2')))
    changed('missing-question',lambda s:s.select('.question')[-1].decompose())
    changed('extra-question',lambda s:s.section.append(copy.deepcopy(s.select('.question')[-1])))
    changed('wrong-heading-tag',lambda s:setattr(s.h2,'name','h3'))
    changed('wrong-section-tag',lambda s:setattr(s.section,'name','div'))
    changed('wrong-question-tag',lambda s:setattr(s.select_one('.question'),'name','section'))
    changed('heading-not-first',lambda s:s.section.append(s.h2.extract()))
    for tag in ['p','img','table','br','div']:
        changed('extra-authored-'+tag,lambda s,tag=tag:s.section.append(s.new_tag(tag)))
    for body in ['0','<p>0</p>','<p></p>','<img alt="">','<br>','<table><tr><td></td></tr></table>',
                 '<div class="question compact-empty-question"><h3>Authored heading</h3></div>']:
        def fill(s,body=body):
            q=s.select_one('.question');q['class']=['question']
            q.select_one('.answer').append(BeautifulSoup(body,'html.parser'))
        changed('authored-fallback-'+str(len(rows)),fill)
    # An unmarked inner question is not an owned direct sibling.
    mixed=BeautifulSoup(document(filled=(0,)),'html.parser')
    mixed.select_one('.answer').append(BeautifulSoup(document(),'html.parser').section)
    rows.append(('nested-authored-markers',str(mixed)))
    return rows

def check(root,before,after):
    recipe.project_prepared(before,after)
    overrides=lambda values:{n:v.decode() if isinstance(v,bytes) else v for n,v in values.items() if n.endswith('.j2')}
    rows=[]
    fixtures=[('EMPTY',{})]
    for path in sorted((root/'fixtures/pilot/en').glob('*.events.json')):
        values={e['path']:({'value':{'value':e['value']['value']}} if e['value']['type']=='IntegrationReply' else e['value']['value']) for e in json.loads(path.read_text())}
        fixtures.append((path.name,values))
    for escape,profile in itertools.product([False,True],['review','submission','unknown']):
        old,new=[environment(root,escape,overrides(v)).from_string(WRAPPER) for v in [before,after]]
        for name,values in fixtures:
            args=dict(repliesMap=values,output_profile=profile,dc={'project':{'created_by':None},'e':{'choices':{}}})
            a,b=old.render(**args),new.render(**args);assert a==b,'Jinja output changed'
            page=BeautifulSoup('<html><body>'+b+'</body></html>','html.parser')
            selected=expected(page)
            if profile!='submission':assert not selected
            if name=='EMPTY' and profile=='submission':assert len(selected)==6
            rows.append(dict(case=name,profile=profile,autoescape=escape,eligible_sections=selected,passed=True))
    return rows
