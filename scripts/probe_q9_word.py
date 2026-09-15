"""Q9 bounded-label regression in both pinned Pandoc AST and actual DOCX."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from probe_q8_word import ROOT, IMAGE, RUNNER
from lxml import etree
from q9_word_contract import expected_blocks,xml,text,style,separator

HANDLER = '  if div.identifier == "q-ethical-issues" then return keep_q9_dataset_labels(div) end'


def fixture(label='Original-v1.2.csv', flags=('No personal data.', 'No sensitive data.'), count=1, qid='q-ethical-issues'):
    return '<div id="'+qid+'"><h3>9. Ethics?</h3><div class="answer"><p>Produced data:</p><ul>'+''.join(
        '<li><strong>'+label+'</strong><ul class="ethical-data-flags">'+''.join('<li>'+f+'</li>' for f in flags)+'</ul></li>'
        for _ in range(count))+'</ul></div></div>'


def cases():
    base=fixture()
    return [
        ('two-flags',base,1),('one-flag',fixture(flags=('One flag.',)),1),
        ('chinese',fixture(label='沿岸水溫觀測資料',flags=('不包含個人資料。','不包含敏感資料。')),1),
        ('eight',fixture(count=8),8),('thirty-two',fixture(count=32),32),
        ('name-boundary',fixture(label='x'*80),1),('cjk-boundary',fixture(label='中'*40),1),
        ('flag-boundary',fixture(flags=('x'*160,'y'*160)),1),
        ('long-name',fixture(label='x'*81),0),('wide-name',fixture(label='中'*41),0),
        ('long-flag',fixture(flags=('x'*161,)),0),('three-flags',fixture(flags=('A.','B.','C.')),0),
        ('thirty-three',fixture(count=33),0),('empty-name',fixture(label=''),0),
        ('empty-flags',fixture(flags=()),0),('empty-flag',fixture(flags=('',)),0),
        ('name-link',fixture(label='<a href="https://example.org">Name</a>'),0),
        ('name-span',fixture(label='<span data-author="original">Name</span>'),0),
        ('name-break',fixture(label='First<br>Second'),0),
        ('flag-link',fixture(flags=('<a href="https://example.org">Original</a>',)),0),
        ('flag-prose',fixture(flags=('<p>First.</p><p>Second.</p>',)),0),
        ('flag-table',fixture(flags=('<table><tr><td>Original.</td></tr></table>',)),0),
        ('flag-nested-list',fixture(flags=('First.<ul><li>Nested.</li></ul>',)),0),
        ('paragraph-name',base.replace('<strong>','<p><strong>').replace('</strong>','</strong></p>'),0),
        ('authored-list',base.replace('<div class="answer">','<div class="answer"><div class="answer-detail">').replace('</ul></div></div>','</ul></div></div></div>'),0),
        ('other-question',fixture(qid='q-copyright-ipr'),0),
        ('missing-flags',base.replace('<ul class="ethical-data-flags"><li>No personal data.</li><li>No sensitive data.</li></ul>','<span> — <em>Not provided.</em></span>'),0),
        ('mixed-missing',base.replace('</ul></div></div>','<li><strong>Unknown</strong><span> — <em>Not provided.</em></span></li></ul></div></div>'),1),
        ('mixed-empty-item',base.replace('</ul></div></div>','<li><strong>Unknown</strong><ul><li></li></ul></li></ul></div></div>'),0),
    ]


def inline_text(values):
    return ''.join(' ' if v['t'] in ['Space','SoftBreak'] else inline_text(v['c']) if v['t']=='Strong' else v['c'] for v in values)


def allowed_changes(before,after,plans=None):
    if before==after:return 0
    if isinstance(before,list) and isinstance(after,list) and len(before)==len(after)==2 and isinstance(before[0],dict) and before[0].get('t')=='Plain' and isinstance(after[0],dict) and after[0].get('t')=='Div':
        assert after[0]['c']==[['',[],[['custom-style','Pilot List Lead']]],[{'t':'Para','c':before[0]['c']}]]
        assert len(before[0]['c'])==1 and before[0]['c'][0]['t']=='Strong'
        assert before[1]['t']==after[1]['t']=='BulletList';flags=[]
        for entry in before[1]['c']:
            assert len(entry)==1;block=entry[0]
            if block['t']=='Div':
                assert block['c'][0]==['',[],[['custom-style','Pilot List Lead']]] and len(block['c'][1])==1
                block=block['c'][1][0]
            assert block['t'] in ['Plain','Para'];flags.append(block['c'])
        assert len(flags) in [1,2]
        gap=[{'t':'Space'}] if len(flags)==2 and separator(*[inline_text(f) for f in flags]) else []
        expected=before[1] if len(flags)==1 else {'t':'BulletList','c':[[{'t':'Plain','c':flags[0]+gap+flags[1]}]]}
        assert after[1]==expected
        if plans is not None:plans.append((inline_text(before[0]['c']),[inline_text(f) for f in flags]))
        return 1
    if isinstance(before,dict) and isinstance(after,dict):
        assert before.keys()==after.keys()
        return sum(allowed_changes(before[k],after[k],plans) for k in before)
    if isinstance(before,list) and isinstance(after,list):
        assert len(before)==len(after)
        return sum(allowed_changes(a,b,plans) for a,b in zip(before,after))
    raise AssertionError('Only a Q9 name style wrapper may change')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();source=ROOT/'src/word/pilot.lua';lua=source.read_text();assert lua.count(HANDLER)==1
    matrix=cases();html=''.join('<div id="'+n+'"><h2>CASE: '+n+'</h2>'+h+'</div>' for n,h,_ in matrix)
    results=[]
    for variant in [lua.replace(HANDLER,''),lua]:
        result=subprocess.check_output(['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c',RUNNER],
            input=json.dumps({'html':html,'lua':variant,'reference':base64.b64encode((ROOT/'src/word/reference.docx').read_bytes()).decode()}).encode())
        results.append(json.loads(result))
    def by_case(values):
        result={'__prefix__':[]};case='__prefix__'
        for value in values:
            node=etree.fromstring(value)
            if style(node)=='Heading2' and text(node).startswith('CASE: '):case=text(node)[6:];result[case]=[]
            result[case].append(node)
        return result
    words=[by_case(r['word_blocks']) for r in results]
    assert [xml(n) for n in words[0]['__prefix__']]==[xml(n) for n in words[1]['__prefix__']]
    asts=[{b['c'][0][0]:b for b in r['ast']['blocks']} for r in results];rows=[]
    for name,_,expected in matrix:
        plans=[];changed=allowed_changes(asts[0][name],asts[1][name],plans);assert changed==expected,(name,changed,expected)
        try:projected,counts=expected_blocks(words[0][name],plans)
        except AssertionError as e:raise AssertionError((name,'Unexpected baseline Word group',str(e))) from e
        assert [xml(n) for n in projected]==[xml(n) for n in words[1][name]],(name,'Unexpected Word XML change')
        assert counts['styled_labels']==expected
        rows.append({'case':name,'styled_labels':changed,'docx_styled_labels':counts['styled_labels'],'joined_flag_pairs':counts['joined_flag_pairs'],'passed':True})
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'passed':True,'release_acceptance':False,'rows':rows,'worker_image':IMAGE,'checker_sha256':sha(Path(__file__)),
            'lua_sha256':sha(source),'contract_sha256':sha(ROOT/'scripts/q9_word_contract.py'),'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'limits':['AST and DOCX paragraph XML, not Microsoft Word layout acceptance','No whole-question keep or authored-text rewriting']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'styled_labels':sum(r['styled_labels'] for r in rows)}))


if __name__=='__main__':main()
