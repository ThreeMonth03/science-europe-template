"""Synthetic branch tests, reusable against actual EN and translated packages."""
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

FACTS = {
    'project-file-naming': ('q-docs-metadata', 'SE-2a',
        'b1df3c74-0b1f-4574-81c4-4cc2d780c1af.8e886b55-3287-48e7-b353-daf6ab40f7d8.c05f27a2-30ac-44fd-9ac9-cd6f62b16d0c.d4fe0b55-4aee-4d05-88d4-a3f4cad2cfa9.8b13234e-879b-4221-be12-4df24e6de00e.9ff389f0-2236-48cf-880c-040ea1bb0d2f'),
    'reference-data-publication-schedule': ('q-share-restrictions', 'SE-5a',
        'd5b27482-b598-4b8c-b534-417d4ad27394.588ad032-56ba-4d52-b29c-6a5b56aa6569.bdf55011-db06-4f4a-b26f-ebbbe029da04.2679736a-800e-4eaa-a70f-818070540c48'),
    'reference-data-maintenance': ('q-data-preservation', 'SE-5b',
        'd5b27482-b598-4b8c-b534-417d4ad27394.588ad032-56ba-4d52-b29c-6a5b56aa6569.bdf55011-db06-4f4a-b26f-ebbbe029da04.27769a31-717b-4204-8468-175ac93b195a'),
}
AUTHORED = '<p>Keep <strong>Original.csv</strong>; 0 GB. 尚待補充 is authored text.</p><p>Second paragraph: <a href="https://example.org/data?a=1&amp;b=2">Release A</a>.</p><ul><li>Do not invent a deadline.</li></ul>'


def schema():
    """Minimal public-UUID fixture, not a copy of any user's KM or replies."""
    km = dict(chapterUuids=[], entities=dict(chapters={}, questions={}, answers={}))
    e = km['entities']
    for _, _, path in FACTS.values():
        chapter, *parts = path.split('.')
        if chapter not in km['chapterUuids']: km['chapterUuids'].append(chapter)
        c = e['chapters'].setdefault(chapter, dict(questionUuids=[]))
        if parts[0] not in c['questionUuids']: c['questionUuids'].append(parts[0])
        for index in range(0, len(parts) - 1, 2):
            q, a, child = parts[index:index + 3]
            e['questions'][q] = dict(questionType='OptionsQuestion', answerUuids=[a])
            answer = e['answers'].setdefault(a, dict(followUpUuids=[]))
            if child not in answer['followUpUuids']: answer['followUpUuids'].append(child)
        e['questions'][parts[-1]] = dict(questionType='ValueQuestion')
    return km


def replies(value=AUTHORED):
    result = {}
    for _, _, path in FACTS.values():
        parts = path.split('.')
        for index in range(2, len(parts), 2): result['.'.join(parts[:index])] = parts[index]
        result[path] = value
    return result


def verify_public_bindings(bundle):
    """Track only the declared entities' parents/types through public KM events.

    Not a general KM compiler. Reject unexpected structural operations, and
    verify every ancestor edge after all package versions, including moves.
    """
    wanted = {part for _, _, p in FACTS.values() for part in p.split('.')}
    parents, kinds = {}, {}
    for package in json.loads(bundle.read_text())['packages']:
        for event in package['events']:
            uid = event['entityUuid']
            if uid not in wanted: continue
            content = event['content']; kind = content['eventType']
            if kind.startswith('Add'):
                parents[uid] = event['parentUuid']
                kinds[uid] = content.get('questionType', kind)
            elif kind.startswith('Move'):
                parents[uid] = content['targetUuid']
            elif kind.startswith('Delete'):
                parents.pop(uid, None); kinds.pop(uid, None)
            elif kind.startswith('Edit'):
                field = content.get('questionType')
                if field is not None:
                    if isinstance(field, str): kinds[uid] = field
                    else:
                        assert isinstance(field, dict) and 'changed' in field
                        if field['changed']: kinds[uid] = field['value']
            else:
                raise AssertionError(('Unknown structural operation', kind))
    for _, _, path in FACTS.values():
        parts = path.split('.')
        assert kinds[parts[0]] == 'AddChapterEvent'
        for parent, child in zip(parts, parts[1:]): assert parents[child] == parent, child
        for question in parts[1:-1:2]: assert kinds[question] == 'OptionsQuestion'
        assert kinds[parts[-1]] == 'ValueQuestion'


