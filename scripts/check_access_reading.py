"""Q12 compact records and Q13 same-repository prose, in both language trees."""
import itertools

from bs4 import BeautifulSoup
from current_support import PREFIX, IDS, WRAPPER, environment, path, identifier_replies

LISTING = path('preservingCUuid', 'producedDataQUuid')
Q12 = 'src/questions/12-access-data.html.j2'
Q13 = 'src/questions/13-persistent-identifier.html.j2'
NO_TOOLS = {'en': 'No specific software is required to access or use this dataset.',
            'zh-Hant': '取用或使用此資料集不需要特定軟體。'}
NEEDS_TOOLS = {'en': 'Specific software is required to use this dataset.',
               'zh-Hant': '使用此資料集需要特定軟體。'}
COMPOUND = {
    'en': {'Yes': 'The repository will assign the persistent identifier and ensure that it resolves to a digital object.',
           'No': 'The repository will assign the persistent identifier but will not guarantee that it resolves to a digital object.'},
    'zh-Hant': {'Yes': '儲存庫將指派持續識別碼，並確保該識別碼能解析至數位物件。',
                'No': '儲存庫將指派持續識別碼，但不保證該識別碼能解析至數位物件。'},
}


def choice(binding, suffix):
    return IDS.get(binding + str(suffix) + 'AUuid', suffix or '')


