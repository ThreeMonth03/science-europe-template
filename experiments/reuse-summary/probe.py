"""Independent public-data oracle for the Q1 summary experiment."""
import copy
import itertools
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from output_profile_contract import environment
from test_answer_retention import IDS, path
from test_structure_bindings import BlockProbe
from probe_pdf_budget_reading import dom

QUESTION = 'src/questions/01-how-data.html.j2'
WRAPPER = ("{% import 'src/macros.html.j2' as macros with context %}"
           "{% import 'src/uuids.j2' as uuids with context %}"
           "{% include 'src/questions/01-how-data.html.j2' %}")
FIELDS = {
    'reuse-scope': ('nrefDataCompleteQUuid', {
        'nrefDataCompleteUseAUuid': 'The project will reuse the complete dataset.',
        'nrefDataCompleteDocumentAUuid': 'The project will reuse a subset of the data and document the filtering or selection process.',
        'nrefDataCompleteSubsetAUuid': 'The project will reuse a selected subset of the data and make it available with the research results.'}),
    'reuse-format': ('nrefDataFormatQUuid', {
        'nrefDataFormatConvertAUuid': 'The data format needs to be converted before reuse.',
        'nrefDataFormatUseAUuid': 'The data can be reused without format conversion.'}),
    'reuse-stability': ('nrefDataFixedQUuid', {
        'nrefDataFixedFixedAUuid': 'The dataset is fixed, so changes to the source data will not affect the reproducibility of the research results.',
        'nrefDataFixedChangeAUuid': 'The dataset may change, which could affect the reproducibility of the research results.'}),
    'reuse-conditions': ('nrefDataConditionsQUuid', {
        'nrefDataConditionsCC0AUuid': 'The dataset is freely available for any use.',
        'nrefDataConditionsCCBYAUuid': 'The dataset is freely available provided that the source is cited.',
        'nrefDataConditionsOtherAUuid': 'Use of this dataset is subject to restrictions, which the project will observe.'}),
}
AUTHORED = '<p>Keep <strong>Original.csv</strong>; v1.2 and 0 GB.</p><p>尚待補充：這是原文。 Do not remove this sentence.</p><ul><li>A &amp; B</li><li><a href="https://example.org/data?a=1&amp;b=2">Source</a></li></ul>'
PRE = path('reusingCUuid', 'preexistingQUuid')
LIST = path(PRE, 'preexistingYesAUuid', 'nrefDataQUuid')
USE = path(LIST, 'sample-1', 'nrefDataUseQUuid')
PREFIX = path(USE, 'nrefDataUseYesAUuid')
DETAIL = path(PREFIX, 'nrefDataConditionsQUuid', 'nrefDataConditionsOtherAUuid', 'nrefDataConditionsOtherQUuid')
OWNED = '.reuse-summary, [data-fact-id="reuse-conditions-detail"]'


def schema():
    e = dict(chapters={}, questions={}, answers={})
    e['chapters'][IDS['reusingCUuid']] = dict(questionUuids=[IDS['preexistingQUuid']])
    for q, a, children in [
        ('preexistingQUuid', 'preexistingYesAUuid', ['nrefDataQUuid']),
        ('nrefDataUseQUuid', 'nrefDataUseYesAUuid', [v[0] for v in FIELDS.values()])]:
        e['questions'][IDS[q]] = dict(questionType='OptionsQuestion', answerUuids=[IDS[a]])
        e['answers'][IDS[a]] = dict(followUpUuids=[IDS[c] for c in children])
    e['questions'][IDS['nrefDataQUuid']] = dict(questionType='ListQuestion', itemTemplateQuestionUuids=[IDS['nrefDataUseQUuid']])
    for question, answers in FIELDS.values():
        e['questions'][IDS[question]] = dict(questionType='OptionsQuestion', answerUuids=[IDS[a] for a in answers])
        for answer in answers:
            e['answers'][IDS[answer]] = dict(followUpUuids=([IDS['nrefDataConditionsOtherQUuid']] if answer == 'nrefDataConditionsOtherAUuid' else []))
    e['questions'][IDS['nrefDataConditionsOtherQUuid']] = dict(questionType='ValueQuestion')
    return dict(chapterUuids=[IDS['reusingCUuid']], entities=e)


