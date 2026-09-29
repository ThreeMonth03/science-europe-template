"""Q11 repository diagnostics are review-only; independently known facts survive."""
import itertools
import re

from bs4 import BeautifulSoup
from current_support import PREFIX, IDS, WRAPPER, environment, path

Q11 = 'src/questions/11-data-preservation.html.j2'
DATASETS = path('preservingCUuid', 'producedDataQUuid')
KNOWN = ['DomainSpecific', 'GeneralPurpose', 'National', 'Institutional', 'Special']
DIAGNOSTICS = {
    'en': ['The repository for this distribution has not been specified.',
           'The selected repository type cannot be described by this template.',
           'Whether we will be able to support this repository for a sufficiently long time has not been specified.'],
    'zh-Hant': ['尚未說明此管道將使用哪個資料儲存庫。', '本模板無法呈現所選的資料儲存庫類型，請核對。',
                '尚未說明能否長期維運此資料儲存庫。'],
}
SUPPORT = {
    'en': {'Yes': 'We will be able to support this repository for a sufficiently long time.',
           'No': 'We will not be able to support this repository for a sufficiently long time.'},
    'zh-Hant': {'Yes': '我們能夠長期維運此資料儲存庫。', 'No': '我們無法長期維運此資料儲存庫。'},
}
SERVICE = {
    'en': {'Download': 'The repository will provide a download-only service.',
           'Simple': 'The repository will provide a search and simple access interface.',
           'Advanced': 'The repository will provide an advanced processing service.'},
    'zh-Hant': {'Download': '資料儲存庫將僅提供下載服務。', 'Simple': '資料儲存庫將提供搜尋與簡易取用介面。',
                'Advanced': '資料儲存庫將提供進階處理服務。'},
}


def repository_replies(repository='Special', support='', service='Advanced', publication='Yes',
                       item='dataset-a', distribution='distro-a'):
    pub = path(DATASETS, item, 'isPublishedDataQUuid')
    listing = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    kind = path(listing, distribution, 'publishedDataRepositoryKindQUuid')
    special = path(kind, 'publishedDataRepositorySpecialAUuid')
    result = {DATASETS: [item], listing: [distribution],
              path(DATASETS, item, 'producedDataNameQUuid'): 'Same dataset',
              path(DATASETS, item, 'publishedDataHowLongQUuid'): IDS['publishedDataHowLongFixedAUuid'],
              path(DATASETS, item, 'publishedDataHowLongQUuid', 'publishedDataHowLongFixedAUuid',
                   'publishedDataHowLongFixedQUuid'): '7 years'}
    for key, binding, value in [(pub, 'isPublishedData', publication), (kind, 'publishedDataRepository', repository),
            (path(special, 'specialRepoLongTermSupportQUuid'), 'specialRepoLongTermSupport', support),
            (path(special, 'specialRepoServiceLevelQUuid'), 'specialRepoServiceLevel', service)]:
        if value:
            result[key] = IDS.get(binding + value + 'AUuid', value)
    return result


