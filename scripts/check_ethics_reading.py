"""Q9 record-level prose checks, including independently missing answers."""
import itertools

from bs4 import BeautifulSoup
from current_support import PREFIX, IDS, WRAPPER, environment, path

Q9 = 'src/questions/09-ethical-issues.html.j2'
DATASETS = path('preservingCUuid', 'producedDataQUuid')
PROJECTS = path('adminDetailsCUuid', 'projectsQUuid')
SUMMARY = {
    'en': {
        ('Yes', 'Yes'): 'This dataset contains personal and sensitive data.',
        ('Yes', 'No'): 'This dataset contains personal data but no sensitive data.',
        ('No', 'Yes'): 'This dataset contains sensitive data but no personal data.',
        ('No', 'No'): 'This dataset contains neither personal nor sensitive data.',
        ('Yes', ''): 'This dataset contains personal data.',
        ('No', ''): 'This dataset does not contain personal data.',
        ('', 'Yes'): 'This dataset contains sensitive data.',
        ('', 'No'): 'This dataset does not contain sensitive data.',
    },
    'zh-Hant': {
        ('Yes', 'Yes'): '此資料集含個人資料與敏感資料。',
        ('Yes', 'No'): '此資料集含個人資料，但不含敏感資料。',
        ('No', 'Yes'): '此資料集含敏感資料，但不含個人資料。',
        ('No', 'No'): '此資料集不含個人資料，也不含敏感資料。',
        ('Yes', ''): '此資料集含個人資料。',
        ('No', ''): '此資料集不含個人資料。',
        ('', 'Yes'): '此資料集含敏感資料。',
        ('', 'No'): '此資料集不含敏感資料。',
    },
}
STATUS = {
    'en': {'Planned': 'Approval is planned.', 'Applied': 'An application for approval has been submitted.',
           'Granted': 'Approval has been granted.', 'Reject': 'Approval has been rejected.'},
    'zh-Hant': {'Planned': '預計申請倫理審查。', 'Applied': '已提出倫理審查申請。',
                'Granted': '倫理審查已核准。', 'Reject': '倫理審查未獲核准。'},
}


def option(binding, value):
    return IDS.get(binding + value + 'AUuid', value)


def data_replies(personal='No', sensitive='No', name='Coastal observations', item='dataset-a'):
    result = {DATASETS: [item]}
    if name is not None: result[path(DATASETS, item, 'producedDataNameQUuid')] = name
    for binding, choice in [('containPersonal', personal), ('containSensitive', sensitive)]:
        if choice: result[path(DATASETS, item, binding + 'QUuid')] = option(binding, choice)
    return result


def approval_replies(approval='Yes', status='Granted', case='CASE-2026', name='Coastal project', item='project-a'):
    parent = path(PROJECTS, item, 'projEthicalApprovalQUuid')
    listing = path(parent, 'projEthicalApprovalYesAUuid', 'projEthicalApprovalAuthQUuid')
    result = {PROJECTS: [item], listing: ['record-a']}
    if name is not None: result[path(PROJECTS, item, 'projectNameQUuid')] = name
    if approval: result[parent] = option('projEthicalApproval', approval)
    if status: result[path(listing, 'record-a', 'projEthicalApprovalAuthStatusQUuid')] = option('projEthicalApprovalAuthStatus', status)
    if case is not None: result[path(listing, 'record-a', 'projEthicalApprovalAuthCaseQUuid')] = case
    return result