def replies(choices=None, detail=AUTHORED):
    choices = choices or [next(iter(answers)) for _, answers in FIELDS.values()]
    values = {PRE: IDS['preexistingYesAUuid'], LIST: ['sample-1'], USE: IDS['nrefDataUseYesAUuid'],
        path(LIST, 'sample-1', 'nrefDataNameQUuid'): 'Public synthetic dataset',
        path(LIST, 'sample-1', 'nrefDataWhereQUuid'): 'https://example.org/data',
        path(PREFIX, 'nrefDataUsageQUuid'): AUTHORED, DETAIL: detail}
    for (question, _), choice in zip(FIELDS.values(), choices):
        if choice is not None: values[path(PREFIX, question)] = IDS.get(choice, choice)
    return values


def check(root, sources, words=None):
    """Checks rendered, optionally translated package files, not guessed HTML."""
    words = words or {}
    translate = lambda text: words.get(text, text)
    overrides = {n: v.decode() if isinstance(v, bytes) else v for n, v in sources.items() if n.endswith('.j2')}
    rows = []
    for escape, profile in itertools.product([False, True], ['review', 'submission']):
        template = environment(root, escape, overrides).from_string(WRAPPER)
        # Independent projection of unchanged Q1: include site stays, new helper is empty.
        control = environment(root, escape, {**overrides, 'src/reuse-summary.html.j2': ''}).from_string(WRAPPER)
        def render(values, km=None):
            raw = template.render(repliesMap=values, km=schema() if km is None else km, output_profile=profile)
            probe = BlockProbe(); probe.feed(raw)
            assert not probe.errors and not probe.stack, (probe.errors, probe.stack)
            return BeautifulSoup(raw, 'html.parser')
        options = [[None, 'unknown', *answers] for _, answers in FIELDS.values()]
        for choices in itertools.product(*options):
            values = replies(choices)
            page = render(values)
            expected = [(fact, translate(answers[choice])) for (fact, (_, answers)), choice in zip(FIELDS.items(), choices) if choice in answers]
            actual = [(s['data-fact-id'], s.get_text()) for s in page.select('.reuse-summary > span')]
            assert actual == expected, (choices, actual, expected)
            paragraphs = page.select('p.reuse-summary')
            assert len(paragraphs) == bool(expected)
            if expected:
                joined = ''.join(text + ('' if index == len(expected) - 1 or text.endswith('。') else ' ') for index, (_, text) in enumerate(expected))
                assert paragraphs[0].get_text() == joined, 'Incorrect sentence boundary spacing'
            details = page.select('[data-fact-id="reuse-conditions-detail"]')
            assert len(details) == (choices[-1] == 'nrefDataConditionsOtherAUuid')
            if details:
                node = copy.deepcopy(details[0]); node.p.decompose()
                assert dom(node) == dom(BeautifulSoup('<div class="answer-detail" data-fact-id="reuse-conditions-detail" data-status="complete">' + AUTHORED + '</div>', 'html.parser').div)
            stripped = copy.deepcopy(page)
            for node in stripped.select(OWNED): node.decompose()
            assert dom(stripped) == dom(BeautifulSoup(control.render(repliesMap=values, km=schema(), output_profile=profile), 'html.parser')), 'Other Q1 content changed'
            rows.append(dict(case='choices', choices=choices, profile=profile, autoescape=escape))
        other = [next(iter(a)) for _, a in FIELDS.values()]; other[-1] = 'nrefDataConditionsOtherAUuid'
        for value in ['', ' \n\t', None, '0', AUTHORED * 30]:
            values = replies(other, value)
            if value is None: values.pop(DETAIL)
            page = render(values)
            detail = page.select_one('[data-fact-id="reuse-conditions-detail"]')
            filled = bool(value and value.strip())
            assert bool(detail) == (filled or profile == 'review')
            if detail:
                assert detail['data-status'] == ('complete' if filled else 'missing')
                if filled:
                    detail.p.decompose()
                    assert dom(detail) == dom(BeautifulSoup('<div class="answer-detail" data-fact-id="reuse-conditions-detail" data-status="complete">' + value + '</div>', 'html.parser').div)
            assert len(page.select('.reuse-summary > span')) == 4
            rows.append(dict(case='detail-' + str([ '', ' \n\t', None, '0', AUTHORED * 30].index(value)), profile=profile, autoescape=escape))
        # Stale descendants cannot survive deselection of either parent.
        for parent in [PRE, USE]:
            for value in [None, 'unknown', IDS['nrefDataUseNoAUuid']]:
                values = replies(other); values[parent] = value
                assert not render(values).select(OWNED)
                rows.append(dict(case='inactive-parent', parent=parent, value=value, profile=profile, autoescape=escape))
        # Every compiled-KM entity and edge used by this block is tested independently.
        base = schema()
        for bucket, entities in base['entities'].items():
            for uid in entities:
                km = copy.deepcopy(base); del km['entities'][bucket][uid]
                page = render(replies(other), km)
                if uid == IDS['nrefDataConditionsOtherQUuid']:
                    assert not page.select('[data-fact-id="reuse-conditions-detail"]')
                    assert len(page.select('.reuse-summary > span')) == 4
                elif uid in [IDS[n] for n in ['reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'nrefDataQUuid', 'nrefDataUseQUuid', 'nrefDataUseYesAUuid']]:
                    assert not page.select(OWNED)
                else:
                    for fact, (question, answers) in FIELDS.items():
                        choice = other[list(FIELDS).index(fact)]
                        assert bool(page.select_one('.reuse-summary > [data-fact-id="' + fact + '"]')) == (uid not in [IDS[question], IDS[choice]])
                rows.append(dict(case='filtered', entity=uid, profile=profile, autoescape=escape))
        for bucket, entities in base['entities'].items():
            for uid, entity in entities.items():
                for key, children in entity.items():
                    if not isinstance(children, list): continue
                    for child in children:
                        km = copy.deepcopy(base); km['entities'][bucket][uid][key].remove(child)
                        # Removing an edge has exactly the same effect as removing its child.
                        missing = copy.deepcopy(base)
                        collection = next(b for b in missing['entities'].values() if child in b); del collection[child]
                        assert dom(render(replies(other), km)) == dom(render(replies(other), missing))
                        rows.append(dict(case='detached-edge', child=child, profile=profile, autoescape=escape))
        for uid, question in base['entities']['questions'].items():
            km = copy.deepcopy(base); km['entities']['questions'][uid]['questionType'] = 'UnsupportedQuestion'
            missing = copy.deepcopy(base); del missing['entities']['questions'][uid]
            assert dom(render(replies(other), km)) == dom(render(replies(other), missing))
            rows.append(dict(case='wrong-type', entity=uid, profile=profile, autoescape=escape))
        km = copy.deepcopy(base); km['chapterUuids'] = []
        assert not render(replies(other), km).select(OWNED)
        # Independent list items, neutral numbering and authored purpose retained.
        values = replies(other); values[LIST] = ['sample-1', 'sample-2']
        values.pop(path(LIST, 'sample-1', 'nrefDataNameQUuid'))
        for key, value in list(values.items()):
            if '.sample-1.' in key: values[key.replace('.sample-1.', '.sample-2.')] = value
        values.pop(path(PREFIX.replace('sample-1', 'sample-2'), 'nrefDataFormatQUuid'))
        page = render(values)
        assert [len(p.select('span')) for p in page.select('.reuse-summary')] == [4, 3]
        assert len(page.select('[data-fact-id="reuse-purpose"]')) == 2
        if profile == 'submission':
            labels = [page.select_one('[data-item-id="' + i + '"] > strong').get_text() for i in ['sample-1', 'sample-2']]
            assert '1' in labels[0] and '2' in labels[1] and labels[0] != labels[1]
            assert not page.select('.data-gap')
        rows.append(dict(case='two-nameless-datasets', profile=profile, autoescape=escape))
    return rows
