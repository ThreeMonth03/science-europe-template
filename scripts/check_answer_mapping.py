"""Focused checks for restored Q1 rights holders and Q4 verification answers.

Synthetic replies only. Can also run against the prepared Chinese source tree;
this checks the translated Jinja, not a separately maintained implementation.
"""
import copy
import itertools

from bs4 import BeautifulSoup
from current_support import IDS, WRAPPER, environment, path

PREFIX = ['10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5',
          '918d5fd1-ea37-468f-8acd-ca3e80203900', '30d1e85c-0e3e-482f-97f9-22a7658b329e']
CHECKS = [
    ('e8a08f27-9f82-4147-b446-822d34a5d468', 'be0761b6-421a-4683-8ff9-de496868feea', '8d038086-a207-46f4-9e7c-180780d9c3a6', 'quality-cross-infrastructure'),
    ('a3a4ce37-4ced-41df-8ec6-e42d87a6a3f1', '4715c145-8e34-45b9-b7c1-77d835d3ade8', '9ffbb7f2-5eb8-455a-bd98-6547887e0eb6', 'quality-automated-workflows'),
    ('34a3ef8b-4a17-4030-9157-ed1c1bf60b80', '56c899c9-fb21-449c-a905-4b9f4fbf6458', 'f14a3135-32d9-4520-bc09-45f50f0c6031', 'quality-independent-verification'),
    ('faf72b3d-ac29-41d1-97f2-5223b199a086', '2c9f5097-34a8-4852-8e10-b26bd71ee1ba', '168ba2ce-e5aa-4dc5-a840-845a5c20058f', 'quality-repeat-subsets'),
]
OWNER = '<p>Example Rights Office — <a href="mailto:rights@example.org">rights@example.org</a></p>'


def schema():
    return dict(chapterUuids=[], entities=dict(chapters={}, questions={}, answers={}))


def chapter(km, uuid):
    km['chapterUuids'].append(uuid)
    return km['entities']['chapters'].setdefault(uuid, dict(questionUuids=[]))['questionUuids']


def question(km, children, uuid, kind, answers=()):
    children.append(uuid)
    result = dict(questionType=kind, answerUuids=list(answers), itemTemplateQuestionUuids=[])
    km['entities']['questions'][uuid] = result
    for answer in answers:
        km['entities']['answers'][answer] = dict(followUpUuids=[])
    return result


def research_fixture(states=('yes',) * 4):
    km = schema()
    question(km, chapter(km, PREFIX[0]), PREFIX[1], 'OptionsQuestion', [PREFIX[2]])
    children = km['entities']['answers'][PREFIX[2]]['followUpUuids']
    replies = {path(*PREFIX[:2]): PREFIX[2]}
    for (uuid, yes, no, _), state in zip(CHECKS, states):
        question(km, children, uuid, 'OptionsQuestion', [yes, no])
        if state != 'missing':
            replies[path(*PREFIX, uuid)] = {'yes': yes, 'no': no, 'unknown': 'obsolete-option'}[state]
    return km, replies