def check(root, language):
    counts = dict(dataset_cases=0, approval_cases=0, identity_cases=0, full_documents=0)
    for escape in (False, True):
        env = environment(root, escape)
        ethics = env.from_string(PREFIX + "{% include '" + Q9 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile):
            soup = BeautifulSoup(template.render(repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')
            assert not soup.select('script, img, p p, p div, p ul, p table')
            if profile == 'submission': assert not soup.select('.data-gap, .data-review')
            return soup

        for personal, sensitive, name, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], ['Yes', 'No', '', 'unknown'],
                ['Coastal observations', None, ' \n ', '<Dataset> & "A"', 'Long dataset name ' * 30],
                ['review', 'submission']):
            replies = data_replies(personal, sensitive, name)
            soup = render(ethics, replies, profile)
            item = soup.select_one('.ethical-dataset[data-item-id="dataset-a"]')
            key = tuple(s if s in ['Yes', 'No'] else '' for s in [personal, sensitive])
            expected_item = profile == 'review' or any(key)
            assert bool(item) == expected_item
            if not item:
                assert not soup.select('.ethical-datasets, h4')
                assert soup.select_one('#q-ethical-issues > h3')
                counts['dataset_cases'] += 1
                continue
            summary = item.select_one('p.ethical-data-summary')
            assert summary and not item.select('ul, ol, h5, br')
            label = summary.strong
            assert label
            if profile == 'submission': assert label.parent.get('class') == ['ethical-dataset-name']
            if name and name.strip(): assert label.get_text() == name and not label.find(True)
            elif profile == 'submission': assert label.select_one('.dataset-label[data-list-index="1"]')
            sentence = summary.select_one('.ethical-data-statement')
            assert bool(sentence) == any(key)
            if sentence:
                assert sentence.get_text(' ', strip=True) == SUMMARY[language][key]
                assert ' '.join(summary.get_text().split()) == ' '.join((label.get_text() + ' ' + SUMMARY[language][key]).split()), 'Actual name/sentence boundary lost'
            for fact, state in [('dataset-personal-data', personal), ('dataset-sensitive-data', sensitive)]:
                nodes = item.select(f'[data-fact-id="{fact}"]')
                assert len(nodes) == int(state in ['Yes', 'No'])
                if nodes: assert nodes[0]['data-status'] == ('complete' if state == 'Yes' else 'explicit-no')
            counts['dataset_cases'] += 1

        for approval, status, case, name, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], ['Planned', 'Applied', 'Granted', 'Reject', '', 'unknown'],
                [None, '', ' \n ', 'CASE-2026', 'Case <A> & "B"'],
                ['Coastal project', ' \n '], ['review', 'submission']):
            soup = render(ethics, approval_replies(approval, status, case, name), profile)
            project = soup.select_one('.ethical-project')
            assert bool(project) == (approval in ['Yes', 'No'])
            if project:
                summary = project.select_one('.ethical-project-summary')
                assert summary and summary.strong
                assert project['data-item-id'] == 'project-a'
                if not name.strip() and profile == 'submission': assert '1' in summary.strong.get_text()
                record = project.select_one('.ethical-approval-record')
                known = status in STATUS[language]
                has_case = bool(case and case.strip())
                assert bool(record) == (approval == 'Yes' and (known or has_case or profile == 'review'))
                assert not [li for li in project.select('li') if not li.get_text(strip=True)], 'No empty bullets'
                if record:
                    paragraphs = record.select('p.ethical-approval-summary')
                    assert len(paragraphs) == int(known or has_case)
                    if paragraphs:
                        text = ' '.join(paragraphs[0].get_text().split())
                        if known: assert STATUS[language][status] in text
                        else: assert not any(s in text for s in STATUS[language].values())
                        if has_case: assert case in text
                        if known and has_case:
                            label = 'Case number: ' if language == 'en' else '案號：'
                            assert text == STATUS[language][status] + ' ' + label + case
                    assert bool(record.select('.data-gap')) == (profile == 'review' and (not known or not has_case))
                elif case and case.strip(): assert case not in project.get_text()
            counts['approval_cases'] += 1

        for profile in ['review', 'submission']:
            replies = data_replies('Yes', 'No', 'Same name')
            other = data_replies('No', 'Yes', 'Same name', 'dataset-b')
            replies.update(other); replies[DATASETS] = ['dataset-b', 'dataset-a']
            replies[path(DATASETS, 'deleted', 'producedDataNameQUuid')] = 'Stale dataset'
            approvals = approval_replies(case='FIRST', name='Same project')
            extra = approval_replies(status='Applied', case='SECOND', name='Same project', item='project-b')
            approvals.update(extra); approvals[PROJECTS] = ['project-b', 'project-a']
            replies.update(approvals)
            soup = render(ethics, replies, profile)
            assert [n['data-item-id'] for n in soup.select('.ethical-dataset')] == ['dataset-b', 'dataset-a']
            assert [n['data-item-id'] for n in soup.select('.ethical-project')] == ['project-b', 'project-a']
            for item, key in [('dataset-b', ('No', 'Yes')), ('dataset-a', ('Yes', 'No'))]:
                assert SUMMARY[language][key] in soup.select_one(f'[data-item-id="{item}"]').get_text(' ', strip=True)
            assert 'SECOND' in soup.select('.ethical-project')[0].get_text()
            assert 'FIRST' in soup.select('.ethical-project')[1].get_text()
            assert 'Stale dataset' not in soup.get_text()
            counts['identity_cases'] += 1

            # Authored collection-purpose HTML is not part of this grouping.
            purpose = path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid',
                           'cpersGdprQUuid', 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid')
            authored = '<p>Keep Ethics-v1.2.csv.</p><p>Second paragraph.</p><ul><li>Original.</li></ul>'
            replies[path('creatingCUuid', 'collectPersonalQUuid')] = IDS['collectPersonalYesAUuid']
            replies[path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid', 'cpersGdprQUuid')] = IDS['cpersGdprExploreAUuid']
            replies[purpose] = authored
            document = render(full, replies, profile)
            assert len(document.select('.question')) == 15 and len(document.select('.dmp-section')) == 6
            q9 = document.select_one('#q-ethical-issues')
            assert authored in str(q9), 'Authored paragraph/list structure must survive'
            counts['full_documents'] += 1
    return counts
