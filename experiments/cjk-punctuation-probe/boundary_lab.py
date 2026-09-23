"""Synthetic falsification lab: a naive CSS/Lua extension is NOT an integration.

Use actual prepared 0.3.50 assets; no source/package is edited. The mixed-boundary
control deliberately exposes a PDF/Word discrepancy in the naive extension.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_empty_pdf import prepared_css
from probe_q8_word import RUNNER as WORD_RUNNER
from probe_identifier_spacing import PDF_RUNNER, formatted_chars, NEW_JOIN

IMAGE = 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
CSS = '\nhtml[lang="zh-Hant"] body .metadata-policy.dataset-policy > p::after { content: none; }\n'
JOIN = NEW_JOIN.replace('div.classes:includes("identifier-arrangement")',
    '(div.classes:includes("identifier-arrangement") or div.classes:includes("metadata-policy"))')


def cases():
    dictionary = '本計畫將建立資料字典或變項定義表。'
    # last two booleans describe observed CSS/Word effects, not acceptance.
    for name,left,right,language,kind,pdf,word in [
        ('zh-owned', dictionary, '後設資料將公開提供。', 'zh-Hant', 'metadata-policy dataset-policy', True, True),
        ('zh-internal-latin', '資料溯源將以 W3C PROV 記錄。', dictionary, 'zh-Hant', 'metadata-policy dataset-policy', True, True),
        ('en-owned', 'We will create a data dictionary.', 'Metadata will be openly available.', 'en', 'metadata-policy dataset-policy', False, False),
        ('unrelated-policy', '原文。', '原文。', 'zh-Hant', 'dataset-policy', False, False),
        ('authored', '原文）。  Keep spaces; v1.25.', '第二段。 https://example.org/a?x=1&amp;y=2', 'zh-Hant', 'answer-detail', False, False),
        ('mixed-boundary', dictionary, 'W3C PROV is supported.', 'zh-Hant', 'metadata-policy dataset-policy', True, False),
    ]:
        source = '<html lang="'+language+'"><body><div class="'+kind+'"><p>'+left+'</p><p>'+right+'</p></div></body></html>'
        yield dict(name=name, html=source, left=left, right=right, pdf_effect=pdf, word_effect=word)


def word_delta(before, after, left, right, eligible):
    if not eligible:
        assert before == after, 'Unrelated Word AST, styling or text changed'
        return
    count = 0
    def projected(value):
        nonlocal count
        if isinstance(value,dict) and value.get('t') == 'Para':
            seq=value['c']
            if all(n['t'] in ['Str','Space'] for n in seq):
                text=''.join(n['c'] if n['t']=='Str' else ' ' for n in seq)
                if text == left+' '+right:
                    prefix=0
                    for i,n in enumerate(seq):
                        if prefix==len(left):
                            assert n=={'t':'Space'}; count+=1
                            return {**value,'c':seq[:i]+seq[i+1:]}
                        prefix+=len(n['c']) if n['t']=='Str' else 1
        if isinstance(value,dict):return {k:projected(v) for k,v in value.items()}
        if isinstance(value,list):return [projected(v) for v in value]
        return value
    assert projected(before['ast'])==after['ast'] and count==1
    assert len(before['word_blocks'])==len(after['word_blocks'])
    changed=0;ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    for a,b in zip(before['word_blocks'],after['word_blocks']):
        if a==b:continue
        x,y=etree.fromstring(a),etree.fromstring(b)
        assert x.tag==y.tag==ns+'p'
        first,last=formatted_chars(x),formatted_chars(y)
        assert ''.join(c for c,_ in first)==left+' '+right
        assert ''.join(c for c,_ in last)==left+right
        assert first[:len(left)]+first[len(left)+1:]==last
        prop=lambda n:etree.tostring(n) if n is not None else None
        assert prop(x.find(ns+'pPr'))==prop(y.find(ns+'pPr'))
        changed+=1
    assert changed==1


def run(source, output):
    assert not output.exists()
    lua=(source/'src/word/pilot.lua').read_text();css=prepared_css(source)
    assert lua.count(NEW_JOIN)==1 and CSS not in css
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000','-i',
        '-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages',
        '-e','XDG_CACHE_HOME=/tmp/private-cache','--entrypoint','python',IMAGE,'-c']
    matrix=list(cases());rows=[]
    for case in matrix:
        snapshots=[]
        for code in [lua,lua.replace(NEW_JOIN,JOIN)]:
            payload=dict(html=case['html'],lua=code,reference=base64.b64encode((source/'src/word/reference.docx').read_bytes()).decode())
            snapshots.append(json.loads(subprocess.check_output(command+[WORD_RUNNER],input=json.dumps(payload).encode(),timeout=180)))
        word_delta(*snapshots,case['left'],case['right'],case['word_effect'])
        rows.append(dict(case=case['name'],word_separator_removed=case['word_effect'],word=snapshots))
    payload=dict(before=css,after=css+CSS,
        cases=[(c['name'],c['html'],c['left'],c['right'],c['pdf_effect']) for c in matrix])
    pdf=json.loads(subprocess.check_output(command+[PDF_RUNNER],input=json.dumps(payload).encode(),timeout=180))
    mismatches=[c['name'] for c in matrix if c['pdf_effect']!=c['word_effect']]
    assert mismatches==['mixed-boundary']
    result=dict(diagnostic_passed=True,source_integrated=False,recommended_for_integration=False,
        reason='The naive CSS selector removes a separator that the Word boundary guard retains in mixed text.',
        worker_image=IMAGE,synthetic_cases=len(matrix),counterexamples=mismatches,
        source_sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest()
            for n in ['src/layout.css','src/word/pilot.lua','src/word/reference.docx','src/fonts/PilotTC.ttf']},
        word=rows,pdf=pdf,native_project_replay=False,native_ms_word=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['diagnostic_passed','recommended_for_integration','synthetic_cases','counterexamples']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.source.resolve(),args.output.resolve())
