"""Historical 0.3.36 two-gap panel; current prose is verified in its own probe."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from probe_budget_word import IMAGE, ROOT
from probe_empty_pdf import prepared_css
from metadata_gap_panel_contract import SELECTOR, prior_css, historical_css, digest


def branch_rows(root):
    sys.path.insert(0, str(ROOT / 'tests'))
    import test_science_europe_contract as adapter
    from generate_metadata_fixtures import ACCESS, INSTRUCTIONS, FORM, IDS
    previous = adapter.ROOT
    adapter.ROOT = root
    try:
        instructions = ['', ' \t ', IDS['metadataOpenInstrYesAUuid'], IDS['metadataOpenInstrNoAUuid'], 'unknown']
        forms = ['', ' \t ', IDS['metadataOpenFormNoAUuid'], IDS['metadataOpenFormYesRepoAUuid'], IDS['metadataOpenFormYesCareAUuid'], 'unknown']
        for i, (instruction, form) in enumerate(itertools.product(instructions, forms)):
            replies = {ACCESS: IDS['metadataOpenYesAUuid'], INSTRUCTIONS: instruction, FORM: form}
            html = adapter.render_question('src/questions/03-docs-metadata.html.j2', replies)
            from metadata_gap_prose_contract import restore
            language = 'chinese' if '尚待補充' in html else 'english'
            html = str(restore(BeautifulSoup(html, 'html.parser'), language))
            yield 'branch-' + str(i), html, not instruction.strip() and not form.strip()
    finally:
        adapter.ROOT = previous


def cases(root):
    matrix = list(branch_rows(root))
    result = [matrix[i] for i in [0, 1, 2, 5, 6, 12, 18, 24, 29]]
    base = matrix[0][1]

    def changed(name, edit):
        soup = BeautifulSoup(base, 'html.parser')
        edit(soup)
        result.append((name, str(soup), False))

    changed('wrong-question', lambda s: s.select_one('.question').__setitem__('id', 'other'))
    changed('wrong-policy', lambda s: s.select_one('.metadata-policy').__setitem__('class', ['dataset-policy']))
    changed('unknown-fact', lambda s: s.select_one('.data-gap').__setitem__('data-fact-id', 'future-field'))
    changed('explicit-no', lambda s: s.select_one('.data-gap').__setitem__('data-status', 'explicit-no'))
    changed('needs-review', lambda s: s.select_one('.data-gap').__setitem__('data-status', 'needs-review'))
    changed('unmapped', lambda s: s.select_one('.data-gap').__setitem__('data-status', 'unmapped'))
    changed('no-gap-class', lambda s: s.select_one('.data-gap').__setitem__('class', []))
    changed('nested-inline', lambda s: s.select_one('.data-gap').append(BeautifulSoup('<em>Original.csv</em>', 'html.parser')))
    changed('extra-child', lambda s: s.select_one('.reading-gap').append(s.new_tag('p')))
    changed('missing-child', lambda s: s.select('.data-gap')[-1].decompose())
    changed('wrong-order', lambda s: s.select_one('.reading-gap').insert(0, s.select('.data-gap')[-1].extract()))
    changed('authored-between', lambda s: s.select_one('.data-gap').insert_after(BeautifulSoup('<div class="answer-detail"><p>Keep Original.csv.</p></div>', 'html.parser')))
    changed('nested-container', lambda s: s.select_one('.reading-gap').wrap(s.new_tag('div', attrs={'class': 'answer-detail'})))
    return result


RUNNER = '''import json,sys
from weasyprint import HTML,__version__
from cssselect2 import ElementWrapper,compile_selector_list
p=json.load(sys.stdin);rows=[]
for name,source,selected in p['cases']:
 for media in ['print','screen']:
  for near_end in ([False,True] if selected and media=='print' else [False]):
   snapshots=[]
   for css in [p['before'],p['after']]:
    spacer='<div style="height:200mm">Before.</div>' if near_end else ''
    doc=HTML(string='<html><body><style>'+css+'</style>'+spacer+source+'</body></html>',media_type=media).render()
    text=[];facts={};panels=[];geometry=[]
    for n,page in enumerate(doc.pages,1):
     roots=[b for b in page._page_box.children if type(b).__name__=='BlockBox' and b.element.tag=='html'];assert len(roots)==1
     for b in roots[0].descendants():
      if type(b).__name__=='TextBox':
       text.append(b.text);geometry.append((n,b.position_x,b.position_y,b.width,b.height,b.text))
      if type(b).__name__=='BlockBox' and b.element.tag=='p' and b.element.get('data-fact-id'):
       key=b.element.get('data-fact-id');assert key not in facts,(name,'split fact');facts[key]=(n,b)
      if type(b).__name__=='BlockBox' and b.element.get('class')=='reading-gap':panels.append((n,b))
    snapshots.append((doc,text,facts,panels,geometry))
   old,new=snapshots;assert old[1]==new[1],(name,media,'text or wrapping changed')
   active=selected and media=='print'
   height_before=height_after=None
   if active:
    assert len(new[3])==1 and len(new[2])==2
    first,last=[new[2][key] for key in ['metadata-access-instructions','metadata-harvestable']]
    assert first[0]==last[0]==new[3][0][0],(name,'panel split')
    panel=new[3][0][1];assert panel.style['border_left_width']==3
    height_before=sum(b.border_height() for _,b in old[3]);height_after=panel.border_height()
    assert 0<height_after<height_before and height_after<160,(name,'unbounded panel')
    for key,(_,b) in new[2].items():
     a=old[2][key][1]
     assert b.style['border_left_width']==b.style['border_top_width']==b.style['border_bottom_width']==0
     assert [str(a.style[k]) for k in ['font_size','line_height']]==[str(b.style[k]) for k in ['font_size','line_height']]
     assert abs(a.content_box_x()-b.content_box_x())<.01 and abs(a.width-b.width)<.01,(name,'text width changed')
   else:assert old[4]==new[4],(name,media,'fallback geometry changed')
   root=ElementWrapper.from_html_root(HTML(string='<html><body>'+source+'</body></html>').etree_element)
   count=sum(compile_selector_list(p['selector'])[0].test(e) for e in root.iter_subtree())
   assert count==int(selected),(name,'selector mismatch',count)
   rows.append(dict(case=name,media=media,near_page_end=near_end,selected=active,height_before=height_before,height_after=height_after,pages=len(new[0].pages),passed=True))
print(json.dumps(dict(weasyprint=__version__,rows=rows)))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    css = historical_css(prepared_css(args.source_dir))
    legacy = (args.source_dir / 'src/style.css').read_text()
    branches = list(branch_rows(args.source_dir))
    for name, source, selected in branches:
        soup = BeautifulSoup('<html><body>' + source + '</body></html>', 'html.parser')
        assert len(soup.select(SELECTOR)) == int(selected), name
    payload = dict(cases=cases(args.source_dir), before=legacy + prior_css(css), after=legacy + css, selector=SELECTOR)
    result = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(payload).encode(), capture_output=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if result.returncode:
        target = args.output.with_suffix('.failure.json')
        assert not target.exists()
        target.write_text(json.dumps(dict(passed=False, stderr=result.stderr.decode()), indent=2) + '\n')
        raise RuntimeError('Pinned engine failed: ' + str(target))
    report = json.loads(result.stdout)
    report.update(passed=True, historical_not_current_template=True, release_acceptance=False, worker_image=IMAGE,
        branch_checks=len(branches), checker_sha256=digest(Path(__file__)),
        css_sha256=digest(args.source_dir / 'src/layout.css'),
        limits=['Only the two named unanswered Q3 publication follow-ups', 'No wording, Jinja, font or Word changes', 'Native DSW and Microsoft Word acceptance are separate'])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, branch_checks=len(branches), engine_checks=len(report['rows']))))


if __name__ == '__main__':
    main()
