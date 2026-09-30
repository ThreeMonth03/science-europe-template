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
PRESERVATION = {
    'en': {
        'metadata': {'Yes': 'The metadata will be available even when the data no longer exists.',
                     'No': 'The metadata will not remain available once the data no longer exists.'},
        'catalogue': {'Yes': 'We will add a reference to the published data in at least one data catalogue.',
                      'No': 'We will not add a reference to the published data in a data catalogue.',
                      'Prime': 'We will not add a separate data catalogue reference because the repository is the main source of reusable data in this field.'}},
    'zh-Hant': {
        'metadata': {'Yes': '即使資料已不存在，仍會持續提供後設資料。',
                     'No': '資料不再存在時，後設資料也將無法取得。'},
        'catalogue': {'Yes': '本計畫將在至少一個資料目錄中登錄已發布資料的參照資訊。',
                      'No': '本計畫不會在資料目錄中登錄已發布資料的參照資訊。',
                      'Prime': '此儲存庫是本領域取得資料進行再利用的主要來源，因此不另在資料目錄登錄已發布資料的參照資訊。'}},
}


def preservation_schema():
    from check_answer_mapping import schema, chapter, question
    km = schema()
    children = chapter(km, IDS['preservingCUuid'])
    children = question(km, children, IDS['producedDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, IDS['publishedDataMetadataPersistentQUuid'], 'OptionsQuestion',
             [IDS['publishedDataMetadataPersistent' + suffix + 'AUuid'] for suffix in ['Yes', 'No']])
    question(km, children, IDS['isPublishedDataQUuid'], 'OptionsQuestion',
             [IDS['isPublishedData' + suffix + 'AUuid'] for suffix in ['Yes', 'No']])
    children = km['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids']
    question(km, children, IDS['publishedDataCatalogueQUuid'], 'OptionsQuestion',
             [IDS['publishedDataCatalogue' + suffix + 'AUuid'] for suffix in ['Yes', 'No', 'Prime']])
    return km


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
    counts = dict(repository_cases=0, preservation_cases=0, inactive_preservation=0, identity_cases=0, full_documents=0)
    for escape in [False, True]:
        env = environment(root, escape)
        template = env.from_string(PREFIX + "{% include '" + Q11 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile, km=None):
            return BeautifulSoup(template.render(km=preservation_schema() if km is None else km,
                repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')

        fields = [('metadata', 'publishedDataMetadataPersistent', 'preservation-metadata-persistence'),
                  ('catalogue', 'publishedDataCatalogue', 'preservation-catalogue')]
        base = path(DATASETS, 'dataset-a')
        paths = [path(base, 'publishedDataMetadataPersistentQUuid'),
                 path(base, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDataCatalogueQUuid')]
        for metadata, catalogue, publication, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], ['Yes', 'No', 'Prime', '', 'unknown'],
                ['Yes', 'No', '', 'unknown'], ['review', 'submission']):
            replies = repository_replies(publication=publication)
            # No dataset name or retention answer: each known fact must survive alone.
            replies = {k: v for k, v in replies.items() if k not in [path(base, 'producedDataNameQUuid')]
                       and IDS['publishedDataHowLongQUuid'] not in k}
            for key, (_, binding, _), value in zip(paths, fields, [metadata, catalogue]):
                if value: replies[key] = IDS.get(binding + value + 'AUuid', value)
            soup = render(template, replies, profile)
            for (name, _, fact), value in zip(fields, [metadata, catalogue]):
                node = soup.select_one('[data-fact-id="' + fact + '"]')
                active = value in PRESERVATION[language][name] and (name == 'metadata' or publication == 'Yes')
                assert bool(node) == active, (name, value, publication)
                if node:
                    assert 'preservation-summary' in node.parent.get('class', [])
                    assert 'dataset-policy' in node.parent.get('class', [])
                    assert node['data-status'] == ('complete' if value == 'Yes' else 'explicit-no')
                    assert node.get_text() == PRESERVATION[language][name][value]
                    if profile == 'submission':
                        assert node.find_parent(class_='dataset-section').select_one('.dataset-label[data-list-index="1"]')
                for option, text in PRESERVATION[language][name].items():
                    assert (text in soup.get_text()) == (active and option == value)
            assert soup.select_one('#q-data-preservation > h3')
            assert not soup.select('p p, p div, p ul, ul:empty, li:empty')
            if profile == 'submission': assert not soup.select('.data-gap, .data-review')
            counts['preservation_cases'] += 1

        for selected, change, profile in itertools.product(['Yes', 'No'],
                ['question-filtered', 'question-deleted', 'answer-filtered', 'answer-deleted',
                 'wrong-type', 'chapter-filtered', 'dataset-deleted'], ['review', 'submission']):
            for index, (_, binding, fact) in enumerate(fields):
                km = preservation_schema()
                replies = repository_replies()
                qid, aid = IDS[binding + 'QUuid'], IDS[binding + selected + 'AUuid']
                replies[paths[index]] = aid
                children = (km['entities']['questions'][IDS['producedDataQUuid']]['itemTemplateQuestionUuids']
                            if index == 0 else km['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids'])
                if change == 'question-filtered': children.remove(qid)
                if change == 'question-deleted': km['entities']['questions'].pop(qid)
                if change == 'answer-filtered': km['entities']['questions'][qid]['answerUuids'].remove(aid)
                if change == 'answer-deleted': km['entities']['answers'].pop(aid)
                if change == 'wrong-type': km['entities']['questions'][qid]['questionType'] = 'ValueQuestion'
                if change == 'chapter-filtered': km['chapterUuids'].clear()
                if change == 'dataset-deleted': replies[DATASETS] = []
                soup = render(template, replies, profile, km)
                assert not soup.select('[data-fact-id="' + fact + '"]'), (binding, selected, change)
                if change != 'dataset-deleted': assert '7 years' in soup.get_text()
                counts['inactive_preservation'] += 1

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