def check(root, sources, baseline=None):
    """No real project answers; test both profiles and exact authored DOM."""
    overrides = {n: v.decode() if isinstance(v, bytes) else v for n, v in sources.items() if n.endswith('.j2')}
    rows = []
    for escape, profile in itertools.product([False, True], ['review', 'submission']):
        env = environment(root, escape, overrides)
        template = env.from_string(WRAPPER)
        render = lambda km, values: BeautifulSoup(template.render(km=km, repliesMap=values,
            dc={'project': {'created_by': None}, 'e': {'choices': {}}}, output_profile=profile), 'html.parser')
        km = schema()
        complete = render(km, replies())
        assert len(complete.select('.question')) == 15 and len(complete.select('.dmp-section')) == 6
        assert not complete.select('p p, p div, p ul, p table')
        for fact, (question, requirement, path) in FACTS.items():
            parts = path.split('.')
            for value in [AUTHORED, '0', '', ' \t\n ', None]:
                values = replies(); values[path] = value
                if value is None: values.pop(path)
                page = render(km, values)
                matches = page.select('[data-fact-id="' + fact + '"]')
                filled = bool(value and value.strip())
                assert len(matches) == (1 if filled or profile == 'review' else 0)
                if matches:
                    node = matches[0]
                    assert node.find_parent(id=question) is not None
                    if filled:
                        assert node.find_parent(attrs={'data-requirement-id': requirement}) is not None
                        expected = BeautifulSoup('<div class="answer-detail" data-fact-id="' + fact + '">' + value + '</div>', 'html.parser').div
                        assert dom(node) == dom(expected), 'Authored markup or punctuation changed'
                    else: assert node['data-status'] == 'missing'
                rows.append(dict(fact=fact, case='value-' + str([AUTHORED, '0', '', ' \t\n ', None].index(value)), profile=profile, autoescape=escape))
            # Each missing/unknown/unselected ancestor must hide its stale child.
            for index in range(2, len(parts), 2):
                parent = '.'.join(parts[:index])
                for selected in [None, 'unknown', 'explicit-other-choice']:
                    values = replies(); values[parent] = selected
                    if selected is None: values.pop(parent)
                    page = render(km, values)
                    assert not page.select('[data-fact-id="' + fact + '"]')
                    rows.append(dict(fact=fact, case='inactive-parent-' + str(index) + '-' + str(selected), profile=profile, autoescape=escape))
            # A filtered entity, detached edge, wrong type or chapter is not a gap.
            for missing in parts:
                altered = copy.deepcopy(km)
                bucket = next(b for b in altered['entities'].values() if missing in b)
                del bucket[missing]
                assert not render(altered, replies()).select('[data-fact-id="' + fact + '"]')
                rows.append(dict(fact=fact, case='filtered-' + missing, profile=profile, autoescape=escape))
            for question in parts[1::2]:
                altered = copy.deepcopy(km)
                altered['entities']['questions'][question]['questionType'] = 'ListQuestion'
                assert not render(altered, replies()).select('[data-fact-id="' + fact + '"]')
                rows.append(dict(fact=fact, case='wrong-type-' + question, profile=profile, autoescape=escape))
            altered = copy.deepcopy(km); altered['chapterUuids'].remove(parts[0])
            assert not render(altered, replies()).select('[data-fact-id="' + fact + '"]')
            for index in range(1, len(parts)):
                altered = copy.deepcopy(km); e = altered['entities']
                parent, child = parts[index-1:index+1]
                bucket, field = ('chapters', 'questionUuids') if index == 1 else (
                    ('questions', 'answerUuids') if index % 2 == 0 else ('answers', 'followUpUuids'))
                e[bucket][parent][field].remove(child)
                assert not render(altered, replies()).select('[data-fact-id="' + fact + '"]')
                rows.append(dict(fact=fact, case='detached-edge-' + str(index), profile=profile, autoescape=escape))
        # Different questions/fields cannot gate each other.
        for retained in FACTS:
            values = replies()
            for fact, (_, _, path) in FACTS.items():
                if fact != retained: values.pop(path)
            assert render(km, values).select_one('.answer-detail[data-fact-id="' + retained + '"]')
        from test_answer_retention import IDS, path as binding_path
        old_parent = binding_path('processingCUuid', 'storageConvQUuid')
        filesystem = binding_path(old_parent, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
        values = replies()
        values.update({old_parent: IDS['storageConvExploreAUuid'], filesystem: IDS['storageConvFSysYesAUuid'],
            binding_path(filesystem, 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid'): '<p>Storage-specific: KEEP_CASE.csv.</p>'})
        page = render(km, values)
        assert 'KEEP_CASE.csv' in page.select_one('[data-fact-id="file-naming"]').get_text()
        assert 'Original.csv' in page.select_one('[data-fact-id="project-file-naming"]').get_text()
        rows.append(dict(case='both-file-naming-branches-retained', profile=profile, autoescape=escape))
        if baseline:
            before_env = environment(root, escape, {n: v.decode() for n, v in baseline.items() if n.endswith('.j2')})
            before = before_env.from_string(WRAPPER)
            # Existing public cases and older storage/naming branch are unchanged.
            for fixture in sorted((ROOT / 'fixtures/pilot/en').glob('*.events.json')):
                events = json.loads(fixture.read_text())
                values = {e['path']: ({'value': {'value': e['value']['value']}}
                    if e['value']['type'] == 'IntegrationReply' else e['value']['value']) for e in events}
                a = BeautifulSoup(before.render(km=km, repliesMap=values, dc={'project': {'created_by': None}, 'e': {'choices': {}}}, output_profile=profile), 'html.parser')
                b = render(km, values)
                assert dom(a) == dom(b), fixture.name
                rows.append(dict(case='baseline-' + fixture.name, profile=profile, autoescape=escape))
    return rows
