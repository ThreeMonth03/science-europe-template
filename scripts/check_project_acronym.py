"""Bounded bilingual checks for project identity, metadata and partial funding."""
import copy
import itertools

from bs4 import BeautifulSoup
from check_answer_mapping import chapter, question, schema
from current_support import PREFIX, IDS, WRAPPER, environment, path

ACRONYM = '5b765df9-299f-4855-9e99-aa844903f8f6'
LISTING = path('adminDetailsCUuid', 'projectsQUuid')
LABELS = {'en': 'Project acronym', 'zh-Hant': '計畫簡稱'}
FUNDING_STATUS = {'en': dict(Planned='(planned)', Applied='(applied)', Granted='(granted)', Rejected='(rejected)'),
                  'zh-Hant': dict(Planned='（規劃中）', Applied='（已申請）', Granted='（已核准）', Rejected='（未核准）')}
METADATA = dict(projectNumberQUuid='project-number', projectStartQUuid='project-start', projectEndQUuid='project-end')
DOCUMENT_NAME = 'DMP <2026> & "B"'


def integration(value='', raw=None, plain=True):
    return {'value': {'value': {'type': 'PlainType' if plain else 'IntegrationType', 'value': value, 'raw': raw}}}


def funding_fixture(name=None, grant=None, status=None):
    km, replies = fixture(None)
    children = km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids']
    children = question(km, children, IDS['fundersQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, IDS['funderNameQUuid'], 'IntegrationQuestion')
    question(km, children, IDS['grantNumberQUuid'], 'ValueQuestion')
    question(km, children, IDS['funderStatusQUuid'], 'OptionsQuestion',
             [IDS['funderStatus'+option+'AUuid'] for option in FUNDING_STATUS['en']])
    listing = path(LISTING, 'project-a', 'fundersQUuid')
    replies[listing] = ['funder-a']
    for field, value in [('funderNameQUuid', name), ('grantNumberQUuid', grant),
                         ('funderStatusQUuid', IDS.get('funderStatus'+str(status)+'AUuid', status))]:
        if value is not None: replies[path(listing, 'funder-a', field)] = value
    return km, replies, listing


def fixture(acronym='COAST', name='Coastal observation', item='project-a'):
    km = schema()
    children = question(km, chapter(km, IDS['adminDetailsCUuid']),
                        IDS['projectsQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, ACRONYM, 'ValueQuestion')
    question(km, children, IDS['projectNameQUuid'], 'ValueQuestion')
    for field in [*METADATA, 'projectAbstractQUuid']:
        question(km, children, IDS[field], 'ValueQuestion')
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
    assert 'html body #dmp-projects .project-funding { overflow-wrap: anywhere; word-break: break-word; }' in css
    for selector in ['.document-heading h1', '.document-heading .document-meta', '#dmp-projects > .project > h3',
                     '.ethical-project-summary > strong', '#q-required-resources .project-resources > p:first-child > strong']:
        assert 'html body '+selector in css
    counts = dict(value_cases=0, inactive_cases=0, identity_cases=0, full_documents=0,
                  funding_cases=0, inactive_funding=0, funding_identity=0,
                  project_values=0, project_titles=0, project_subsets=0,
                  inactive_overview=0, header_metadata=0, project_identity=0, budget_identity=0)
    for escape in (False, True):
        env = environment(root, escape)
        env.filters['datetime_format'] = lambda value, fmt: '2026-09-30'
        overview = env.from_string(PREFIX + "{% include 'src/projects.html.j2' %}")
        full = env.from_string(WRAPPER)
        headed = env.from_string(PREFIX + "{% include 'src/frontmatter.html.j2' %}{% include 'src/projects.html.j2' %}")

        def render(template, km, replies, profile, dc=None, ctx=None):
            soup = BeautifulSoup(template.render(km=km, repliesMap=replies,
                output_profile=profile, dc=dc or {'project': {'created_by': None, 'name': DOCUMENT_NAME, 'versions': []},
                    'document': {'created_at': ''}, 'e': {'choices': {}}},
                ctx=ctx or {'phaseUuid': None, 'project': {'versionUuid': None}}), 'html.parser')
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

        label, uri = 'Agency <A> & "B"', 'https://example.org/funder?id=1&group=B'
        names = [(None, '', None), (integration(''), '', None), (integration(' \n '), '', None),
                 (integration(label), label, None),
                 (integration(raw=dict(name=label, uri=uri), plain=False), label, uri),
                 (integration(raw=dict(name=label), plain=False), label, None),
                 (integration(raw=dict(uri=uri), plain=False), uri, uri),
                 (integration(raw=dict(name=' ', uri=' '), plain=False), '', None),
                 (integration(label, plain=False), label, None)]
        for (name, expected, link), grant, status, profile in itertools.product(
                names, [None, '', ' \n ', 'GRANT <A> & "B"', '0'],
                [None, 'unknown', *FUNDING_STATUS[language]], ['review', 'submission']):
            km, replies, listing = funding_fixture(name, grant, status)
            soup = render(overview, km, replies, profile)
            rows = soup.select('[data-fact-id="project-funding"] li')
            funding = soup.select_one('[data-fact-id="project-funding"]')
            if funding:
                assert funding.name == 'div' and funding.h4 is not None
                assert funding.find_parent('table') is None, 'Funding must flow outside the metadata table'
            visible = profile == 'review' or bool(expected or (grant or '').strip() or status in FUNDING_STATUS[language])
            assert len(rows) == int(visible)
            if visible:
                text = rows[0].get_text().strip()
                number = grant if (grant or '').strip() else ('grant number not yet given' if language=='en' else '尚未提供補助編號') if profile=='review' else ''
                separator = ': ' if language == 'en' else '：'
                wanted = expected + (separator if expected and number else '') + number
                if status in FUNDING_STATUS[language]: wanted += ' ' + FUNDING_STATUS[language][status]
                assert text == wanted.strip(), (text, wanted)
                assert [a['href'] for a in rows[0].select('a')] == ([link] if link else [])
                assert not rows[0].select('b, img, script'), 'Funding fields are text, not HTML'
            if profile == 'submission':
                assert not soup.select('table.project-details')
                assert bool(soup.select('[data-fact-id="project-funding"]')) == visible
            assert not soup.select('ul:empty, li:empty')
            counts['funding_cases'] += 1

        for change, profile in itertools.product(
                ['chapter', 'list', 'project', 'entry', 'name', 'grant', 'status', 'option', 'answer'],
                ['review', 'submission']):
            km, replies, listing = funding_fixture(integration(label), 'G <A>', 'Granted')
            questions, answers = km['entities']['questions'], km['entities']['answers']
            if change=='chapter': km['chapterUuids'].clear()
            elif change=='list': questions[IDS['projectsQUuid']]['itemTemplateQuestionUuids'].remove(IDS['fundersQUuid'])
            elif change=='project': replies[LISTING] = []
            elif change=='entry': replies[listing] = []
            elif change in ['name','grant','status']:
                field = dict(name='funderNameQUuid', grant='grantNumberQUuid', status='funderStatusQUuid')[change]
                questions[IDS['fundersQUuid']]['itemTemplateQuestionUuids'].remove(IDS[field])
            elif change=='option': questions[IDS['funderStatusQUuid']]['answerUuids'].remove(IDS['funderStatusGrantedAUuid'])
            elif change=='answer': answers.pop(IDS['funderStatusGrantedAUuid'])
            soup = render(overview, km, replies, profile)
            text = soup.get_text()
            active = change not in ['chapter','list','project','entry']
            assert (label in text) == (active and change!='name')
            assert ('G <A>' in text) == (active and change!='grant')
            assert (FUNDING_STATUS[language]['Granted'] in text) == (active and change not in ['status','option','answer'])
            counts['inactive_funding'] += 1

        for profile in ['review','submission']:
            km, replies, listing = funding_fixture(integration(label), 'FIRST', 'Applied')
            replies[listing] = ['empty-before', 'funder-a', 'grant-only', 'same-name', 'empty-after']
            replies[path(listing, 'grant-only', 'grantNumberQUuid')] = 'SECOND'
            replies[path(listing, 'same-name', 'funderNameQUuid')] = integration(label)
            replies[path(listing, 'deleted', 'grantNumberQUuid')] = 'STALE'
            soup = render(full, km, replies, profile)
            rows = soup.select('[data-fact-id="project-funding"] li')
            expected = replies[listing] if profile=='review' else ['funder-a','grant-only','same-name']
            assert [row['data-item-id'] for row in rows] == expected
            assert 'STALE' not in soup.get_text() and 'SECOND' in soup.get_text()
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            blank = copy.deepcopy(replies); blank[listing] = []
            control = render(full, km, blank, profile)
            assert [str(q) for q in soup.select('.question')] == [str(q) for q in control.select('.question')]
            counts['funding_identity'] += 1

        values = [None, '', ' \n\t ', '0', 'N/A', 'REF <A> & "B"', '2026-01-01', 'TOKEN-'+'1234567890'*18]
        for field, value, profile in itertools.product(METADATA, values, ['review', 'submission']):
            km, replies = fixture(None)
            if value is not None: replies[path(LISTING, 'project-a', field)] = value
            soup = render(overview, km, replies, profile)
            cell = soup.select_one('[data-fact-id="'+METADATA[field]+'"] td')
            visible = bool((value or '').strip())
            assert bool(cell) == (visible or profile=='review')
            if cell:
                assert cell.get_text() == (value if visible else 'N/A' if language=='en' else '尚未提供')
                assert cell.find(True) is None
            counts['project_values'] += 1

        names = [None, '', ' \n\t ', '0', 'N/A', 'Coast <A> & "B"', DOCUMENT_NAME, 'Coastal研究'*30]
        for name, multiple, profile in itertools.product(names, [False, True], ['review', 'submission']):
            km, replies = fixture(None, name)
            if multiple:
                replies[LISTING].append('project-b')
                replies[path(LISTING, 'project-b', 'projectNameQUuid')] = 'SECOND'
            soup = render(headed, km, replies, profile)
            visible = bool((name or '').strip())
            assert soup.h1.get_text() == (name if visible and not multiple else DOCUMENT_NAME)
            assert soup.h1.find(True) is None
            heading = soup.select_one('.project h3')
            if multiple and visible: assert heading.get_text() == name and heading.find(True) is None
            elif not visible:
                assert heading.get_text().strip() == (('Project 1' if language=='en' else '計畫 1') if profile=='submission' else ('(project name not given)' if language=='en' else '（尚未提供專案名稱）'))
            else: assert heading is None
            assert DOCUMENT_NAME in soup.header.get_text()
            counts['project_titles'] += 1

        for states, profile in itertools.product(itertools.product([False, True], repeat=3), ['review','submission']):
            km, replies = fixture(None)
            for field, filled in zip(METADATA, states): replies[path(LISTING,'project-a',field)] = '0' if filled else ' \n '
            soup = render(overview, km, replies, profile)
            assert len(soup.select('.project-details tr')) == (sum(states) if profile=='submission' else 3)
            assert bool(soup.select('.project-details')) == (any(states) or profile=='review')
            counts['project_subsets'] += 1

        for field, change, profile in itertools.product([*METADATA,'projectNameQUuid','projectAbstractQUuid'],
                ['parent','entry','field','deleted','type'], ['review','submission']):
            km, replies = fixture(None)
            replies[path(LISTING,'project-a',field)] = 'STALE-ANSWER'
            questions = km['entities']['questions']
            if change=='parent': km['entities']['chapters'][IDS['adminDetailsCUuid']]['questionUuids'].clear()
            elif change=='entry': replies[LISTING] = []
            elif change=='field': questions[IDS['projectsQUuid']]['itemTemplateQuestionUuids'].remove(IDS[field])
            elif change=='deleted': questions.pop(IDS[field])
            elif change=='type': questions[IDS[field]]['questionType'] = 'OptionsQuestion'
            soup = render(headed, km, replies, profile)
            assert 'STALE-ANSWER' not in soup.get_text(), (field, change)
            counts['inactive_overview'] += 1

        for known_phase, profile in itertools.product([False,True], ['review','submission']):
            km, replies = fixture(None)
            phase, version = 'Phase <A> & B', 'Version <A> & B'
            km['entities']['phases'] = {'phase-a': {'title': phase}} if known_phase else {}
            dc = dict(project=dict(name=DOCUMENT_NAME, versions=[dict(uuid='version-a',name=version,created_at=''),
                dict(uuid='old',name='STALE-VERSION',created_at='')]), document=dict(created_at=''))
            soup = render(headed, km, replies, profile, dc, dict(phaseUuid='phase-a',project=dict(versionUuid='version-a')))
            assert version in soup.header.get_text() and 'STALE-VERSION' not in soup.get_text()
            assert (phase in soup.header.get_text()) == known_phase
            assert not soup.header.select('a, b, img, script')
            counts['header_metadata'] += 1

        for profile in ['review','submission']:
            km, replies = fixture(None, 'Same <name>', 'project-b')
            replies[LISTING] = ['blank', 'project-b', 'project-a']
            replies[path(LISTING,'project-b','projectNumberQUuid')] = 'SECOND'
            replies[path(LISTING,'project-a','projectNameQUuid')] = 'Same <name>'
            replies[path(LISTING,'project-a','projectNumberQUuid')] = 'THIRD'
            replies[path(LISTING,'project-a','projectAbstractQUuid')] = '<p>Keep <em>authored formatting</em>.</p>'
            replies[path(LISTING,'deleted','projectNameQUuid')] = 'STALE-DELETED'
            soup = render(full, km, replies, profile)
            assert [p['data-item-id'] for p in soup.select('.project')] == replies[LISTING]
            assert soup.select_one('.abstract em').get_text() == 'authored formatting'
            assert 'SECOND' in soup.get_text() and 'THIRD' in soup.get_text() and 'STALE-DELETED' not in soup.get_text()
            blank = copy.deepcopy(replies)
            for key in list(blank):
                if key.split('.')[-1] in {IDS[field] for field in ['projectStartQUuid','projectEndQUuid','projectAbstractQUuid']}: blank.pop(key)
            control = render(full, km, blank, profile)
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            assert [str(q) for q in soup.select('.question')] == [str(q) for q in control.select('.question')]
            counts['project_identity'] += 1

        budget = env.from_string(PREFIX + "{% include 'src/questions/15-required-resources.html.j2' %}")
        for name, number, change, profile in itertools.product([None,' \n ','Coast <A>'], [None,' \n ','ID <B>'],
                ['active','name','number','project'], ['review','submission']):
            km, replies = fixture(None, name)
            replies[LISTING] = ['blank','project-a']
            replies[path(LISTING,'project-a','costQUuid')] = ['cost-a']
            if number is not None: replies[path(LISTING,'project-a','projectNumberQUuid')] = number
            if change in ['name','number']:
                field = 'projectNameQUuid' if change=='name' else 'projectNumberQUuid'
                km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids'].remove(IDS[field])
            elif change=='project': km['chapterUuids'].clear()
            soup = render(budget, km, replies, profile)
            label = soup.select_one('.project-resources[data-item-id="'+path(LISTING,'project-a')+'"] > p > strong')
            if change=='project': assert not soup.select('.project-resources')
            else:
                missing = ('Project 2' if language=='en' else '計畫 2') if profile=='submission' else ('(no name given)' if language=='en' else '（計畫名稱尚未提供）')
                expected = name if (name or '').strip() and change!='name' else missing
                if (number or '').strip() and change!='number': expected += ' - '+number
                assert label.get_text().strip() == expected, (label.get_text(), expected)
                assert label.find(True) is None
            counts['budget_identity'] += 1
    return counts