def access_replies(publication='Yes', software='No', name='Dataset A', count=0, item='dataset-a'):
    base = path(LISTING, item)
    pub = path(base, 'isPublishedDataQUuid')
    sw = path(pub, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
    listing = path(sw, 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid')
    result = {LISTING: [item], path(base, 'producedDataNameQUuid'): name,
              pub: choice('isPublishedData', publication), sw: choice('publishedSpecSwUse', software),
              listing: [f'tool-{i}' for i in range(count)]}
    for index, tool in enumerate(result[listing]):
        result[path(listing, tool, 'publishedSpecSwUseWhatNameQUuid')] = 'Tool <A> & "B"' if index == 0 else ' \n '
        result[path(listing, tool, 'publishedSpecSwUseWhatPIDQUuid')] = 'https://example.org/tool?x=1&y=2' if index == 0 else ''
    return result


def check(root, language):
    counts = dict(access_cases=0, software_cases=0, identifier_cases=0, identity_cases=0, full_documents=0)
    for escape in (False, True):
        env = environment(root, escape)
        access = env.from_string(PREFIX + "{% include '" + Q12 + "' %}")
        identifier = env.from_string(PREFIX + "{% include '" + Q13 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile):
            soup = BeautifulSoup(template.render(repliesMap=replies, output_profile=profile,
                dc={'project': {'created_by': None}, 'e': {'choices': {}}}), 'html.parser')
            assert not soup.select('p p, p div, p ul, p table, script, img')
            if profile == 'submission': assert not soup.select('.data-gap, .data-review')
            return soup

        for pub, sw, count, name, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], ['Yes', 'No', '', 'unknown'], [0, 2],
                ['Dataset A', '', ' \n '], ['review', 'submission']):
            soup = render(access, access_replies(pub, sw, name, count), profile)
            dataset = soup.select_one('.dataset-section')
            expected_dataset = profile == 'review' or pub == 'No' or (pub == 'Yes' and sw in ['Yes', 'No'])
            assert bool(dataset) == expected_dataset
            if not dataset:
                assert 'Tool <A>' not in soup.get_text() and 'https://example.org/tool' not in soup.get_text()
                assert soup.select_one('#q-access-data > h3')
                counts['access_cases'] += 1
                continue
            assert dataset['data-item-id'] == 'dataset-a'
            summary = dataset.select_one('.dataset-access-summary')
            assert bool(summary) == (pub == 'No' or pub == 'Yes' and sw in ['Yes', 'No'])
            if summary:
                assert not dataset.h5
                label = summary.strong
                assert not summary.select('p, ul, li, h5')
            else:
                label = dataset.h5
            assert label and (name in label.get_text() if name.strip() else bool(label.get_text(strip=True)))
            if not name.strip() and profile == 'submission': assert label.select_one('.dataset-label[data-list-index="1"]')
            assert (NO_TOOLS[language] in dataset.get_text()) == (pub == 'Yes' and sw == 'No')
            tools = dataset.select('ul.required-software > li')
            active_tools = pub == 'Yes' and sw == 'Yes' and count > 0
            assert len(tools) == (count if active_tools else 0)
            assert bool(dataset.select('.answer-lead')) == active_tools
            if active_tools:
                assert tools[0].strong.get_text() == 'Tool <A> & "B"'
                assert 'https://example.org/tool?x=1&y=2' in tools[0].get_text()
                assert bool(tools[1].select('.data-gap')) == (profile == 'review')
                if profile == 'submission': assert '2' in tools[1].strong.get_text()
            else:
                assert 'Tool <A>' not in dataset.get_text() and 'https://example.org/tool' not in dataset.get_text()
            if pub == 'Yes' and sw == 'Yes' and not count:
                assert NEEDS_TOOLS[language] in dataset.get_text()
                assert dataset.select_one('[data-fact-id="required-software-list"][data-status="partial"]')
            counts['access_cases'] += 1

        for name, location, profile in itertools.product(
                ['Tool <A> & "B"', ' \n '], ['https://example.org/tool?x=1&y=2', ' \n '], ['review', 'submission']):
            replies = access_replies(software='Yes', count=1)
            base = path(LISTING, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid',
                        'publishedSpecSwUseQUuid', 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid', 'tool-0')
            replies[path(base, 'publishedSpecSwUseWhatNameQUuid')] = name
            replies[path(base, 'publishedSpecSwUseWhatPIDQUuid')] = location
            tool = render(access, replies, profile).select_one('ul.required-software > li')
            assert tool
            if name.strip(): assert tool.strong.get_text() == name
            elif profile == 'submission': assert '1' in tool.strong.get_text()
            if location.strip(): assert location in tool.get_text()
            assert bool(tool.select('.data-gap')) == (not location.strip() and profile == 'review')
            counts['software_cases'] += 1

        for pub, parent, actor, resolves, profile in itertools.product(
                ['Yes', 'No', ''], ['Yes', 'No', '', 'unknown'],
                ['Repository', 'ProjectDataSteward', 'InstitDataSteward', '', 'unknown'],
                ['Yes', 'No', '', 'unknown'], ['review', 'submission']):
            replies = identifier_replies(identifier=parent, assigns=actor, resolves=resolves, count=1)
            replies[path(LISTING, 'dataset-a', 'isPublishedDataQUuid')] = choice('isPublishedData', pub)
            soup = render(identifier, replies, profile)
            dataset = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
            expected_dataset = profile == 'review' or pub == 'No' or (pub == 'Yes' and parent in ['Yes', 'No'])
            assert bool(dataset) == expected_dataset
            distribution = soup.select_one('.distribution-section[data-item-id="distro-0"]')
            expected_distribution = pub == 'Yes' and (profile == 'review' or parent in ['Yes', 'No'])
            assert bool(distribution) == expected_distribution
            policy = soup.select_one('.identifier-arrangement')
            assert bool(policy) == (pub == parent == 'Yes')
            if policy:
                assigner = policy.select_one('[data-fact-id="identifier-assigner"]')
                resolution = policy.select_one('[data-fact-id="identifier-resolution"]')
                assert bool(assigner) == (actor in ['Repository', 'ProjectDataSteward', 'InstitDataSteward'])
                assert bool(resolution) == (resolves in ['Yes', 'No'])
                if resolution: assert resolution['data-status'] == ('complete' if resolves == 'Yes' else 'explicit-no')
                if actor == 'Repository' and resolves in ['Yes', 'No']:
                    assert len(policy.find_all('p', recursive=False)) == 1
                    assert policy.get_text(' ', strip=True) == COMPOUND[language][resolves]
                    assert assigner.select_one('[data-fact-id="identifier-resolution"]') is resolution
                else:
                    assert not any(text in policy.get_text() for text in COMPOUND[language].values())
                gaps = soup.select('.identifier-followups .data-gap')
                assert bool(gaps) == (profile == 'review' and (not assigner or not resolution))
            else:
                assert not soup.select('.identifier-followups, [data-fact-id="identifier-assigner"], [data-fact-id="identifier-resolution"]')
            counts['identifier_cases'] += 1

        for profile in ['review', 'submission']:
            # Same dataset names are not an identity key; stale deleted entries
            # and a sibling's software or identifier state must never leak.
            replies = access_replies(name='Same Name')
            other = access_replies(software='Yes', name='Same Name', count=2, item='dataset-b')
            replies.update({k: v for k, v in other.items() if k != LISTING})
            replies[LISTING].append('dataset-b')
            deleted = access_replies(software='Yes', name='Deleted dataset', count=2, item='deleted')
            replies.update({k: v for k, v in deleted.items() if k != LISTING})
            soup = render(access, replies, profile)
            assert len(soup.select('.dataset-section')) == 2 and 'Deleted dataset' not in soup.get_text()
            assert not soup.select('[data-item-id="dataset-a"] .required-software')
            assert len(soup.select('[data-item-id="dataset-b"] .required-software > li')) == 2
            counts['identity_cases'] += 1
            extra = identifier_replies(count=2)
            for key in list(extra):
                if 'distro-1' in key and key.endswith(IDS['publishedDataIdentifierResolvableQUuid']):
                    extra[key] = IDS['publishedDataIdentifierResolvableNoAUuid']
            replies.update({k: v for k, v in extra.items() if k != LISTING})
            soup = render(full, replies, profile)
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            assert COMPOUND[language]['Yes'] == soup.select_one('#q-persistent-identifier [data-item-id="distro-0"] .identifier-arrangement').get_text(' ', strip=True)
            assert COMPOUND[language]['No'] == soup.select_one('#q-persistent-identifier [data-item-id="distro-1"] .identifier-arrangement').get_text(' ', strip=True)
            counts['full_documents'] += 1
    return counts