def owner_fixture(kind):
    km = schema()
    question(km, chapter(km, IDS['reusingCUuid']), IDS['preexistingQUuid'],
             'OptionsQuestion', [IDS['preexistingYesAUuid']])
    children = km['entities']['answers'][IDS['preexistingYesAUuid']]['followUpUuids']
    items = question(km, children, IDS[kind + 'DataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, items, IDS[kind + 'DataUseQUuid'], 'OptionsQuestion',
             [IDS[kind + 'DataUseYesAUuid'], IDS[kind + 'DataUseNoAUuid']])
    followups = km['entities']['answers'][IDS[kind + 'DataUseYesAUuid']]['followUpUuids']
    question(km, followups, IDS[kind + 'DataOwnerQUuid'], 'ValueQuestion')
    parent = path('reusingCUuid', 'preexistingQUuid')
    listing = path(parent, 'preexistingYesAUuid', kind + 'DataQUuid')
    use = path(listing, 'dataset-1', kind + 'DataUseQUuid')
    owner = path(use, kind + 'DataUseYesAUuid', kind + 'DataOwnerQUuid')
    replies = {parent: IDS['preexistingYesAUuid'], listing: ['dataset-1'],
               use: IDS[kind + 'DataUseYesAUuid'], owner: OWNER}
    return km, replies, (parent, listing, use, owner)


def check(root, language="en"):
    counts = dict(research_combinations=0, inactive_branches=0, owner_cases=0, full_documents=0, authorization_cases=0)
    for escape in (False, True):
        env = environment(root, escape)
        wrap = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}"
        quality = env.from_string(wrap + "{% include 'src/questions/04-quality-control.html.j2' %}")
        reuse = env.from_string(wrap + "{% include 'src/questions/01-how-data.html.j2' %}")
        full = env.from_string(WRAPPER)

        legal = env.from_string(wrap + "{% include 'src/questions/08-copyright-ipr.html.j2' %}{% include 'src/questions/10-share-restrictions.html.j2' %}")
        parent = path('accessCUuid', 'openImmediatelyQUuid')
        reason = path(parent, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        authenticated = path(reason, 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid')
        authorization = path(authenticated, 'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthorizeQUuid')
        detail = path(authorization, 'legalReasonsAuthorizeOtherAUuid', 'legalReasonsAuthorizeOtherQUuid')
        committee = path(authorization, 'legalReasonsAuthorizeOldCommitteeAUuid', 'legalReasonsAuthorizeOldCommitteeQUuid')
        base = {parent: IDS['openImmediatelyNoAUuid'], reason: IDS['notOpenLegalReasonsYesAUuid'],
                authenticated: IDS['legalReasonsAuthenticatedYesAUuid']}
        authored = '<p>Access office: <em>Coast A</em>.</p><p>Retain original notes.</p>'
        for choice, value, profile in itertools.product(
                ['Member', 'NewCommittee', 'OldCommittee', 'Other', None, 'obsolete'],
                ['', '  \n ', authored, authored * 40,
                 '<ul><li>Access office: Coast A.</li><li>Keep the original decision.</li></ul>',
                 '<table><tr><th>Office</th><th>Record</th></tr><tr><td>Access office: Coast A.</td><td>access.csv</td></tr></table>'],
                ['review', 'submission']):
            replies = dict(base); replies[detail] = replies[committee] = value
            if choice: replies[authorization] = IDS.get('legalReasonsAuthorize'+choice+'AUuid', choice)
            soup = BeautifulSoup(legal.render(repliesMap=replies, output_profile=profile), 'html.parser')
            q8 = soup.select_one('#q-copyright-ipr')
            known = choice in ['Member', 'NewCommittee', 'OldCommittee', 'Other']
            assert len(q8.select('[data-fact-id="authorization-arrangements"]')) == int(known)
            assert len(q8.select('[data-fact-id="authorization-details"]')) == int(choice == 'Other' and not value.strip() and profile == 'review')
            assert '尚未決定授權安排' not in q8.get_text() and 'not yet decided on the authorization' not in q8.get_text()
            assert ('Access office:' in q8.get_text()) == (choice in ['Other', 'OldCommittee'] and bool(value.strip()))
            q10 = soup.select_one('#q-share-restrictions')
            body = q10.select_one('.authorization-details')
            has_detail = choice in ['Other', 'OldCommittee'] and bool(value.strip())
            assert bool(body) == has_detail
            assert bool(q10.select('.answer-lead > [data-fact-id="authenticated-access"]')) == has_detail
            assert not q10.select('p p,p div,p ul,p table,em p')
            if has_detail:
                assert body.decode_contents() == value
                assert body.find_previous_sibling('div')['class'] == ['answer-lead']
            elif choice == 'Other':
                lead = q10.select_one('[data-fact-id="authenticated-access"]')
                assert lead.get_text().strip().endswith('.' if language == 'en' else '。')
            if language == 'en' and choice == 'OldCommittee' and not value.strip():
                lead = q10.select_one('[data-fact-id="authenticated-access"]')
                assert 'required. People can apply' in ' '.join(lead.get_text().split())
            if choice == 'Other':
                if value.strip():
                    for p in BeautifulSoup(value, 'html.parser').select('p'): assert str(p) in str(q8)
                else:
                    expected = 'We will make other arrangements for authorizing potential users.' if language == 'en' else '本計畫將採用其他方式，辦理潛在資料使用者的授權。'
                    assert expected in q8.get_text()
            if profile == 'submission': assert not q8.select('.data-gap,.data-review')
            counts['authorization_cases'] += 1
        negatives = {parent: IDS['openImmediatelyYesAUuid'], reason: IDS['notOpenLegalReasonsNoAUuid'],
                     authenticated: 'da8b25a9-8865-4ce8-a2ba-d592c42daa4c'}  # KM 2.7.0: authenticated access = No
        for key, value, profile in itertools.product([parent, reason, authenticated],
                [None, 'negative', 'obsolete-option'], ['review', 'submission']):
            replies = dict(base); replies[authorization] = IDS['legalReasonsAuthorizeOtherAUuid']; replies[detail] = authored
            if value is None: replies.pop(key)
            else: replies[key] = negatives[key] if value == 'negative' else value
            soup = BeautifulSoup(legal.render(repliesMap=replies, output_profile=profile), 'html.parser')
            assert not soup.select('[data-fact-id="authorization-arrangements"],[data-fact-id="authorization-details"],[data-fact-id="authenticated-access"]')
            assert 'Access office:' not in soup.get_text()
            counts['authorization_cases'] += 1

        def render(template, km, replies, profile):
            return BeautifulSoup(template.render(km=km, repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')

        for states in itertools.product(('yes', 'no', 'missing', 'unknown'), repeat=4):
            km, replies = research_fixture(states)
            for profile in ('review', 'submission'):
                soup = render(quality, km, replies, profile)
                assert not soup.select('[data-status="missing-output"]')
                assert len(soup.select('.research-quality > p')) == int(any(s in ('yes', 'no') for s in states))
                for (_, _, _, fact), state in zip(CHECKS, states):
                    nodes = soup.select(f'[data-fact-id="{fact}"]')
                    expected = state in ('yes', 'no') or profile == 'review'
                    assert len(nodes) == int(expected), (escape, profile, states, fact)
                    if expected:
                        assert nodes[0]['data-status'] == dict(yes='complete', no='explicit-no', missing='missing', unknown='needs-review')[state]
                        assert nodes[0].get_text().strip()
                if profile == 'submission':
                    assert not soup.select('.data-gap')
                counts['research_combinations'] += 1

        for change in ('parent-unanswered', 'parent-changed', 'chapter-filtered', 'leaf-filtered', 'answer-deleted'):
            km, replies = research_fixture()
            if change == 'parent-unanswered': replies.pop(path(*PREFIX[:2]))
            if change == 'parent-changed': replies[path(*PREFIX[:2])] = 'different-answer'
            if change == 'chapter-filtered': km['chapterUuids'].clear()
            if change == 'leaf-filtered': km['entities']['answers'][PREFIX[2]]['followUpUuids'].remove(CHECKS[0][0])
            if change == 'answer-deleted': km['entities']['answers'].pop(CHECKS[0][1])
            soup = render(quality, km, replies, 'submission')
            facts = soup.select('.research-quality [data-fact-id]')
            assert len(facts) == (3 if change in ('leaf-filtered', 'answer-deleted') else 0), change
            counts['inactive_branches'] += 1

        for kind in ('ref', 'nref'):
            for change in ('none', 'blank-owner', 'parent-unanswered', 'use-no', 'item-deleted', 'owner-filtered'):
                for profile in ('review', 'submission'):
                    km, replies, (parent, listing, use, owner) = owner_fixture(kind)
                    if change == 'blank-owner': replies[owner] = '  \n '
                    if change == 'parent-unanswered': replies.pop(parent)
                    if change == 'use-no': replies[use] = IDS[kind + 'DataUseNoAUuid']
                    if change == 'item-deleted': replies[listing] = []
                    if change == 'owner-filtered': km['entities']['answers'][IDS[kind + 'DataUseYesAUuid']]['followUpUuids'].clear()
                    soup = render(reuse, km, replies, profile)
                    holders = soup.select('[data-fact-id="reuse-rightsholder"]')
                    assert len(holders) == int(change == 'none'), (kind, profile, change)
                    if holders:
                        assert str(holders[0].select('p')[-1]) == str(BeautifulSoup(OWNER, 'html.parser').p)
                        if profile == 'submission':
                            label = soup.select_one('.dataset-label')
                            assert label and label['data-list-index'] == '1'
                            assert not soup.select('.data-gap')
                    counts['owner_cases'] += 1

        for profile in ('review', 'submission'):
            km, replies = research_fixture(('yes', 'missing', 'no', 'unknown'))
            for kind in ('ref', 'nref'):
                extra, more, _ = owner_fixture(kind)
                if extra['chapterUuids'][0] not in km['chapterUuids']:
                    km['chapterUuids'] += extra['chapterUuids']
                    km['entities']['chapters'].update(extra['entities']['chapters'])
                for entity_kind in ('questions', 'answers'):
                    for uuid, item in extra['entities'][entity_kind].items():
                        if entity_kind == 'answers' and uuid in km['entities']['answers']:
                            km['entities']['answers'][uuid]['followUpUuids'] += item['followUpUuids']
                        else: km['entities'][entity_kind][uuid] = copy.deepcopy(item)
                replies.update(more)
            soup = render(full, km, replies, profile)
            assert len(soup.select('.question')) == 15
            assert len(soup.select('.dmp-section')) == 6
            assert len(soup.select('[data-fact-id="reuse-rightsholder"]')) == 2
            assert len(soup.select('.research-quality [data-fact-id]')) == 2
            assert not soup.select('p p, p div, p ul, p table')
            if profile == 'submission': assert not soup.select('.data-gap')
            counts['full_documents'] += 1
    return counts
