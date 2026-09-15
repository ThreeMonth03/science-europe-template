"""Probe Q15 CSS in the pinned worker engine, not only a browser selector library."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from probe_budget_word import IMAGE, ROOT

SELECTOR = 'html body #q-required-resources .resource-table:has(tbody > tr > td:first-child > .answer-detail > :nth-child(12))'
RUNNER = '''import json,sys
from weasyprint import HTML,__version__
from cssselect2 import ElementWrapper,compile_selector_list
payload=json.load(sys.stdin); result=[]
for name,source,eligible in payload['cases']:
    html=HTML(string=source.replace('</head>','<style>'+payload['css']+'</style></head>'))
    root=ElementWrapper.from_html_root(html.etree_element)
    matches=sum(compile_selector_list(payload['selector'])[0].test(e) for e in root.iter_subtree())
    document=html.render()
    values={box.style['break_inside'] for page in document.pages for box in page._page_box.descendants()
            if type(box).__name__=='TableBox' and box.element.get('id')=='budget-probe'}
    assert matches==int(eligible),(name,matches)
    assert values==({'auto'} if eligible else {'avoid'}),(name,values)
    result.append({'case':name,'eligible':eligible,'passed':True,'computed_break_inside':sorted(values)})
print(json.dumps({'weasyprint':__version__,'rows':result}))
'''


def cases():
    def fixture(n):
        return '<html><head></head><body><div id="q-required-resources"><table id="budget-probe" class="resource-table"><tbody><tr><td><div class="answer-detail">' + '<p>Original purpose.</p>' * n + '</div></td><td>0 TWD</td><td>Original funder.</td></tr></tbody></table></div></body></html>'
    long = fixture(12)
    return [('eleven', fixture(11), False), ('twelve', long, True), ('sixty', fixture(60), True),
            ('chinese', long.replace('Original purpose.', '原始用途。'), True),
            ('wrong-question', long.replace('q-required-resources', 'q-other'), False),
            ('wrong-detail', long.replace('answer-detail', 'other-detail'), False),
            ('nested-wrapper', long.replace('<td><div', '<td><section><div').replace('</div></td>', '</div></section></td>'), False),
            ('funding-not-purpose', long.replace('<tr><td>', '<tr><td>Title.</td><td>', 1), False)]


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    css = (ROOT / 'src/layout.css').read_text(); assert SELECTOR + ' { break-inside: auto; }' in css
    payload = {'selector': SELECTOR, 'css': css, 'cases': cases()}
    result = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(payload).encode()))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result.update({'passed': True, 'release_acceptance': False, 'worker_image': IMAGE,
        'checker_sha256': digest(Path(__file__)), 'css_sha256': digest(ROOT / 'src/layout.css'),
        'helper_sha256': {'scripts/probe_budget_word.py': digest(ROOT / 'scripts/probe_budget_word.py')},
        'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'limits': ['Computed style and selector checks, not whole-DMP native rendering or visual acceptance']})
    assert not a.output.exists(); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases': len(result['rows']), 'weasyprint': result['weasyprint']}))


if __name__ == '__main__':
    main()