def contact_replies(text, item='dataset-a', distribution='distro-c'):
    result = repository_replies('DomainSpecific', item=item, distribution=distribution)
    kind = path(DATASETS, item, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid',
                'publishedDistrosQUuid', distribution, 'publishedDataRepositoryKindQUuid')
    parent = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
    result[parent] = IDS['domainSpecificRepoContactBeforeOtherAUuid']
    result[path(parent, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')] = text
    return result


def check(root, language):
    counts = dict(repository_cases=0, identity_cases=0, full_documents=0)
    for escape in [False, True]:
        env = environment(root, escape)
        template = env.from_string(PREFIX + "{% include '" + Q11 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile):
            return BeautifulSoup(template.render(repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')

        for repo, support, service, publication, profile in itertools.product(
                KNOWN + ['', 'unknown'], ['Yes', 'No', '', 'unknown'], [*SERVICE[language], '', 'unknown'],
                ['Yes', 'No', '', 'unknown'], ['review', 'submission']):
            replies = repository_replies(repo, support, service, publication)
            soup = render(template, replies, profile)
            rows = soup.select('.repository-distribution')
            visible = publication == 'Yes' and (repo in KNOWN or profile == 'review')
            assert len(rows) == int(visible), 'Do not leave a diagnostic-only or empty submission bullet'
            assert bool(soup.select('.repository-destinations')) == visible, 'No orphan heading/list'
            assert '7 years' in soup.get_text(), 'Repository gap must not hide independent retention answers'
            assert not soup.select('p p, p div, p ul, ul:empty, ol:empty')
            assert not [li for li in soup.select('li') if not li.get_text(strip=True)]
            if visible:
                row = rows[0]
                assert row['data-item-id'] == 'distro-a' and not row.select('.repository-label')
                punctuation = r'\s+[.:!?;,]' if language == 'en' else r'\s+[。！？：，；]'
                assert not re.search(punctuation, row.get_text())
                state = row.select_one('[data-fact-id="repository-long-term-support"]')
                wanted = repo == 'Special' and (support in SUPPORT[language] or profile == 'review')
                assert bool(state) == wanted
                if state:
                    status = 'complete' if support == 'Yes' else 'explicit-no' if support == 'No' else 'missing'
                    assert state['data-status'] == status
                    assert state.get_text() == SUPPORT[language].get(support, DIAGNOSTICS[language][2])
                for choice, sentence in SERVICE[language].items():
                    assert (sentence in row.get_text()) == (repo == 'Special' and service == choice)
                destination = row.select_one('[data-fact-id="repository-destination"]')
                assert bool(destination) == (repo not in KNOWN and profile == 'review')
                if destination:
                    assert destination['data-status'] == ('needs-review' if repo else 'missing')
            if profile == 'submission':
                assert not any(text in soup.get_text() for text in DIAGNOSTICS[language])
                assert not soup.select('.repository-destinations [data-status="missing"], .repository-destinations [data-status="needs-review"]')
            counts['repository_cases'] += 1

        for profile in ['review', 'submission']:
            for missing_middle in ['', 'unknown']:
                listing = path(DATASETS, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
                replies = repository_replies('Special', 'No', 'Advanced')
                authored = '<p>Authored example: ' + DIAGNOSTICS[language][0] + '</p><p>Keep Repo-v1.2.csv.</p><ul><li>Original.</li></ul>'
                for more in [repository_replies(missing_middle, 'Yes', 'Advanced', distribution='distro-b'), contact_replies(authored)]:
                    replies.update({k: v for k, v in more.items() if k not in [DATASETS, listing]})
                replies[listing] = ['distro-a', 'distro-b', 'distro-c']
                # Equal dataset names still belong to separate records.
                replies.update({k: v for k, v in repository_replies('', item='dataset-b').items() if k != DATASETS})
                replies[path(DATASETS, 'dataset-b', 'producedDataNameQUuid')] = ' \n '
                replies[DATASETS] = ['dataset-b', 'dataset-a', 'dataset-empty']
                soup = render(template, replies, profile)
                datasets = soup.select('.dataset-section')
                expected_datasets = ['dataset-b', 'dataset-a', 'dataset-empty'] if profile == 'review' else ['dataset-b', 'dataset-a']
                assert [d['data-item-id'] for d in datasets] == expected_datasets
                if profile == 'submission':
                    assert datasets[0].h5.select_one('.dataset-label[data-list-index="1"]')
                else:
                    expected_name = '(no name given)' if language == 'en' else '（名稱尚未提供）'
                    assert datasets[0].h5.get_text(strip=True) == expected_name
                ids = ['distro-a', 'distro-b', 'distro-c'] if profile == 'review' else ['distro-a', 'distro-c']
                assert [n['data-item-id'] for n in datasets[1].select('.repository-distribution')] == ids
                numbers = ['1', '2', '3'] if profile == 'review' else ['1', '3']
                labels = datasets[1].select('.repository-label')
                assert len(labels) == len(numbers) and all(number in label.get_text() for number, label in zip(numbers, labels))
                assert datasets[1].select_one('#repository-contact-2-3'), 'Contact anchors must keep original dataset/distribution indices'
                assert datasets[1].select_one('.answer-detail[data-fact-id="repository-contact-arrangements"]').decode_contents() == authored
                assert not datasets[1].select('.short-repository-list'), 'Authored blocks must not acquire a keep-together hint'
                assert bool(datasets[0].select('.repository-destinations')) == (profile == 'review')
                counts['identity_cases'] += 1
                doc = render(full, replies, profile)
                assert len(doc.select('.question')) == 15 and len(doc.select('.dmp-section')) == 6
                anchor = doc.select_one('#q-share-restrictions a[href="#repository-contact-2-3"]')
                assert anchor and doc.select_one(anchor['href'])
                assert doc.select_one('#q-data-preservation .answer-detail[data-fact-id="repository-contact-arrangements"]').decode_contents() == authored
                counts['full_documents'] += 1
    return counts
