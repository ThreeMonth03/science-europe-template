"""Q10 publication summary: complete sentences, partial replies and record identity."""
import itertools
import re

from bs4 import BeautifulSoup
from current_support import PREFIX, IDS, WRAPPER, environment, path

Q10 = 'src/questions/10-share-restrictions.html.j2'
DATASETS = path('preservingCUuid', 'producedDataQUuid')
TIMING = {
    'en': dict(Soon='The dataset will be published as soon as possible after collection.',
               Cleanup='The dataset will be published after initial cleanup.',
               Finished='The dataset will be published after all processing has finished.',
               Wrapped='The dataset will be published when the project is completed.',
               Embargo='The dataset will be published after an embargo.'),
    'zh-Hant': dict(Soon='資料蒐集後將儘速發布。',
                    Cleanup='資料完成初步清理後將發布。',
                    Finished='資料完成所有處理作業後將發布。',
                    Wrapped='資料將於計畫完成時發布。',
                    Embargo='資料將於延後公開期限屆滿後發布。'),
}
YES = {'en': 'This dataset will be published.', 'zh-Hant': '此資料集將發布。'}
NO = {'en': 'This dataset will not be published.', 'zh-Hant': '此資料集將不公開發布。'}
CATALOGUE = {'en': 'We will add a reference to the published data in at least one data catalogue.',
             'zh-Hant': '本計畫將在至少一個資料目錄中登錄已發布資料的參照資訊。'}


def publication_replies(publication='Yes', timing='Wrapped', catalogue='Yes', name='Coastal data', item='dataset-a'):
    parent = path(DATASETS, item, 'isPublishedDataQUuid')
    result = {DATASETS: [item]}
    if name is not None:
        result[path(DATASETS, item, 'producedDataNameQUuid')] = name
    for key, binding, value in [
            (parent, 'isPublishedData', publication),
            (path(parent, 'isPublishedDataYesAUuid', 'publishedWhenQUuid'), 'publishedWhen', timing),
            (path(parent, 'isPublishedDataYesAUuid', 'publishedDataCatalogueQUuid'), 'publishedDataCatalogue', catalogue)]:
        if value:
            result[key] = IDS.get(binding + value + 'AUuid', value)
    return result


def expected(publication, timing, catalogue, language):
    if publication == 'No':
        return [NO[language]]
    sentences = []
    if timing in TIMING[language]:
        sentences.append(TIMING[language][timing])
    elif publication == 'Yes':
        sentences.append(YES[language])
    if catalogue == 'Yes':
        sentences.append(CATALOGUE[language])
    return sentences


