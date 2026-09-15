"""Q9 bounded-label regression in both pinned Pandoc AST and actual DOCX."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from probe_q8_word import ROOT, IMAGE, RUNNER, word_changes

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


def allowed_changes(before,after):
    if before==after:return 0
    if isinstance(before,dict) and isinstance(after,dict):
        if before.get('t')=='Plain' and after.get('t')=='Div':
            assert after['c']==[['',[],[['custom-style','Pilot List Lead']]],[{'t':'Para','c':before['c']}]]
            assert len(before['c'])==1 and before['c'][0]['t']=='Strong'
            return 1
        assert before.keys()==after.keys()
        return sum(allowed_changes(before[k],after[k]) for k in before)
    if isinstance(before,list) and isinstance(after,list):
        assert len(before)==len(after)
        return sum(allowed_changes(a,b) for a,b in zip(before,after))
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
    counts=word_changes(results[0]['paragraphs'],results[1]['paragraphs'])
    asts=[{b['c'][0][0]:b for b in r['ast']['blocks']} for r in results];rows=[]
    for name,_,expected in matrix:
        changed=allowed_changes(asts[0][name],asts[1][name]);assert changed==counts[name]==expected,(name,changed,counts[name],expected)
        rows.append({'case':name,'styled_labels':changed,'docx_styled_labels':counts[name],'passed':True})
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'passed':True,'release_acceptance':False,'rows':rows,'worker_image':IMAGE,'checker_sha256':sha(Path(__file__)),
            'lua_sha256':sha(source),'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'limits':['AST and DOCX paragraph XML, not Microsoft Word layout acceptance','No whole-question keep or authored-text rewriting']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'styled_labels':sum(r['styled_labels'] for r in rows)}))


if __name__=='__main__':main()
