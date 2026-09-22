"""Text/structure oracle for conservative empty-heading classification."""
import copy
import itertools
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from output_profile_contract import environment, WRAPPER
from probe_pdf_budget_reading import dom

CLASS = 'compact-empty-question'


def expected(page, profile):
    """Parsed-DOM oracle, independent of the implementation's string whitelist."""
    result = copy.deepcopy(page)
    if profile != 'submission': return result
    for question in result.select('#dmp-content > .dmp-section > .question'):
        answer = question.select_one(':scope > .answer')
        if answer is None: continue
        visible = [n for n in answer.contents if getattr(n, 'name', None) or str(n).strip()]
        empty = not visible
        if not empty and question.get('id') == 'q-store-backup' and len(visible) == 1:
            policy = visible[0]
            if getattr(policy, 'name', None) == 'div' and policy.attrs == {'class':['workspace-policy', 'dataset-policy']}:
                children = [n for n in policy.contents if getattr(n, 'name', None) or str(n).strip()]
                empty = len(children) == 2 and all(getattr(n, 'name', None) == 'div' and n.attrs == {'class':['reading-gap']} and not n.contents for n in children)
        if empty: question['class'].append(CLASS)
    return result


def overrides(sources):
    return {n: v.decode() if isinstance(v, bytes) else v for n, v in sources.items() if n.endswith('.j2')}


def check(root, before, after):
    rows = []
    for escape, profile in itertools.product([False, True], ['review', 'submission', 'unknown']):
        old = environment(root, escape, overrides(before)).from_string(WRAPPER)
        new = environment(root, escape, overrides(after)).from_string(WRAPPER)
        cases = [('empty', {})]
        for fixture in sorted((root / 'fixtures/pilot/en').glob('*.events.json')):
            values = {e['path']: ({'value': {'value': e['value']['value']}}
                if e['value']['type'] == 'IntegrationReply' else e['value']['value']) for e in json.loads(fixture.read_text())}
            cases.append((fixture.name, values))
        for case, values in cases:
            args = dict(repliesMap=values, output_profile=profile, dc={'project':{'created_by':None}, 'e':{'choices':{}}})
            a, b = [BeautifulSoup(t.render(**args), 'html.parser') for t in [old, new]]
            assert dom(expected(a, profile)) == dom(b), (case, profile, 'Unexpected content/structure change')
            assert len(b.select('.question')) == 15 and len(b.select('.dmp-section')) == 6
            if case == 'empty': assert len(b.select('.' + CLASS)) == (15 if profile == 'submission' else 0)
            rows.append(dict(case=case, profile=profile, autoescape=escape, marked=len(b.select('.'+CLASS))))
        # Minimal HTML probes ensure zero/images/tables/unknown markup are never empty.
        helper = environment(root, escape, overrides(after)).from_string(
            "{% import 'src/question-spacing.html.j2' as q with context %}"
            "{% call q.question(identifier) %}{{ html|safe }}{% endcall %}")
        variants = [('', True), (' \n\t', True), ('0', False), ('<p>0</p>', False),
            ('<img src="data:image/png;base64,AA==" alt="">', False), ('<hr>', False), ('<br>', False),
            ('<table><tr><td></td></tr></table>', False), ('<p></p>', False), ('<div class="answer-detail"></div>', False),
            ('&lt;p&gt;&lt;/p&gt;', False), ('<!-- authored comment -->', False),
            ('<div class="question"><h3>Authored question</h3><div class="answer"></div></div>', False)]
        for index, (body, eligible) in enumerate(variants):
            html = '<div id="q-quality-control" class="question" data-requirement-id="SE-2b"><h3>4. Quality?</h3><div class="answer">' + body + '</div></div>'
            output = helper.render(identifier='q-quality-control', html=html, output_profile=profile)
            wanted = html.replace('class="question"', 'class="question ' + CLASS + '"', 1) if eligible and profile == 'submission' else html
            assert output == wanted, ('non-text or literal content misclassified', index, profile)
            rows.append(dict(case='classifier-'+str(index), profile=profile, autoescape=escape, marked=int(eligible and profile=='submission')))
        # A mismatched root must not change a nested or authored heading.
        html = '<div id="q-other" class="question" data-requirement-id="SE-2b"><h3>Other</h3><div class="answer"></div></div>'
        assert helper.render(identifier='q-quality-control', html=html, output_profile=profile) == html
        rows.append(dict(case='mismatched-root', profile=profile, autoescape=escape, marked=0))
    return rows