def check(root, language):
    counts = dict(summary_cases=0, record_cases=0, identifier_cases=0, full_documents=0)
    for escape in [False, True]:
        env = environment(root, escape)
        template = env.from_string(PREFIX + "{% include '" + Q10 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile):
            return BeautifulSoup(template.render(repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')

        for publication, timing, catalogue, name, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], [*TIMING[language], '', 'unknown'],
                ['Yes', 'No', '', 'unknown'], ['Coastal data', None, ' \n ', '<Dataset> & "A"'],
                ['review', 'submission']):
            soup = render(template, publication_replies(publication, timing, catalogue, name), profile)
            item = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
            sentences = expected(publication, timing, catalogue, language)
            expected_dataset = profile == 'review' or bool(sentences)
            assert bool(item) == expected_dataset
            if not item:
                assert soup.select_one('#q-share-restrictions > h3') and not soup.select('.data-gap')
                counts['summary_cases'] += 1
                continue
            summary = item.select('p.publication-summary')
            assert len(summary) == bool(sentences), 'One actual paragraph, not several visually adjacent paragraphs'
            if summary:
                separator = ' ' if language == 'en' else ''
                assert summary[0].get_text() == separator.join(sentences), (publication, timing, catalogue, summary[0].get_text())
                assert not summary[0].select('p, div, ul, br')
                assert item.h5.find_next_sibling() == summary[0]
            for sentence in [YES[language], NO[language], *TIMING[language].values(), CATALOGUE[language]]:
                assert item.get_text().count(sentence) == int(sentence in sentences), (publication, timing, catalogue, sentence)
            if profile == 'submission':
                assert not item.select('.data-gap')
                if not name or not name.strip():
                    assert item.h5.select_one('.dataset-label[data-list-index="1"]')
            if name and name.strip():
                assert item.h5.get_text() == name and not item.h5.find(True)
            assert bool(item.select('.data-gap[data-fact-id="publication-decision"]')) == (profile == 'review' and publication not in ['Yes', 'No'])
            assert not soup.select('script, img, p p, p div, p ul')
            counts['summary_cases'] += 1

        # Identifier value/type are sibling answers: a missing type must not
        # erase a value. Retained inactive Other labels must not leak through.
        for kind, value, custom, profile in itertools.product(
                ['Handle', 'Doi', 'Ark', 'Url', 'Other', '', 'unknown'],
                ['10.1234/value', None, ' \n ', '<identifier> & "A"'],
                [None, 'Catalogue ID', '<Type> & "B"'], ['review', 'submission']):
            replies = publication_replies()
            listing = path(DATASETS, 'dataset-a', 'producedDataIdentifiersQUuid')
            item = path(listing, 'identifier-a')
            type_path = path(item, 'dataIdentifierTypeQUuid')
            replies[listing] = ['empty-before', 'identifier-a', 'empty-after']
            if kind:
                replies[type_path] = IDS.get('dataIdentifierType' + kind + 'AUuid', kind)
            if value is not None:
                replies[path(item, 'dataIdentifierIdentifierQUuid')] = value
            if custom is not None:
                replies[path(type_path, 'dataIdentifierTypeOtherAUuid', 'dataIdentifierTypeOtherTypeQUuid')] = custom
            soup = render(template, replies, profile)
            entries = soup.select('.dataset-section[data-item-id="dataset-a"] > ul > li')
            actual_value = (value or '').strip()
            labels = dict(Handle='Handle', Doi='DOI', Ark='ARK', Url='URL')
            label = labels.get(kind, '')
            if kind == 'Other':
                label = custom or ('Other identifier' if language == 'en' else '其他識別碼')
            elif not label and actual_value:
                label = 'Identifier' if language == 'en' else '識別碼'
            assert len(entries) == bool(label), (kind, value, custom, entries)
            if entries:
                separator = ': ' if language == 'en' else '：'
                assert entries[0].get_text() == label + (separator + actual_value if actual_value else '')
                links = entries[0].select('a')
                assert len(links) == int(bool(actual_value) and kind in ['Doi', 'Url'])
                if links:
                    assert links[0]['href'] == ('https://doi.org/' if kind == 'Doi' else '') + actual_value
                assert not entries[0].select('identifier, type, script, img')
            else:
                assert not soup.select('.dataset-section > ul')
            if profile == 'submission':
                assert not soup.select('.data-gap, .data-review')
            counts['identifier_cases'] += 1

        for profile in ['review', 'submission']:
            replies = publication_replies(name='Same dataset')
            extra = publication_replies('No', 'Soon', 'Yes', 'Same dataset', 'dataset-b')
            replies.update(extra)
            replies[DATASETS] = ['dataset-b', 'dataset-a']
            replies[path(DATASETS, 'deleted', 'producedDataNameQUuid')] = 'Stale dataset'
            # Distribution terms and qualified references stay in their own blocks.
            pub = path(DATASETS, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid')
            distros = path(pub, 'publishedDistrosQUuid')
            licenses = path(distros, 'distro-a', 'publishedDataLicensesQUuid')
            license_path = path(licenses, 'license-a', 'publishedDataLicenseQUuid')
            repository_kind = path(distros, 'distro-a', 'publishedDataRepositoryKindQUuid')
            authored = '<p>Keep v1.2.csv.</p><p>Second paragraph.</p><ul><li>Original.</li></ul>'
            replies.update({distros: ['distro-empty-before', 'distro-a', 'distro-empty-after'], licenses: ['license-a'],
                repository_kind: IDS['publishedDataRepositoryDomainSpecificAUuid'],
                license_path: IDS['publishedDataLicenseRestrictAUuid'],
                path(license_path, 'publishedDataLicenseRestrictAUuid', 'licenseRestrictConditionsQUuid'): authored})
            refs = path(pub, 'publishedQReferencesQUuid')
            items = path(refs, 'publishedQReferencesYesAUuid', 'publishedQReferencesItemQUuid')
            replies.update({refs: IDS['publishedQReferencesYesAUuid'], items: ['reference-a'],
                path(items, 'reference-a', 'publishedQReferenceIdQUuid'): 'Reference-01',
                path(items, 'reference-a', 'publishedQReferenceRelQUuid'): 'Derived from reference data.'})
            # Retained child answers of an explicit No must not claim publication.
            inactive = pub.replace('dataset-a', 'dataset-b')
            replies.update({key.replace(pub, inactive): value for key, value in list(replies.items()) if key.startswith(pub + '.')})
            soup = render(template, replies, profile)
            datasets = soup.select('.dataset-section')
            assert [d['data-item-id'] for d in datasets] == ['dataset-b', 'dataset-a']
            assert not datasets[0].select('.distribution-section')
            assert 'Reference-01' not in datasets[0].get_text()
            assert 'Reference-01' in datasets[1].get_text()
            distributions = datasets[1].select('.distribution-section')
            expected_distributions = ['distro-empty-before', 'distro-a', 'distro-empty-after'] if profile == 'review' else ['distro-a']
            assert [distribution['data-item-id'] for distribution in distributions] == expected_distributions
            retained = datasets[1].select_one('.distribution-section[data-item-id="distro-a"]')
            expected_label = 'Distribution 2' if language == 'en' else '資料提供管道 2'
            assert retained.select_one('.answer-lead').get_text(' ', strip=True) == expected_label
            punctuation = r'\s+[.:!?;,]' if language == 'en' else r'\s+[。！？：，；]'
            assert not re.search(punctuation, retained.select_one('.repository-arrangement').get_text())
            assert datasets[1].select_one('.answer-detail').decode_contents() == authored
            assert 'Stale dataset' not in soup.get_text()
            counts['record_cases'] += 1
            doc = render(full, replies, profile)
            assert len(doc.select('.question')) == 15 and len(doc.select('.dmp-section')) == 6
            assert doc.select_one('#q-share-restrictions .answer-detail').decode_contents() == authored
            counts['full_documents'] += 1
    return counts
