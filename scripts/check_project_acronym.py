"""Bounded bilingual checks for the optional project acronym mapping."""
import copy
import itertools

from bs4 import BeautifulSoup
from check_answer_mapping import chapter, question, schema
from current_support import PREFIX, IDS, WRAPPER, environment, path

ACRONYM = '5b765df9-299f-4855-9e99-aa844903f8f6'
LISTING = path('adminDetailsCUuid', 'projectsQUuid')
LABELS = {'en': 'Project acronym', 'zh-Hant': '計畫簡稱'}


def fixture(acronym='COAST', name='Coastal observation', item='project-a'):
    km = schema()
    children = question(km, chapter(km, IDS['adminDetailsCUuid']),
                        IDS['projectsQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, ACRONYM, 'ValueQuestion')
    question(km, children, IDS['projectNameQUuid'], 'ValueQuestion')
    replies = {LISTING: [item]}
    if acronym is not None:
        replies[path(LISTING, item, ACRONYM)] = acronym
    if name is not None:
        replies[path(LISTING, item, 'projectNameQUuid')] = name
    return km, replies


def check(root, language):
    css = (root / 'src/layout.css').read_text()
    selector = 'html body #dmp-projects > .project > table.project-details'
    for rule in [' { table-layout: fixed; }', ' th { width: 24%; }',
                 ' td { overflow-wrap: anywhere; word-break: break-word; }']:
        assert selector + rule in css, ('Missing project table rule', rule)
    counts = dict(value_cases=0, inactive_cases=0, identity_cases=0, full_documents=0)
    for escape in (False, True):
        env = environment(root, escape)
        overview = env.from_string(PREFIX + "{% include 'src/projects.html.j2' %}")
        full = env.from_string(WRAPPER)

        def render(template, km, replies, profile):
            soup = BeautifulSoup(template.render(km=km, repliesMap=replies,
                output_profile=profile, dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')
            assert not soup.select('script, img, p p, p table, p div')
            if profile == 'submission':
                assert not soup.select('.data-gap, .data-review, .empty-value')
            return soup

        for acronym, name, profile in itertools.product(
                [None, '', ' \n\t ', 'COAST', '0', 'N/A', 'A <B> & "C"',
                 '<img src=x onerror=alert(1)>', '海岸觀測-Coastal-' * 30],
                [None, '', 'Coastal observation'], ['review', 'submission']):
            km, replies = fixture(acronym, name)
            soup = render(overview, km, replies, profile)
            rows = soup.select('[data-fact-id="project-acronym"]')
            visible = bool(acronym and acronym.strip())
            assert len(rows) == int(visible), (acronym, name, profile)
            if visible:
                assert rows[0].name == 'tr' and rows[0]['data-status'] == 'complete'
                assert rows[0].th.get('scope') == 'row'
                assert rows[0].th.get_text() == LABELS[language]
                assert rows[0].td.get_text() == acronym
                assert not rows[0].td.find(True), 'Acronym is plain text, not authored HTML'
            if profile == 'submission':
                assert bool(soup.select('table.project-details')) == visible
                if not name:
                    assert soup.h3.get_text(strip=True) == ('Project 1' if language == 'en' else '計畫 1')
            counts['value_cases'] += 1

        for change, profile in itertools.product(
                ['chapter-filtered', 'chapter-deleted', 'list-filtered', 'list-deleted',
                 'list-unanswered', 'item-deleted', 'leaf-filtered', 'leaf-deleted',
                 'wrong-leaf-type', 'km-absent'], ['review', 'submission']):
            km, replies = fixture()
            if change == 'chapter-filtered': km['chapterUuids'].clear()
            if change == 'chapter-deleted': km['entities']['chapters'].clear()
            if change == 'list-filtered': km['entities']['chapters'][IDS['adminDetailsCUuid']]['questionUuids'].clear()
            if change == 'list-deleted': km['entities']['questions'].pop(IDS['projectsQUuid'])
            if change == 'list-unanswered': replies.pop(LISTING)
            if change == 'item-deleted': replies[LISTING] = []
            if change == 'leaf-filtered': km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids'].remove(ACRONYM)
            if change == 'leaf-deleted': km['entities']['questions'].pop(ACRONYM)
            if change == 'wrong-leaf-type': km['entities']['questions'][ACRONYM]['questionType'] = 'OptionsQuestion'
            if change == 'km-absent': km = {}
            soup = render(overview, km, replies, profile)
            assert not soup.select('[data-fact-id="project-acronym"]'), change
            assert 'COAST' not in soup.get_text(), change
            counts['inactive_cases'] += 1

        for profile in ('review', 'submission'):
            km, replies = fixture('FIRST', 'Same name')
            _, other = fixture('SECOND', 'Same name', 'project-b')
            replies.update(other)
            replies[LISTING] = ['project-b', 'project-a']
            replies[path(LISTING, 'deleted', ACRONYM)] = 'STALE'
            soup = render(overview, km, replies, profile)
            assert [p.select_one('[data-fact-id="project-acronym"] td').get_text()
                    for p in soup.select('.project')] == ['SECOND', 'FIRST']
            assert 'STALE' not in soup.get_text()
            counts['identity_cases'] += 1

            full_soup = render(full, km, replies, profile)
            blank = copy.deepcopy(replies)
            for key in list(blank):
                if key.endswith(ACRONYM): blank.pop(key)
            control = render(full, km, blank, profile)
            assert len(full_soup.select('.question')) == 15
            assert len(full_soup.select('.dmp-section')) == 6
            assert [str(q) for q in full_soup.select('.question')] == [str(q) for q in control.select('.question')]
            assert len(full_soup.select('[data-fact-id="project-acronym"]')) == 2
            counts['full_documents'] += 1
    return counts
