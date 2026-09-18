"""Q3 prose: exact fact-preserving HTML, pinned PDF/screen and actual DOCX."""
import argparse
import base64
import itertools
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as E
from bs4 import BeautifulSoup
from probe_budget_word import IMAGE, ROOT
from probe_empty_pdf import prepared_css
from probe_q8_word import RUNNER as WORD_RUNNER
from metadata_gap_panel_contract import historical_css, digest
from metadata_gap_prose_contract import templates, compare, OLD, joined

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def word_text(xml):
    return ''.join(n.text or '' for n in E.fromstring(xml).findall('.//w:t', NS))


def check_word(before, after, language):
    """Allow only the exact adjacent warning pair -> one styled paragraph."""
    result = list(before)
    indexes = [i for i, block in enumerate(result) if word_text(block) == OLD[language][0]]
    count = 0
    for i in reversed(indexes):
        if i + 1 >= len(result) or word_text(result[i + 1]) != OLD[language][1]:
            continue  # Independent missing/review states are not a joined pair.
        candidates = [b for b in after if word_text(b) == joined(language).get_text()]
        assert candidates and len(set(candidates)) == 1, 'Missing or inconsistent joined Word paragraph'
        replacement = candidates[0]
        nodes = [E.fromstring(b) for b in [result[i], result[i + 1], replacement]]
        assert all(n.tag == '{' + NS['w'] + '}p' for n in nodes)
        styles = [E.tostring(n.find('w:pPr', NS)) for n in nodes]
        assert styles[0] == styles[1] == styles[2], 'Warning paragraph style changed'
        # No links, tables, authored emphasis or controls may hide in the new paragraph.
        allowed = {'pPr', 'r'}
        assert all(n.tag.rsplit('}', 1)[-1] in allowed for n in nodes[2])
        def properties(run):
            props = run.find('w:rPr', NS)
            return E.tostring(props) if props is not None else None
        original = {properties(run) for node in nodes[:2] for run in node.findall('w:r', NS)}
        assert len(original) == 1, 'Original warning runs are not uniformly styled'
        # Pandoc gives Chinese text the original eastAsia hint, but omits the
        # hint on the final standalone full stop after an inline span. Admit
        # that exact generated-punctuation shape, never arbitrary font changes.
        for run in nodes[2].findall('w:r', NS):
            assert all(c.tag in {'{' + NS['w'] + '}t', '{' + NS['w'] + '}rPr'} for c in run)
            text = ''.join(t.text or '' for t in run.findall('w:t', NS))
            if properties(run) not in original:
                assert language == 'chinese' and text == '。' and properties(run) is None, 'Unexpected joined run formatting'
                expected = E.Element('{' + NS['w'] + '}rPr')
                E.SubElement(expected, '{' + NS['w'] + '}rFonts', {'{' + NS['w'] + '}hint': 'eastAsia'})
                assert original == {E.tostring(expected)}
        result[i:i + 2] = [replacement]
        count += 1
    assert result == after, 'Word content/format outside the exact warning pair changed'
    return count


def cases(root, frozen, language):
    sys.path.insert(0, str(ROOT / 'tests'))
    from generate_metadata_fixtures import ACCESS, INSTRUCTIONS, FORM, IDS
    old, new = templates(root, frozen)
    choices = itertools.product(['', ' \t ', IDS['metadataOpenInstrYesAUuid'], IDS['metadataOpenInstrNoAUuid'], 'unknown'],
        ['', ' \t ', IDS['metadataOpenFormNoAUuid'], IDS['metadataOpenFormYesRepoAUuid'], IDS['metadataOpenFormYesCareAUuid'], 'unknown'])
    entries = [('branch-' + str(i), {ACCESS: IDS['metadataOpenYesAUuid'], INSTRUCTIONS: a, FORM: b}) for i, (a, b) in enumerate(choices)]
    entries += [('empty', {}), ('private', {ACCESS: IDS['metadataOpenNoAUuid']}),
        ('stale', {INSTRUCTIONS: IDS['metadataOpenInstrYesAUuid'], FORM: 'unknown'})]
    result = []
    for name, replies in entries:
        soups = [BeautifulSoup(t.render(repliesMap=replies), 'html.parser') for t in (old, new)]
        compare(*soups, language)
        selected = bool(soups[1].select('.metadata-publication-gap'))
        result.append((name, *map(str, soups), selected))
    return result


