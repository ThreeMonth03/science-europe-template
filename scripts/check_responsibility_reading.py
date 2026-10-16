"""Check per-person responsibility prose in either prepared language tree."""
import itertools

from bs4 import BeautifulSoup
from current_support import PREFIX, IDS, WRAPPER, environment, path

ROLE_NAMES = ['DataCurator', 'DataCollector', 'DataManager', 'DataSteward',
              'Distributor', 'DataProtector', 'CreatorOfDMP']
ROLES = [IDS['contributorRole' + role + 'AUuid'] for role in ROLE_NAMES]
CONTACT = '2c6ee59d-4dc9-4dcb-ac13-d969c317a117'
# Public Common DSW KM 2.7.0 choice labels, as supplied by the worker's dc.e.choices.
ROLE_LABELS = {
    'en': ['Data Curator', 'Data Collector', 'Data Manager', 'Data Steward',
           'Distributor', 'Data Protection Officer', 'Creator of DMP', 'Contact Person'],
    'zh-Hant': ['資料策展人', '資料蒐集者', '資料管理者', '資料託管員',
                '發布者', '資料保護官', '資料管理方案創作者', '聯絡人'],
}
SENTENCES = {
    'en': [
        '{actor} is responsible for reviewing, enhancing, cleaning or standardizing metadata and associated data submitted to a data centre or repository for storage, use and maintenance.',
        '{actor} is responsible for finding, gathering and collecting data.',
        '{actor} is responsible for maintaining the completed resource.',
        '{actor} is responsible for managing data and supporting its effective use, including data processing, policies, guidelines and availability.',
        '{actor} is responsible for producing and disseminating electronic or print copies of the resource.',
        '{actor} is responsible for addressing personal-data protection and data-protection policies.',
        '{actor} is a creator of the data management plan.',
    ],
    'zh-Hant': [
        '{actor}負責審查、補充、清理或標準化提交至資料中心或儲存庫的後設資料及相關資料，以供儲存、使用與維護。',
        '{actor}負責尋找、彙整與蒐集資料。',
        '{actor}負責維護已完成的資源。',
        '{actor}負責管理資料並支援其有效運用，涵蓋資料處理、資料政策、指引與可用性。',
        '{actor}負責以電子或紙本形式製作並發布資源副本。',
        '{actor}負責個人資料保護及資料保護政策相關工作。',
        '{actor}為資料管理方案撰寫者。',
    ],
}
LISTING = path('adminDetailsCUuid', 'contributorsQUuid')


def contributor_replies(people):
    """Synthetic rows are (item ID, optional name, selected role UUIDs)."""
    replies = {LISTING: [item for item, _, _ in people]}
    for item, name, roles in people:
        if name is not None:
            replies[path(LISTING, item, 'contributorNameQUuid')] = name
        replies[path(LISTING, item, 'contributorRoleQUuid')] = roles
    return replies


