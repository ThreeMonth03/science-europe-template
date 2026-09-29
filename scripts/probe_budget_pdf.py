"""Check current bounded-budget hints and computed styles in the pinned worker."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from jinja2 import Environment, FileSystemLoader
from probe_budget_word import IMAGE, ROOT

SELECTOR = 'html body .resource-table.pdf-bounded-budget, html body .resource-table.pdf-short-budget'
RUNNER = '''import json,sys
from weasyprint import HTML,__version__
from cssselect2 import ElementWrapper,compile_selector_list
payload=json.load(sys.stdin); result=[]
selectors=compile_selector_list(payload['selector'])
for name,source,keep in payload['cases']:
    html=HTML(string=source.replace('</head>','<style>'+payload['css']+'</style></head>'))
    root=ElementWrapper.from_html_root(html.etree_element)
    matches=sum(any(selector.test(e) for selector in selectors) for e in root.iter_subtree())
    document=html.render()
    values={box.style['break_inside'] for page in document.pages for box in page._page_box.descendants()
            if type(box).__name__=='TableBox' and box.element.get('id')=='budget-probe'}
    assert matches==int(keep),(name,matches)
    assert values==({'avoid'} if keep else {'auto'}),(name,values)
    result.append({'case':name,'keep_whole_table':keep,'passed':True,'computed_break_inside':sorted(values)})
print(json.dumps({'weasyprint':__version__,'rows':result}))
'''


def cases(root=ROOT):
    def fixture(n):
        return '<html><head></head><body><div id="q-required-resources"><table id="budget-probe" class="resource-table"><tbody><tr><td><div class="answer-detail">' + '<p>Original purpose.</p>' * n + '</div></td><td>0 TWD</td><td>Original funder.</td></tr></tbody></table></div></body></html>'
    long = fixture(12)
    # Retain the old boundary/structure fixtures. Unmarked tables now default to
    # auto: paragraph or row counts alone must not force a whole-table keep.
    result = [('eleven', fixture(11), False), ('twelve', long, False), ('sixty', fixture(60), False),
            ('chinese', long.replace('Original purpose.', '原始用途。'), False),
            ('wrong-question', long.replace('q-required-resources', 'q-other'), False),
            ('wrong-detail', long.replace('answer-detail', 'other-detail'), False),
            ('nested-wrapper', long.replace('<td><div', '<td><section><div').replace('</div></td>', '</div></section></td>'), False),
            ('funding-not-purpose', long.replace('<tr><td>', '<tr><td>Title.</td><td>', 1), False)]
    helper = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do']).get_template('src/budget-reading.html.j2').module
    for language, sentence in [('en', 'Retain original data.'), ('zh', '保留原始資料。')]:
        gap = '<p class="data-gap" data-requirement-id="SE-6b" data-fact-id="resource-amount" data-status="missing">Amount / 金額</p>'
        for name, count, purpose, budget, keep in [
            ('bounded', 1, '<p>'+sentence+'</p>', '<p>0 TWD</p>', True),
            ('three-rows', 3, '<p>'+sentence+'</p>', '<p>0 TWD</p>', True),
            ('four-rows', 4, '<p>'+sentence+'</p>', '<p>0 TWD</p>', False),
            ('single-long-paragraph', 1, '<p>'+sentence*150+'</p>', '<p>0 TWD</p>', False),
            ('many-paragraphs', 1, ('<p>'+sentence+'</p>')*16, '<p>0 TWD</p>', False),
            ('missing-amount', 1, '<p>'+sentence+'</p>', gap, True),
        ]:
            row = dict(title='<p>Storage / 儲存</p>', purpose=purpose, budget=budget, funding='<p>Institute / 機構</p>')
            original = '<table class="resource-table"><tbody>' + (
                '<tr><td>'+row['title']+purpose+'</td><td>'+budget+'</td><td>'+row['funding']+'</td></tr>')*count + '</tbody></table>'
            actual = str(helper.short_table(original, [row]*count)).replace('<table ', '<table id="budget-probe" ', 1)
            result.append((language+'-'+name, '<html><head></head><body><div id="q-required-resources">'+actual+'</div></body></html>', keep))
    for hint in ['pdf-bounded-budget', 'pdf-short-budget']:
        result.append(('wrong-table-'+hint, fixture(1).replace('class="resource-table"', 'class="other-table '+hint+'"'), False))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    css = (ROOT / 'src/layout.css').read_text()
    payload = {'selector': SELECTOR, 'css': css, 'cases': cases()}
    result = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(payload).encode()))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result.update({'passed': True, 'release_acceptance': False, 'worker_image': IMAGE,
        'checker_sha256': digest(Path(__file__)), 'css_sha256': digest(ROOT / 'src/layout.css'),
        'helper_sha256': {name: digest(ROOT / name) for name in ['scripts/probe_budget_word.py', 'src/budget-reading.html.j2']},
        'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'limits': ['Computed style and selector checks, not whole-DMP native rendering or visual acceptance']})
    assert not a.output.exists(); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases': len(result['rows']), 'weasyprint': result['weasyprint']}))


if __name__ == '__main__':
    main()
