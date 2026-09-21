"""Bounded profile oracle. Never delete diagnostics from production HTML here.

This is an independent test projection of explicitly owned template nodes;
authored blocks and every other question must remain unchanged.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
import test_science_europe_contract as adapter
from probe_pdf_budget_reading import dom

CONTRACT = json.loads((ROOT/'requirements/output-profiles.json').read_text())
WRAPPER = ("{% import 'src/macros.html.j2' as macros with context %}"
           "{% import 'src/uuids.j2' as uuids with context %}"
           "{% include 'src/projects.html.j2' %}{% include 'src/content.html.j2' %}")


def environment(root, escape=False, overrides=None):
    loaders = ([DictLoader(overrides)] if overrides else []) + [FileSystemLoader(root)]
    env = Environment(loader=ChoiceLoader(loaders), extensions=['jinja2.ext.do'], autoescape=escape)
    env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items,
        reply_str_value=adapter.reply_str_value, markdown=lambda v: Markup(v) if escape else v,
        any=any, dot=lambda v: str(v) + ('' if str(v).endswith('.') else '.'))
    env.tests['true'] = lambda v: v is True
    return env


def expected(review, language):
    """Exact structural delta allowed by this partial pilot, not a blanket hide."""
    soup = copy.deepcopy(review)
    q3 = soup.select_one('#q-docs-metadata > .answer')
    for node in list(q3.select(':scope > .metadata-policy > .reading-gap, '
                              ':scope > .storage-conventions-policy > .reading-gap, '
                              ':scope > .data-gap[data-status="missing-output"]')):
        node.decompose()
    for node in list(q3.select(':scope > .storage-conventions-policy')):
        if not node.get_text().strip() and not node.select('img, table'):
            heading = node.find_previous_sibling('h4')
            assert heading is not None
            heading.decompose(); node.decompose()
    if not q3.get_text().strip() and not q3.select('img, table'):
        q3.clear()
    for node in list(soup.select('#q-store-backup > .answer > .storage-detail-limits')):
        parent = node.parent
        parent['class'] = [c for c in parent.get('class', []) if c != 'q5-short-context']
        node.decompose()
    for node in list(soup.select('#q-data-preservation > .answer > .reading-gap > '
                                '[data-fact-id="preservation-selection-review"]')):
        node.parent.decompose()
    funding = 'Funding information has not been provided.' if language == 'english' else '尚未提供經費來源。'
    for row in list(soup.select('#dmp-projects > .project > .project-details > tbody > tr')):
        cell = row.find('td', recursive=False)
        if cell and not cell.find(True) and cell.get_text().strip() == funding:
            row.decompose()
    for node in soup.select('p.data-gap[data-fact-id="quality-methods"][data-status="missing"]'):
        # Never match inside an authored answer-detail block.
        if node.find_parent(class_='answer-detail'): continue
        name = copy.deepcopy(node.strong); assert name is not None
        node.clear(); node['class'] = ['quality-summary']; node['data-status'] = 'partial'
        node.append('Quality control is planned for ' if language == 'english' else '本計畫將對 ')
        node.append(name); node.append('.' if language == 'english' else ' 進行品質管控。')
    return soup


def compare(review, submission, language):
    assert dom(expected(review, language)) == dom(submission), 'Unexpected profile fact/prose/structure delta'
    assert len(submission.select('.question')) == 15
    assert len(submission.select('.dmp-section')) == 6
    assert not submission.select('p p, p div, p ul, p table')


def check(root, fixture_folder, language, baseline=False, source_overrides=None):
    overrides = None
    if baseline:
        overrides = {**(source_overrides or {}), **{name: subprocess.check_output(['git', '-C', str(ROOT), 'show',
            CONTRACT['baseline_commit']+':'+name], text=True) for name in CONTRACT['changed_source_files']}
        }
    rows = []
    for escape in (False, True):
        template = environment(root, escape, source_overrides).from_string(WRAPPER)
        prior = environment(root, escape, overrides).from_string(WRAPPER) if overrides else None
        for filename in sorted(fixture_folder.glob('*.events.json')):
            replies = {e['path']: ({'value': {'value': e['value']['value']}}
                       if e['value']['type'] == 'IntegrationReply' else e['value']['value'])
                       for e in json.loads(filename.read_text())}
            render = lambda **kw: BeautifulSoup(template.render(repliesMap=replies, **kw), 'html.parser')
            review, submission = render(), render(output_profile='submission')
            compare(review, submission, language)
            assert dom(review) == dom(render(output_profile='review'))
            assert dom(review) == dom(render(output_profile='unknown'))
            if prior:
                assert dom(review) == dom(BeautifulSoup(prior.render(repliesMap=replies), 'html.parser')), (filename.name, 'Review changed from 0.3.37')
            if filename.name == 'profile-partial.events.json':
                marker = 'Information not provided: this is authored' if language == 'english' else '尚待補充：這是使用者填寫'
                assert marker in submission.get_text()
                assert 'Original.csv' in submission.get_text()
                assert len(submission.select('[data-fact-id="quality-methods"][data-status="partial"]')) == 2
            rows.append({'case': filename.name, 'autoescape': escape,
                         'remaining_diagnostic_nodes': len(submission.select('.data-gap')), 'passed': True})
    return rows