def check(root, language):
    counts = dict(role_subsets=0, identity_cases=0, missing_name_cases=0, full_documents=0)
    separator = ' ' if language == 'en' else ''
    label = 'Contributor' if language == 'en' else '參與人員'
    name_gap = ('Please provide the name of the person or team assigned these responsibilities.'
                if language == 'en' else '請補上負責上述職責的人員或團隊名稱。')
    dc = {'project': {'created_by': None}, 'e': {'choices': {
        role: {'label': label} for role, label in zip([*ROLES, CONTACT], ROLE_LABELS[language])}}}
    for escape in (False, True):
        env = environment(root, escape, language=language)
        question = env.from_string(PREFIX + "{% include 'src/questions/14-dm-responsible.html.j2' %}")
        front = env.from_string(PREFIX + "{% include 'src/contributors.html.j2' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile):
            return BeautifulSoup(template.render(repliesMap=replies, output_profile=profile, dc=dc), 'html.parser')

        def validate(soup, people, profile):
            expected = [(i, item, name, roles) for i, (item, name, roles) in enumerate(people, 1)
                        if any(role in roles for role in ROLES)]
            nodes = soup.select('.person-responsibilities')
            assert len(nodes) == len(expected)
            for node, (index, item, name, roles) in zip(nodes, expected):
                selected = [r for r in ROLES if r in roles]
                assert node['data-contributor-id'] == item
                assert node['data-contributor-index'] == str(index)
                actor = name if name and name.strip() else f'{label} {index}'
                assert not node.select('.responsible-person')
                paragraphs = node.select('.responsibility-summary')
                assert len(paragraphs) == 1
                assert paragraphs[0]['data-role-uuids'].split() == selected
                assert paragraphs[0].get_text().strip() == separator.join(
                    sentence.format(actor=actor) for role, sentence in zip(ROLES, SENTENCES[language]) if role in roles).strip()
                gaps = node.select('.data-gap')
                assert len(gaps) == int(profile == 'review' and not (name and name.strip()))
                if gaps: assert gaps[0].get_text(strip=True) == name_gap
            assert not soup.select('p p, p div, p ul, p table, script, img')
            if profile == 'submission': assert not soup.select('.data-gap, .data-review')
            if not expected:
                assert bool(soup.select('[data-status="missing-output"]')) == (profile == 'review')
                assert soup.select_one('#q-dm-responsible > h3')
            else:
                assert 'short-reading-unit' not in soup.select_one('.responsibilities-block').get('class', [])

        for bits, profile in itertools.product(itertools.product((False, True), repeat=7), ('review', 'submission')):
            selected = [role for role, included in zip(ROLES, bits) if included]
            people = [('person-1', 'Alex Chen', selected)]
            validate(render(question, contributor_replies(people), profile), people, profile)
            counts['role_subsets'] += 1

        identity_cases = [
            [('a', 'Same Name', ROLES[:3]), ('b', 'Same Name', ROLES[2:])],
            [('a', 'Alex Chen', ROLES), ('b', 'Robin Lin', [ROLES[1]]), ('c', 'Casey Wu', [CONTACT])],
            [('a', 'Alex Chen', list(reversed(ROLES)) + [ROLES[0], CONTACT, 'obsolete-role'])],
            [('a', 'Alex <script>alert(1)</script> & "Team"', ROLES)],
            [('a', 'Long organizational name ' * 50, ROLES)],
            [('a', 'Contact only', [CONTACT])],
            [('a', 'Unassigned', [])],
            [('obsolete', None, ['obsolete-role'])],
            [],
        ]
        for people, profile in itertools.product(identity_cases, ('review', 'submission')):
            replies = contributor_replies(people)
            # Stale deleted list items must never contribute names or roles.
            replies.update({path(LISTING, 'deleted', 'contributorNameQUuid'): 'Deleted person',
                            path(LISTING, 'deleted', 'contributorRoleQUuid'): ROLES})
            soup = render(question, replies, profile)
            validate(soup, people, profile)
            assert 'Deleted person' not in soup.get_text()
            if people and people[0][1] and people[0][1].startswith('Long organizational'):
                assert not soup.select('.person-responsibilities.short-reading-unit')
            if people and people[0][0] == 'obsolete':
                people_front = render(front, replies, profile)
                assert not people_front.select('.contributor')
                assert bool(people_front.select('#dmp-contributors')) == (profile == 'review')
            counts['identity_cases'] += 1

        for name, profile in itertools.product((None, '', ' \n '), ('review', 'submission')):
            people = [('empty', None, []), ('nameless', name, ROLES), ('named', 'Robin Lin', [ROLES[1]])]
            replies = contributor_replies(people)
            soup = render(question, replies, profile)
            validate(soup, people, profile)
            people_front = render(front, replies, profile)
            front_names = [n.get_text(strip=True) for n in people_front.select('.contributor .name')]
            expected_name = (f'{label} 2' if profile == 'submission'
                             else '(name not given)' if language == 'en' else '（姓名尚未提供）')
            assert front_names == [expected_name, 'Robin Lin']
            counts['missing_name_cases'] += 1

        for profile in ('review', 'submission'):
            people = [('a', None, ROLES), ('b', 'Robin Lin', [ROLES[1]])]
            soup = render(full, contributor_replies(people), profile)
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            validate(soup, people, profile)
            counts['full_documents'] += 1
    return counts