PDF_RUNNER = '''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin);rows=[];compact=lambda t:re.sub(r'\\s+','',''.join(t))
for name,before,after,selected in p['cases']:
 for media in ['print','screen']:
  for near_end in ([False,True] if selected and media=='print' else [False]):
   snapshots=[]
   for source,css in [(before,p['before_css']),(after,p['after_css'])]:
    spacer='<div style="height:200mm">Before.</div>' if near_end else ''
    doc=HTML(string='<html><body><style>'+css+'</style>'+spacer+source+'</body></html>',media_type=media).render()
    text=[];geometry=[];warnings=[]
    for n,page in enumerate(doc.pages,1):
     roots=[b for b in page._page_box.children if type(b).__name__=='BlockBox' and b.element.tag=='html'];assert len(roots)==1
     for b in roots[0].descendants():
      if type(b).__name__=='TextBox':
       text.append(b.text);geometry.append((n,b.position_x,b.position_y,b.width,b.height,b.text))
       assert b.position_x>=0 and b.position_x+b.width<=page.width+.1,(name,'horizontal clipping')
      if type(b).__name__=='BlockBox' and b.element.tag=='p' and ('metadata-publication-gap' in b.element.get('class','') or b.element.get('data-fact-id') in p['facts']):warnings.append((n,b))
    snapshots.append((doc,text,geometry,warnings))
   old,new=snapshots
   if selected:
    assert len(old[3])==2 and len(new[3])==1,(name,'warning paragraph split/lost')
    expected=compact(old[1]);first,last=[compact([t]) for t in p['old']]
    assert expected.count(first)==expected.count(last)==1
    expected=expected.replace(first+last,compact([p['joined']]))
    assert expected==compact(new[1]),(name,'unexpected PDF text delta')
    for _,box in old[3]:
     assert [str(box.style[k]) for k in ['font_size','line_height']]==[str(new[3][0][1].style[k]) for k in ['font_size','line_height']]
    assert len(new[0].pages)<=len(old[0].pages),(name,'pages increased')
   else:assert old[2]==new[2],(name,media,'fallback geometry or text changed')
   rows.append(dict(case=name,media=media,near_page_end=near_end,selected=selected,pages=len(new[0].pages),passed=True))
print(json.dumps(dict(weasyprint=__version__,rows=rows)))
'''


def run(code, payload):
    result = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', code],
        input=json.dumps(payload).encode(), capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    return json.loads(result.stdout)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, default=ROOT)
    p.add_argument('--frozen', type=Path, default=ROOT / 'tests/fixtures/metadata-0.3.36.en.html.j2')
    p.add_argument('--language', choices=['english', 'chinese'], default='english')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, release_acceptance=False, checker_sha256=digest(Path(__file__)), worker_image=IMAGE)
    try:
        matrix = cases(a.source_dir, a.frozen, a.language)
        css = prepared_css(a.source_dir); base = (a.source_dir / 'src/style.css').read_text()
        pdf = run(PDF_RUNNER, dict(cases=matrix, before_css=base + historical_css(css), after_css=base + css,
            facts=['metadata-access-instructions', 'metadata-harvestable'], old=OLD[a.language], joined=joined(a.language).get_text()))
        report.update(pdf)
        words = []
        for variant in [1, 2]:
            html = ''.join('<h2>CASE: ' + row[0] + '</h2>' + row[variant] for row in matrix)
            words.append(run(WORD_RUNNER, dict(html=html, lua=(a.source_dir / 'src/word/pilot.lua').read_text(),
                reference=base64.b64encode((a.source_dir / 'src/word/reference.docx').read_bytes()).decode())))
        count = check_word(words[0]['word_blocks'], words[1]['word_blocks'], a.language)
        assert count == sum(row[3] for row in matrix)
        report.update(pdf, passed=True, language=a.language, branch_checks=len(matrix), word_joins=count,
            limits=['Pinned worker engine and actual DOCX, not native DSW or Microsoft Word visual acceptance',
                    'Only two simultaneously absent Q3 publication follow-ups; other states unchanged'])
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, branches=len(matrix), engine_checks=len(pdf['rows']), word_joins=count)))


if __name__ == '__main__':
    main()
