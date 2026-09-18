"""Pinned Q11 post-filter: selected label joins and exact unselected fallbacks."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from lxml import etree as E

from probe_budget_word import ROOT, IMAGE
from preservation_reading_contract import FILTER, expected_ast, word_content, word_anchors, W
from prepare_layout import prepare_layout

RUNNER = '''import base64,json,os,sys,tempfile,subprocess,zipfile
from pathlib import Path
p=json.load(sys.stdin); rows=[]
os.environ['SOURCE_DATE_EPOCH']='1789603200'
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for name in ('pilot.lua','preservation-reading.lua'): (root/name).write_text(p[name])
 (root/'reference.docx').write_bytes(base64.b64decode(p['reference']))
 for name,html,selected in p['cases']:
  outputs=[]
  for enabled in (False,True):
   common=['pandoc','--from=html','--lua-filter='+str(root/'pilot.lua')]
   if enabled: common+=['--lua-filter='+str(root/'preservation-reading.lua')]
   ast=json.loads(subprocess.check_output(common+['--to=json'],input=html.encode()))
   out=root/'out.docx'
   subprocess.run(common+['--to=docx','--reference-doc='+str(root/'reference.docx'),'-o',str(out)],input=html.encode(),check=True)
   with zipfile.ZipFile(out) as z: parts={n:base64.b64encode(z.read(n)).decode() for n in z.namelist()}
   outputs.append(dict(ast=ast,parts=parts))
  rows.append(dict(name=name,selected=selected,outputs=outputs))
 print(json.dumps(dict(rows=rows,pandoc=subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0])))
'''


def dataset(name='Dataset', summary='<p>Data will be published.</p><p>Retain for ten years.</p>', identifier='one', extra=''):
    return '<div class="dataset-section" data-item-id="'+identifier+'"><h5>'+name+'</h5><div class="preservation-summary dataset-policy">'+summary+'</div>'+extra+'</div>'


def question(content, qid='q-data-preservation'):
    return '<div id="'+qid+'"><h3>11. Preservation?</h3><div class="answer">'+content+'</div></div>'


def cases():
    base = dataset(); rows = [('short', question(base), ['one']),
        ('chinese', question(dataset('沿岸觀測資料', '<p>資料將發布。</p><p>保留 10 年，費用已預付。</p>')), ['one']),
        ('negative-zero', question(dataset(summary='<p>Data will not be published.</p><p>0 years. Original.csv.</p>')), ['one']),
        ('with-tail', question(dataset(extra='<p>Other facts unchanged.</p><ul><li>Original list.</li></ul>')), ['one']),
        ('two-datasets', question(base+dataset('Second', identifier='two')), ['one', 'two']),
        ('empty', question(''), []), ('no-summary', question(dataset(summary='')), []),
        ('wrong-question', question(base, 'q-other'), []),
        ('authored-lookalike', question('<div class="answer-detail">'+base+'</div>'), [])]
    rows += [('authored-nested-question', question('<div class="answer-detail">'+question(base)+'</div>'), []),
        ('other-question-authored-lookalike', question(question(base), 'q-copyright-ipr'), []),
        ('cross-reference', question(dataset(extra='<p><a href="#dataset">Retained link.</a></p>')), ['one']),
        ('empty-list-tail', question(dataset(extra='<ul><li></li></ul>')), ['one'])]
    for name, value in [('name-boundary', 'x'*80), ('name-too-long', 'x'*81), ('cjk-name-boundary', '中'*40), ('cjk-name-too-long', '中'*41)]:
        rows.append((name, question(dataset(value)), ['one'] if 'boundary' in name else []))
    for length in (359, 360, 361): rows.append(('summary-'+str(length), question(dataset(summary='<p>'+'x'*length+'</p>')), ['one'] if length <= 360 else []))
    for length in (180, 181): rows.append(('cjk-summary-'+str(length), question(dataset(summary='<p>'+'中'*length+'</p>')), ['one'] if length == 180 else []))
    for name, summary in [('authored', '<div class="answer-detail"><p>Free answer.</p></div><p>Fixed policy.</p>'),
        ('gap', '<p>Fixed policy.</p><div class="reading-gap"><p>Missing.</p></div>'),
        ('link', '<p><a href="https://example.org">Original</a></p>'), ('strong', '<p><strong>Original</strong></p>'),
        ('span', '<p><span data-owned="unknown">Original</span></p>'), ('code', '<p><code>0.csv</code></p>'),
        ('break', '<p>First<br>Second</p>'), ('list', '<ul><li>Original.</li></ul>'),
        ('table', '<table><tr><td>Original.</td></tr></table>'), ('image', '<p><img src="never-fetch.png" alt="Original"></p>')]:
        rows.append((name, question(dataset(summary=summary)), []))
    for name, old, new in [('unknown-dataset-class', 'dataset-section', 'dataset-section unknown'),
        ('unknown-policy-class', 'preservation-summary dataset-policy', 'preservation-summary dataset-policy unknown'),
        ('unknown-attribute', 'data-item-id="one"', 'data-item-id="one" data-other="unknown"'),
        ('missing-identity', 'data-item-id="one"', ''), ('unknown-heading', '<h5>', '<h5 class="unknown">'),
        ('rich-name', 'Dataset</h5>', '<em>Dataset</em></h5>')]: rows.append((name, question(base.replace(old, new)), []))
    rows.append(('mixed', question(base+dataset('Long', '<p>'+'x'*361+'</p>', 'two')), ['one']))
    rows.append(('mixed-second-only', question(dataset('Dataset', '<p>'+'x'*361+'</p>')+dataset(identifier='two')), ['two']))
    rows.append(('same-labels', question(base+dataset(identifier='two')), ['one', 'two']))
    return rows


def reference(root):
    path = root/'src/word/reference.docx'
    with zipfile.ZipFile(path) as archive:
        if b'PilotPreservationSummary' in archive.read('word/styles.xml'): return path.read_bytes()
    # Reference-only engine probes need no real PDF font; preparing here gives
    # the same paragraph styles without introducing an undeclared CI asset.
    with tempfile.TemporaryDirectory(prefix='preservation-reference-') as temp:
        folder = Path(temp); (folder/'src/word').mkdir(parents=True)
        shutil.copyfile(path, folder/'src/word/reference.docx')
        shutil.copyfile(root/'src/layout.css', folder/'src/layout.css')
        font = folder/'unused-font.ttf'; font.write_bytes(b'Reference-only probe; never render this font')
        prepare_layout(folder, font, 'en')
        return (folder/'src/word/reference.docx').read_bytes()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, default=ROOT); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    payload = {name: (a.source_dir/'src/word'/name).read_text() for name in ('pilot.lua', 'preservation-reading.lua')}
    payload.update(reference=base64.b64encode(reference(a.source_dir)).decode(), cases=cases())
    report = dict(passed=False, release_acceptance=False, worker_image=IMAGE, rows=[],
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        filter_sha256=hashlib.sha256((a.source_dir/FILTER).read_bytes()).hexdigest())
    try:
        raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(payload).encode())
        result = json.loads(raw); report['pandoc_version'] = result['pandoc']
        for row in result['rows']:
            before, after = row['outputs']; selected = row['selected']
            assert expected_ast(before['ast'], selected) == after['ast'], (row['name'], 'AST delta')
            parts = [{k: base64.b64decode(v) for k, v in out['parts'].items()} for out in (before, after)]
            assert parts[0].keys() == parts[1].keys()
            for name in parts[0]:
                if name != 'word/document.xml': assert parts[0][name] == parts[1][name], (row['name'], name)
            word_content(parts[0]['word/document.xml'], parts[1]['word/document.xml'], word_anchors(before['ast'], selected, parts[0]['word/document.xml']))
            report['rows'].append(dict(case=row['name'], joined_datasets=len(selected), passed=True))
        report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if 'row' in locals():
            report['failed_case'] = row['name']
            report['failed_outputs'] = row['outputs']
        raise
    finally:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(passed=True, cases=len(report['rows']))))


if __name__ == '__main__': main()
