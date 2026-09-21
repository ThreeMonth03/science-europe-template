"""Pinned PDF/Pandoc probes for the Q13-owned Chinese sentence separator."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from lxml import etree
from probe_budget_word import ROOT, IMAGE
from probe_q8_word import RUNNER as WORD_RUNNER
from probe_empty_pdf import prepared_css

CSS_BEGIN = '/* BEGIN identifier CJK separator:'
CSS_END = '/* END identifier CJK separator */'
LUA_BEGIN = '-- BEGIN identifier CJK separator\n'
LUA_END = '-- END identifier CJK separator\n\n'
OLD_JOIN = 'if #inlines > 0 then inlines:insert(pandoc.Space()) end'
NEW_JOIN = 'if #inlines > 0 and not (div.classes:includes("identifier-arrangement") and identifier_cjk_boundary(inlines, block.content)) then inlines:insert(pandoc.Space()) end'


def baseline(source, begin, end):
    assert source.count(begin) == source.count(end) == 1
    a, rest = source.split(begin)
    _, b = rest.split(end)
    return a + b.removeprefix('\n') if begin == CSS_BEGIN else a + b


def old_lua(source):
    assert source.count(NEW_JOIN) == 1
    return baseline(source, LUA_BEGIN, LUA_END).replace(NEW_JOIN, OLD_JOIN)


def frozen_lua(source):
    """Compose the exact reviewed Q5 delta before checking the older Q13 hash."""
    from storage_context_contract import without_reviewed_context
    return old_lua(without_reviewed_context(source, 'lua'))


def without_reviewed_archive_panels(source):
    """Admit exactly the reviewed 0.3.30 block; keep the old Q13 hash gate."""
    from probe_archive_gap_panels import BEGIN, END, split_css
    if BEGIN not in source and END not in source: return source
    previous, block = split_css(source)
    assert hashlib.sha256(block.encode()).hexdigest() == 'bcdbb69bcfd2ddce20f6c55f4ee2ab81754e4059988d6c255eae98c97a77d7f5', 'Unreviewed Q11 CSS'
    return previous


def frozen_prepared_css(source):
    """Strip exact later additions, retaining the original prepared Q13 hash."""
    from metadata_gap_panel_contract import prior_css
    from budget_grouping_contract import without_grouping
    source = without_grouping(source, 'css')
    from probe_storage_context import strip
    prepared, block = strip(prior_css(source) if '/* BEGIN metadata gap panel:' in source else source, 'css')
    delta = json.loads((ROOT / 'docs/storage-context-style-delta.json').read_text())
    assert hashlib.sha256(block.encode()).hexdigest() == delta['css']['block_sha256']
    return baseline(without_reviewed_archive_panels(prepared), CSS_BEGIN, CSS_END)


def fixture(left, right, language='zh-Hant', kind='identifier-arrangement dataset-policy', extra=''):
    return '<html lang="'+language+'"><body><div class="'+kind+'"><p>'+left+'</p><p>'+right+'</p>'+extra+'</div></body></html>'


def cases():
    result = []
    actors = ['持續識別碼將由資料儲存庫指派。', '持續識別碼將由機構的資料託管員指派。',
              '持續識別碼將由計畫的資料託管員或主持人指派。', '資料將取得持續識別碼。']
    for i, left in enumerate(actors):
        for j, right in enumerate(['資料儲存庫將確保持續識別碼可解析至數位物件。',
                                   '資料儲存庫將不保證持續識別碼可解析至數位物件。']):
            result.append((f'zh-{i}-{j}', fixture('<span data-fact-id="identifier-assigner">'+left+'</span>', right), left, right, True))
    # English spacing and unrelated Chinese policy/headings/authored blocks stay as-is.
    for name, left, right, language, kind, extra in [
        ('english', 'The repository will assign the persistent identifier.', 'The repository will make sure it resolves.', 'en', 'identifier-arrangement dataset-policy', ''),
        ('english-negative', 'Persistent identifiers will be assigned.', 'The repository will not ensure resolution.', 'en', 'identifier-arrangement dataset-policy', ''),
        ('other-policy', '原文。', '原文。', 'zh-Hant', 'dataset-policy', ''),
        ('heading', '資料提供管道 1', '機構資料儲存庫', 'zh-Hant', 'identifier-heading', ''),
        ('authored', '作者原文。  保留空格。', '版本 A-B / 0.05 / DOI 10.1000/test', 'zh-Hant', 'answer-detail', ''),
    ]:
        result.append((name, fixture(left,right,language,kind,extra), left,right,False))
    return result


def formatted_chars(node):
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    result = []
    for child in node:
        if child.tag == ns+'pPr': continue
        assert child.tag == ns+'r'
        props = child.find(ns+'rPr')
        style = etree.tostring(props) if props is not None else None
        for part in child:
            assert part.tag in [ns+'rPr',ns+'t']
            if part.tag == ns+'t': result.extend((c,style) for c in part.text or '')
    return result


def word_delta(before, after, left, right, eligible):
    if not eligible:
        assert before == after
        return
    def projected(value):
        if isinstance(value,dict) and value.get('t') == 'Para':
            seq=value['c']
            # A precise oracle: only the one newly inserted separator between
            # two complete fixed phrases may vanish; all other AST nodes stay.
            indices=[i for i,v in enumerate(seq) if v=={'t':'Space'}]
            if len(indices)==1:
                n=indices[0]
                return {**value,'c':seq[:n]+seq[n+1:]}
        if isinstance(value,dict): return {k:projected(v) for k,v in value.items()}
        if isinstance(value,list): return [projected(v) for v in value]
        return value
    assert projected(before['ast']) == after['ast']
    assert len(before['word_blocks']) == len(after['word_blocks'])
    changed=0
    ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    for a,b in zip(before['word_blocks'],after['word_blocks']):
        if a==b: continue
        x,y=etree.fromstring(a),etree.fromstring(b)
        assert x.tag==y.tag==ns+'p'
        chars=formatted_chars(x); current=formatted_chars(y)
        assert ''.join(c for c,_ in chars)==left+' '+right
        assert ''.join(c for c,_ in current)==left+right
        assert chars[:len(left)]+chars[len(left)+1:]==current
        props=lambda n: etree.tostring(n) if n is not None else None
        assert props(x.find(ns+'pPr'))==props(y.find(ns+'pPr'))
        changed+=1
    assert changed==1


PDF_RUNNER = '''import json,sys
from weasyprint import HTML,__version__
p=json.load(sys.stdin);rows=[]
for name,source,left,right,eligible in p['cases']:
 snapshots=[]
 for css in [p['before'],p['after']]:
  doc=HTML(string=source+'<style>'+css+'</style>').render()
  boxes=[b for page in doc.pages for b in page._page_box.descendants() if type(b).__name__=='TextBox']
  snapshots.append({'text':''.join(b.text for b in boxes),'boxes':[(b.text,b.position_x,b.position_y,b.width,b.height,b.style['font_size']) for b in boxes],'pages':len(doc.pages)})
 a,b=snapshots
 if eligible:
  assert a['text']==left+' '+right,(name,a['text'])
  assert b['text']==left+right,(name,b['text'])
  assert {x[-1] for x in a['boxes']}=={x[-1] for x in b['boxes']}
  assert b['pages']<=a['pages']
 else:assert a==b,(name,'Fallback PDF geometry changed')
 rows.append({'case':name,'eligible':eligible,'before':a,'after':b})
print(json.dumps({'weasyprint':__version__,'rows':rows}))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--preflight-only',action='store_true',help='Check frozen prepared-source gates before expensive engine probes')
    a=p.parse_args(); assert not a.output.exists()
    lua=(a.source_dir/'src/word/pilot.lua').read_text()
    css=prepared_css(a.source_dir)
    # Freeze 0.3.27's actual prepared source, not a baseline inferred from the
    # new behavior. This probe deliberately requires a prepared build folder.
    digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
    assert digest(frozen_lua(lua))=='7136b5e64ac731b736ed3dd400e7e69994e89448c54bb2b6e35ccbc189275fa7'
    # Prepared CSS contains the font/profile prefix; strip the exact source
    # addition before retaining the original prepared-CSS hash gate.
    assert digest(frozen_prepared_css((a.source_dir/'src/layout.css').read_text()))=='840c42a6fe505d73dcaf6eb9c57a92dd2c26d67416206f1a7d73f539cc812362'
    if a.preflight_only:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(dict(passed=True, preflight_only=True, release_acceptance=False,
            checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            source_sha256={name:hashlib.sha256((a.source_dir/name).read_bytes()).hexdigest() for name in ['src/layout.css','src/word/pilot.lua']}), indent=2)+'\n')
        print(json.dumps(dict(passed=True, preflight_only=True)))
        return
    matrix=cases();rows=[]
    command=['docker','run','--rm','--network','none','-i','--entrypoint','python',IMAGE,'-c']
    for name,html,left,right,eligible in matrix:
        result=[]
        for code in [old_lua(lua),lua]:
            payload={'html':html,'lua':code,'reference':base64.b64encode((a.source_dir/'src/word/reference.docx').read_bytes()).decode()}
            result.append(json.loads(subprocess.check_output(command+[WORD_RUNNER],input=json.dumps(payload).encode())))
        word_delta(*result,left,right,eligible)
        rows.append({'case':name,'removed_inserted_word_spaces':int(eligible),'passed':True})
    pdf=json.loads(subprocess.check_output(command+[PDF_RUNNER],input=json.dumps({'before':baseline(css,CSS_BEGIN,CSS_END),'after':css,'cases':matrix}).encode()))
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'passed':True,'release_acceptance':False,'word':rows,'pdf':pdf,'worker_image':IMAGE,
            'source_sha256':{n:sha(a.source_dir/n) for n in ['src/layout.css','src/word/pilot.lua','src/word/reference.docx']},
            'checker_sha256':sha(Path(__file__)),
            'limits':['Synthetic engine probes, not native project or Microsoft Word acceptance',
                      'Only fixed Q13 policy boundaries; other Chinese sentence spaces remain']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'word_spaces_removed':sum(r['removed_inserted_word_spaces'] for r in rows)}))


if __name__=='__main__': main()
