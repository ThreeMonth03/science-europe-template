"""Bounded short-budget PDF hint: exact fragments and conservative fallbacks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from probe_pdf_budget_reading import matrix as long_matrix, render
from generate_pilot_fixtures import IDS
from probe_budget_word import ROOT

BEGIN = '/* BEGIN short-budget panel:'
END = '/* END short-budget panel */'


def split_css(css):
    assert css.count(BEGIN) == css.count(END) == 1
    before, rest = css.split(BEGIN); panel, after = rest.split(END)
    return before+after.removeprefix('\n'), BEGIN+panel+END


def fragments():
    base = dict(title='<p><strong>Resource 1</strong></p>',
        purpose='<div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>Original purpose.</p></div><p>Supports FAIR data.</p>',
        budget='<p data-fact-id="resource-amount-value" data-status="complete">0</p><p class="data-gap" data-requirement-id="SE-6b" data-fact-id="resource-amount" data-status="missing"><strong>Information not provided:</strong> currency.</p>',
        funding='<div class="answer-detail"><p>Institutional funds.</p></div>')
    cases = []
    def changed(name, key, value, eligible=False):
        row = dict(base); row[key] = value; cases.append((name, [row], eligible))
    for n in [0, 1, 2, 3, 4, 8, 33]: cases.append((f'rows-{n}', [dict(base) for _ in range(n)], 1 <= n <= 3))
    changed('complete-budget', 'budget', '<p>0 TWD</p>')
    changed('not-a-budget-gap', 'budget', base['budget'].replace('resource-amount"', 'unknown"'))
    changed('unknown-status', 'budget', base['budget'].replace('"missing"', '"unrecognized"'))
    for field, limit in [('title', 80), ('purpose', 200), ('budget', 80), ('funding', 100)]:
        # Keep the owned gap in a separate row when checking the budget length.
        for delta in [0, 1]:
            row = dict(base); row[field] = '<p>'+'中'*(limit+delta)+'</p>'
            cases.append((f'{field}-length-{limit+delta}', [dict(base), row], delta == 0))
    for field, limit in [('title', 1), ('purpose', 2), ('budget', 3), ('funding', 3)]:
        for delta in [0, 1]:
            row = dict(base); row[field] = '<p>x</p>'*(limit+delta)
            cases.append((f'{field}-paragraphs-{limit+delta}', [dict(base), row], delta == 0))
    for name, value in [('br', '<p>A<br>B</p>'), ('list', '<ul><li>Item</li></ul>'),
        ('heading', '<h4>Heading</h4>'), ('image', '<img src="no-fetch.png">'),
        ('table', '<table><tr><td>Cell</td></tr></table>'), ('link', '<p><a href="https://example.org">Link</a></p>'),
        ('style', '<p style="height:1000px">Text</p>'), ('empty', ''), ('many-inline-tags', '<p>'+'<em></em>'*240+'Text</p>')]:
        changed(name, 'purpose', value)
    changed('inline-and-punctuation', 'purpose', '<p>  <strong>原始。</strong> <em>Purpose.</em> <code>A.csv</code>  </p>', True)
    return cases


def check(root):
    env = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do'])
    helper = env.get_template('src/budget-reading.html.j2').module
    results = []
    for name, rows, eligible in fragments():
        original = '<table class="resource-table"><tbody>'+''.join('<tr>'+''.join('<td>'+r[k]+'</td>' for k in ['title', 'purpose', 'budget', 'funding'])+'</tr>' for r in rows)+'</tbody></table>'
        actual = helper.short_table(original, rows)
        expected = original.replace('class="resource-table"', 'class="resource-table pdf-short-budget"', 1) if eligible else original
        assert actual == expected, (name, 'Hint must be the only byte change')
        results.append({'case': name, 'eligible': eligible, 'passed': True})
    _, base, _ = long_matrix()[0]
    costs = next(p for p in base if p.endswith(IDS['costQUuid'])); first = costs+'.'+base[costs][0]
    for name, updates, eligible in [
        ('complete', {}, False),
        ('missing-currency', {first+'.'+IDS['costCurrencyQUuid']: ''}, True),
        ('missing-amount', {first+'.'+IDS['costAmountQUuid']: ''}, True),
        ('missing-both', {first+'.'+IDS['costAmountQUuid']: '', first+'.'+IDS['costCurrencyQUuid']: ''}, True),
        ('missing-funding-only', {first+'.'+IDS['costCoverQUuid']: ''}, False),
        ('long-purpose-fallback', {first+'.'+IDS['costCurrencyQUuid']: '', first+'.'+IDS['costDescriptionQUuid']: '<p>'+'Long '*1000+'</p>'}, False)]:
        replies = copy.deepcopy(base); replies.update(updates)
        original = render(root, replies); actual = render(root, replies, True)
        assert len(BeautifulSoup(actual, 'html.parser').select('.pdf-short-budget')) == int(eligible), name
        assert actual.replace('class="resource-table pdf-short-budget"', 'class="resource-table"') == original, name
        results.append({'case': 'question-'+name, 'eligible': eligible, 'passed': True})
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source-dir', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    result = {'passed': True, 'release_acceptance': False, 'rows': check(a.source_dir),
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_sha256': {name: hashlib.sha256((a.source_dir/name).read_bytes()).hexdigest() for name in ['src/budget-reading.html.j2', 'src/layout.css']},
        'limits': ['Bounded-fragment hints are not a general HTML validator', 'Native bilingual exports and visual review remain required']}
    assert not a.output.exists(); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': len(result['rows'])}))


if __name__ == '__main__': main()
