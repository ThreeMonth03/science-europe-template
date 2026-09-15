"""Pinned Pandoc Q8 probe: only short name-Div style attributes may change."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from probe_budget_word import ROOT, IMAGE

RUNNER = '''import base64,json,sys,tempfile,subprocess,zipfile
from pathlib import Path
from xml.etree import ElementTree as E
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/"pilot.lua";f.write_text(p["lua"])
 ref=Path(tmp)/"reference.docx";ref.write_bytes(base64.b64decode(p["reference"]))
 common=["pandoc","--from=html","--lua-filter="+str(f)]
 ast=json.loads(subprocess.check_output(common+["--to=json"],input=p["html"].encode()))
 doc=Path(tmp)/"probe.docx"
 subprocess.run(common+["--to=docx","--reference-doc="+str(ref),"-o",str(doc)],input=p["html"].encode(),check=True)
 with zipfile.ZipFile(doc) as z: body=E.fromstring(z.read("word/document.xml"))
 ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
 paragraphs=[]
 for node in body.findall(".//w:body/w:p",ns):
  style=node.find("w:pPr/w:pStyle",ns)
  value=style.get("{"+ns["w"]+"}val") if style is not None else None
  if style is not None:node.find("w:pPr",ns).remove(style)
  paragraphs.append({"text":"".join(t.text or "" for t in node.findall(".//w:t",ns)),"style":value,"other_xml":E.tostring(node,encoding="unicode")})
 print(json.dumps({"ast":ast,"paragraphs":paragraphs}))
'''

HANDLER = '  if div.identifier == "q-copyright-ipr" then return keep_q8_reference_labels(div) end'
STYLE = ['custom-style', 'Pilot List Lead']


def fixture(label='Dataset.csv', permission='Available with attribution.', count=2, extra='', qid='q-copyright-ipr'):
    return '<div id="'+qid+'"><h3>8. Ownership?</h3><div class="answer"><p>Reuse conditions:</p><ul>'+''.join(
        '<li><div>'+label+'</div>'+permission+extra+'</li>' for _ in range(count))+'</ul></div></div>'


def cases():
    return [
        ('two', fixture(), 2), ('one', fixture(count=1), 1),
        ('chinese', fixture(label='沿岸水溫觀測資料', permission='此資料可自由取得，使用時須註明來源。'), 2),
        ('eight', fixture(count=8), 8), ('thirty-two', fixture(count=32), 32),
        ('name-boundary', fixture(label='x'*80), 2), ('cjk-name-boundary', fixture(label='中'*40), 2),
        ('permission-boundary', fixture(permission='p'*320), 2),
        ('punctuation', fixture(label='Original-v1.2.csv &amp; 0', permission='Keep exact: 0.05; A-B.'), 2),
        ('long-name', fixture(label='x'*81), 0), ('wide-name', fixture(label='中'*41), 0),
        ('long-permission', fixture(permission='p'*321), 0), ('thirty-three', fixture(count=33), 0),
        ('empty-name', fixture(label=''), 0), ('empty-permission', fixture(permission=''), 0),
        ('hard-break', fixture(label='First<br>Second'), 0),
        ('authored-paragraphs', fixture(permission='<p>First.</p><p>Second.</p>'), 0),
        ('nested-list', fixture(extra='<ul><li>Original.</li></ul>'), 0),
        ('nested-table', fixture(extra='<table><tr><td>Original.</td></tr></table>'), 0),
        ('image', fixture(label='<img src="never-fetch.png" alt="Original">'), 0),
        ('link', fixture(label='<a href="https://example.org/dataset">Original</a>'), 0),
        ('strong', fixture(label='<strong>Original</strong>'), 0),
        ('attributed-label', fixture().replace('<li><div>', '<li><div data-author="original">'), 0),
        ('nested-authored-list', fixture().replace('<ul>', '<div class="answer-detail"><ul>', 1).replace('</ul></div></div>', '</ul></div></div></div>'), 0),
        ('other-question', fixture(qid='q-data-preservation'), 0),
        ('mixed', '<div id="q-copyright-ipr"><div class="answer"><ul><li><div>Short</div>Permission.</li><li><div>Long</div><p>First.</p><p>Second.</p></li></ul></div></div>', 1),
    ]


def allowed_changes(before, after):
    """Whitelist only an attribute on a previously unstyled one-paragraph Div."""
    if before == after: return 0
    if isinstance(before, dict) and isinstance(after, dict):
        if before.get('t') == after.get('t') == 'Div':
            left, right = before['c'], after['c']
            if left[0] == ['', [], []] and right[0] == ['', [], [STYLE]]:
                assert len(left[1]) == len(right[1]) == 1
                assert left[1][0]['t'] in ['Plain', 'Para']
                assert right[1][0] == {'t': 'Para', 'c': left[1][0]['c']}
                return 1
        assert before.keys() == after.keys()
        return sum(allowed_changes(before[k], after[k]) for k in before)
    if isinstance(before, list) and isinstance(after, list):
        assert len(before) == len(after)
        return sum(allowed_changes(a, b) for a, b in zip(before, after))
    raise AssertionError('Unexpected AST change')


def word_changes(before, after):
    assert len(before) == len(after)
    counts = {}; case = None
    for left, right in zip(before, after):
        assert left['text'] == right['text'] and left['other_xml'] == right['other_xml']
        if left['text'].startswith('CASE: '):
            case = left['text'][6:]; counts[case] = 0
        if left['style'] != right['style']:
            assert case is not None and left['style'] == 'Compact' and right['style'] == 'PilotListLead'
            counts[case] += 1
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    source = ROOT/'src/word/pilot.lua'; lua = source.read_text(); assert lua.count(HANDLER) == 1
    matrix = cases(); html = ''.join('<div id="'+name+'"><h2>CASE: '+name+'</h2>'+body+'</div>' for name, body, _ in matrix)
    results = []
    for variant in [lua.replace(HANDLER, ''), lua]:
        raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER],
                                      input=json.dumps({'lua': variant, 'html': html,
                                          'reference': base64.b64encode((ROOT/'src/word/reference.docx').read_bytes()).decode()}).encode())
        results.append(json.loads(raw))
    asts = [{b['c'][0][0]: b for b in result['ast']['blocks']} for result in results]
    docx_counts = word_changes(results[0]['paragraphs'], results[1]['paragraphs'])
    rows = []
    for name, _, count in matrix:
        before, after = [v[name] for v in asts]
        changed = allowed_changes(before, after)
        assert changed == count, (name, changed, count)
        assert docx_counts[name] == count, (name, 'DOCX styles not applied', docx_counts[name], count)
        rows.append({'case': name, 'styled_labels': changed, 'docx_styled_labels': docx_counts[name], 'passed': True})
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'passed': True, 'release_acceptance': False, 'rows': rows, 'worker_image': IMAGE,
              'checker_sha256': digest(Path(__file__)), 'lua_sha256': digest(source),
              'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'limits': ['AST and actual DOCX with fixed Pandoc, not Microsoft Word layout acceptance',
                         'Long/complex/attributed labels or permissions remain unchanged']}
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': len(rows), 'styled_labels': sum(r['styled_labels'] for r in rows)}))


if __name__ == '__main__': main()
