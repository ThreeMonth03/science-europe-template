"""Q12 compact records and Q13 same-repository prose, in both language trees."""
import itertools
import copy

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
SOFTWARE_FACTS = {
    'en': {'documentation': {'Yes': 'Documentation for this software will be included in the metadata.',
                            'No': 'Documentation for this software will not be included in the metadata.'},
           'included': {'Yes': 'This software will be included.', 'No': 'This software will not be included.'}},
    'zh-Hant': {'documentation': {'Yes': '此軟體的說明文件將納入後設資料。',
                                 'No': '此軟體的說明文件不會納入後設資料。'},
                'included': {'Yes': '將一併提供此軟體。', 'No': '不會一併提供此軟體。'}},
}
REUSE = {
    'en': {'Us': 'Only we will be interested in re-using this data.',
           'SameField': 'Other researchers in this field will be interested in re-using this data.',
           'OtherField': 'Researchers working in other fields will be interested in re-using this data.'},
    'zh-Hant': {'Us': '只有我們有意再次使用這份資料。',
                'SameField': '本領域的其他研究人員會有興趣再次使用這份資料。',
                'OtherField': '其他領域的研究人員會有興趣再次使用這份資料。'},
}


def reuse_schema():
    from check_answer_mapping import schema, chapter, question
    km = schema()
    children = chapter(km, IDS['creatingCUuid'])
    question(km, children, IDS['measuredQUuid'], 'OptionsQuestion', [IDS['measuredYesAUuid'], IDS['measuredNoAUuid']])
    children = km['entities']['answers'][IDS['measuredYesAUuid']]['followUpUuids']
    children = question(km, children, IDS['measuredDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, IDS['measuredDataNameQUuid'], 'ValueQuestion')
    question(km, children, IDS['measuredDataReuseQUuid'], 'OptionsQuestion',
             [IDS['measuredDataReuse' + option + 'AUuid'] for option in REUSE['en']])
    question(km, km['entities']['answers'][IDS['measuredDataReuseOtherFieldAUuid']]['followUpUuids'],
             IDS['measuredDataReuseOtherFieldHowQUuid'], 'ValueQuestion')
    return km


def reuse_replies(option='OtherField', name='Dataset <A> & "B"', detail='<p>Original use.</p>'):
    parent = path('creatingCUuid', 'measuredQUuid')
    listing = path(parent, 'measuredYesAUuid', 'measuredDataQUuid')
    base = path(listing, 'measured-a')
    selection = path(base, 'measuredDataReuseQUuid')
    replies = {parent: IDS['measuredYesAUuid'], listing: ['measured-a']}
    for key, value in [(path(base, 'measuredDataNameQUuid'), name),
                       (selection, choice('measuredDataReuse', option)),
                       (path(selection, 'measuredDataReuseOtherFieldAUuid', 'measuredDataReuseOtherFieldHowQUuid'), detail)]:
        if value is not None: replies[key] = value
    return replies, listing


def software_schema():
    from check_answer_mapping import schema, chapter, question
    km = schema()
    children = chapter(km, IDS['preservingCUuid'])
    children = question(km, children, IDS['producedDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    for prefix in ['isPublishedData', 'publishedSpecSwUse']:
        question(km, children, IDS[prefix + 'QUuid'], 'OptionsQuestion', [IDS[prefix + 'YesAUuid'], IDS[prefix + 'NoAUuid']])
        children = km['entities']['answers'][IDS[prefix + 'YesAUuid']]['followUpUuids']
    children = question(km, children, IDS['publishedSpecSwUseWhatQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    for prefix in ['publishedSpecSwDocumentation', 'publishedSpecSwIncluded']:
        question(km, children, IDS[prefix + 'QUuid'], 'OptionsQuestion', [IDS[prefix + 'YesAUuid'], IDS[prefix + 'NoAUuid']])
    question(km, km['entities']['answers'][IDS['publishedSpecSwDocumentationNoAUuid']]['followUpUuids'],
             IDS['publishedSpecSwDocumentationReasonQUuid'], 'ValueQuestion')
    return km


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
    counts = dict(access_cases=0, software_cases=0, software_followups=0, inactive_software=0,
                  identifier_cases=0, reuse_cases=0, inactive_reuse=0, reuse_identity=0,
                  identity_cases=0, full_documents=0)
    for escape in (False, True):
        env = environment(root, escape)
        access = env.from_string(PREFIX + "{% include '" + Q12 + "' %}")
        identifier = env.from_string(PREFIX + "{% include '" + Q13 + "' %}")
        full = env.from_string(WRAPPER)

        def render(template, replies, profile, km=None):
            context = dict(km=km) if km is not None else {}
            soup = BeautifulSoup(template.render(repliesMap=replies, output_profile=profile, **context,
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
            assert len(tools) == ((count if profile == 'review' else 1) if active_tools else 0)
            assert bool(dataset.select('.answer-lead')) == active_tools
            if active_tools:
                assert tools[0].strong.get_text() == 'Tool <A> & "B"'
                assert 'https://example.org/tool?x=1&y=2' in tools[0].get_text()
                if profile == 'review': assert tools[1].select('.data-gap')
            else:
                assert 'Tool <A>' not in dataset.get_text() and 'https://example.org/tool' not in dataset.get_text()
            if pub == 'Yes' and sw == 'Yes' and not count:
                assert NEEDS_TOOLS[language] in dataset.get_text()
                assert dataset.select_one('[data-fact-id="required-software-list"][data-status="partial"]')
            counts['access_cases'] += 1

        for name, location, profile in itertools.product(
                ['Tool <A> & "B"', ' \n ', '', None], ['https://example.org/tool?x=1&y=2', ' \n ', '', None], ['review', 'submission']):
            replies = access_replies(software='Yes', count=1)
            base = path(LISTING, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid',
                        'publishedSpecSwUseQUuid', 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid', 'tool-0')
            for field, value in [('publishedSpecSwUseWhatNameQUuid', name), ('publishedSpecSwUseWhatPIDQUuid', location)]:
                if value is None: replies.pop(path(base, field), None)
                else: replies[path(base, field)] = value
            soup = render(access, replies, profile)
            tool = soup.select_one('ul.required-software > li')
            named, located = bool((name or '').strip()), bool((location or '').strip())
            assert bool(tool) == (profile == 'review' or named or located)
            if tool:
                if named: assert tool.strong.get_text() == name
                elif profile == 'submission': assert '1' in tool.strong.get_text()
                if located: assert location in tool.get_text()
                assert bool(tool.select('.data-gap')) == (not located and profile == 'review')
            else:
                assert NEEDS_TOOLS[language] in soup.get_text() and NO_TOOLS[language] not in soup.get_text()
                assert soup.select_one('[data-fact-id="required-software-list"][data-status="partial"]')
                assert not soup.select('ul.required-software, .answer-lead')
            counts['software_cases'] += 1

        km = software_schema()
        for documentation, included, named, profile in itertools.product(
                ['Yes', 'No', '', 'unknown'], ['Yes', 'No', '', 'unknown'], [False, True], ['review', 'submission']):
            replies = access_replies(software='Yes', count=1)
            listing = next(key for key in replies if key.endswith(IDS['publishedSpecSwUseWhatQUuid']))
            base = path(listing, 'tool-0')
            replies[path(base, 'publishedSpecSwUseWhatNameQUuid')] = 'Tool <A> & "B"' if named else ''
            replies[path(base, 'publishedSpecSwUseWhatPIDQUuid')] = ''
            docpath = path(base, 'publishedSpecSwDocumentationQUuid')
            replies[docpath] = choice('publishedSpecSwDocumentation', documentation)
            replies[path(base, 'publishedSpecSwIncludedQUuid')] = choice('publishedSpecSwIncluded', included)
            reason = '<p>Keep v1.2 &amp; README.md.</p><p>Second authored paragraph.</p><ul><li>Original item.</li></ul>'
            replies[path(docpath, 'publishedSpecSwDocumentationNoAUuid', 'publishedSpecSwDocumentationReasonQUuid')] = reason
            soup = render(access, replies, profile, km)
            assert bool(soup.select('.required-software > li')) == (profile == 'review' or named or documentation in ['Yes', 'No'] or included in ['Yes', 'No'])
            for fact, state in [('documentation', documentation), ('included', included)]:
                node = soup.select_one('[data-fact-id="software-' + fact + '"]')
                assert bool(node) == (state in ['Yes', 'No'])
                if node:
                    assert node.get_text() == SOFTWARE_FACTS[language][fact][state]
                    assert node['data-status'] == ('complete' if state == 'Yes' else 'explicit-no')
            detail = soup.select_one('[data-fact-id="software-documentation-reason"]')
            assert bool(detail) == (documentation == 'No')
            if detail: assert detail.decode_contents().strip().endswith(reason)
            else: assert 'README.md' not in soup.get_text()
            counts['software_followups'] += 1

        # An old reply behind a filtered question, removed answer, deleted item
        # or inactive parent must not create a new factual statement.
        for change in ['documentation-filtered', 'reason-filtered', 'included-filtered', 'answer-removed',
                       'chapter-filtered', 'publication-no', 'software-no', 'item-deleted']:
            schema = copy.deepcopy(km)
            replies = access_replies(software='Yes', count=1)
            listing = next(key for key in replies if key.endswith(IDS['publishedSpecSwUseWhatQUuid']))
            base = path(listing, 'tool-0')
            docpath = path(base, 'publishedSpecSwDocumentationQUuid')
            replies[docpath] = IDS['publishedSpecSwDocumentationNoAUuid']
            replies[path(base, 'publishedSpecSwIncludedQUuid')] = IDS['publishedSpecSwIncludedYesAUuid']
            replies[path(docpath, 'publishedSpecSwDocumentationNoAUuid', 'publishedSpecSwDocumentationReasonQUuid')] = '<p>Original reason.</p>'
            children = schema['entities']['questions'][IDS['publishedSpecSwUseWhatQUuid']]['itemTemplateQuestionUuids']
            if change == 'documentation-filtered': children.remove(IDS['publishedSpecSwDocumentationQUuid'])
            if change == 'included-filtered': children.remove(IDS['publishedSpecSwIncludedQUuid'])
            if change == 'reason-filtered': schema['entities']['answers'][IDS['publishedSpecSwDocumentationNoAUuid']]['followUpUuids'].clear()
            if change == 'answer-removed': schema['entities']['answers'].pop(IDS['publishedSpecSwDocumentationNoAUuid'])
            if change == 'chapter-filtered': schema['chapterUuids'].clear()
            if change == 'item-deleted': replies[listing] = []
            if change == 'publication-no': replies[path(LISTING, 'dataset-a', 'isPublishedDataQUuid')] = IDS['isPublishedDataNoAUuid']
            if change == 'software-no': replies[listing.rsplit('.', 2)[0]] = IDS['publishedSpecSwUseNoAUuid']
            for profile in ['review', 'submission']:
                soup = render(access, replies, profile, schema)
                expected = {'software-documentation', 'software-included', 'software-documentation-reason'}
                if change in ['documentation-filtered', 'answer-removed']: expected -= {'software-documentation', 'software-documentation-reason'}
                if change == 'included-filtered': expected.remove('software-included')
                if change == 'reason-filtered': expected.remove('software-documentation-reason')
                if change in ['chapter-filtered', 'publication-no', 'software-no', 'item-deleted']: expected.clear()
                actual = {node['data-fact-id'] for node in soup.select('[data-fact-id^="software-"]') if node['data-fact-id'] != 'software-location'}
                assert actual == expected, (change, actual)
                counts['inactive_software'] += 1

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

        authored = '<p>Combine v1.2.csv with <a href="https://example.org/observations">other observations</a>.</p><ul><li>Keep this list.</li></ul><p>Keep this paragraph.</p>'
        for option, name, detail, profile in itertools.product(
                [*REUSE[language], '', 'unknown'], ['Dataset <A> & "B"', 'Same name', None, ' \n ', 'Long dataset name ' * 10],
                [None, ' \n ', authored], ['review', 'submission']):
            replies, listing = reuse_replies(option, name, detail)
            soup = render(identifier, replies, profile, reuse_schema())
            entries = soup.select('.measured-data-reuse > ul > li')
            visible = profile == 'review' or bool((name or '').strip()) or option in REUSE[language]
            assert len(entries) == int(visible)
            assert bool(soup.select('.measured-data-reuse h4')) == visible
            if visible:
                summary = entries[0].select_one('.reuse-summary')
                assert ('answer-lead' in summary.parent.get('class', [])) == (
                    option == 'OtherField' and bool((detail or '').strip()) and len(name or '') <= 80)
                assert not summary.select('p, div, ul, br')
                label = summary.strong
                if name and name.strip():
                    assert label.get_text() == name and not label.find(True), 'Dataset names are text, not HTML'
                elif profile == 'submission': assert label.select_one('.dataset-label[data-list-index="1"]')
                else: assert label.get_text() == ('(no name given)' if language == 'en' else '（名稱尚未提供）')
                fact = summary.select_one('[data-fact-id="measured-data-reuse"]')
                assert bool(fact) == (option in REUSE[language])
                if fact: assert fact.get_text() == REUSE[language][option] and fact['data-status'] == 'complete'
                assert (' — ' in summary.get_text()) == bool(fact)
            body = soup.select_one('[data-fact-id="measured-data-reuse-uses"]')
            assert bool(body) == (option == 'OtherField' and bool((detail or '').strip()))
            if body:
                assert body.decode_contents() == authored, 'Never prepend a fabricated because-clause to authored uses'
                assert body.find_previous_sibling().get_text() == ('Potential uses in other fields:' if language == 'en' else '其他領域的可能用途：')
            else: assert 'v1.2.csv' not in soup.get_text()
            assert not soup.select('ul:empty, li:empty')
            counts['reuse_cases'] += 1

        for change, profile in itertools.product(
                ['chapter-filtered', 'list-filtered', 'name-filtered', 'choice-filtered', 'choice-removed',
                 'option-filtered', 'answer-removed', 'how-filtered', 'parent-no', 'parent-missing', 'item-deleted'],
                ['review', 'submission']):
            schema = reuse_schema()
            replies, listing = reuse_replies(detail=authored)
            e = schema['entities']
            children = e['questions'][IDS['measuredDataQUuid']]['itemTemplateQuestionUuids']
            if change == 'chapter-filtered': schema['chapterUuids'].clear()
            if change == 'list-filtered': e['answers'][IDS['measuredYesAUuid']]['followUpUuids'].clear()
            if change == 'name-filtered': children.remove(IDS['measuredDataNameQUuid'])
            if change == 'choice-filtered': children.remove(IDS['measuredDataReuseQUuid'])
            if change == 'choice-removed': e['questions'].pop(IDS['measuredDataReuseQUuid'])
            if change == 'option-filtered': e['questions'][IDS['measuredDataReuseQUuid']]['answerUuids'].remove(IDS['measuredDataReuseOtherFieldAUuid'])
            if change == 'answer-removed': e['answers'].pop(IDS['measuredDataReuseOtherFieldAUuid'])
            if change == 'how-filtered': e['answers'][IDS['measuredDataReuseOtherFieldAUuid']]['followUpUuids'].clear()
            if change == 'parent-no': replies[path('creatingCUuid', 'measuredQUuid')] = IDS['measuredNoAUuid']
            if change == 'parent-missing': replies.pop(path('creatingCUuid', 'measuredQUuid'))
            if change == 'item-deleted': replies[listing] = []
            soup = render(identifier, replies, profile, schema)
            assert bool(soup.select('.measured-data-reuse')) == (change in ['name-filtered', 'choice-filtered', 'choice-removed', 'option-filtered', 'answer-removed', 'how-filtered'])
            assert bool(soup.select('[data-fact-id="measured-data-reuse"]')) == (change in ['name-filtered', 'how-filtered'])
            assert bool(soup.select('[data-fact-id="measured-data-reuse-uses"]')) == (change == 'name-filtered')
            counts['inactive_reuse'] += 1

        for profile in ['review', 'submission']:
            replies, listing = reuse_replies(name=' \n ', detail=authored)
            replies[listing] = ['empty-before', 'name-only', 'measured-a', 'same-name', 'empty-after']
            for item in ['name-only', 'same-name', 'deleted']:
                replies[path(listing, item, 'measuredDataNameQUuid')] = 'Same name'
            replies[path(listing, 'same-name', 'measuredDataReuseQUuid')] = IDS['measuredDataReuseSameFieldAUuid']
            soup = render(full, replies, profile, reuse_schema())
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            rows = soup.select('.measured-data-reuse > ul > li')
            expected = replies[listing] if profile == 'review' else ['name-only', 'measured-a', 'same-name']
            assert [r['data-item-id'] for r in rows] == expected
            if profile == 'submission': assert rows[1].select_one('.dataset-label[data-list-index="3"]')
            assert soup.select_one('.measured-data-reuse .answer-detail').decode_contents() == authored
            replies[listing] = []
            assert not render(identifier, replies, profile, reuse_schema()).select('.measured-data-reuse, ul:empty')
            counts['reuse_identity'] += 1

        for profile in ['review', 'submission']:
            # Same dataset names are not an identity key; stale deleted entries
            # and a sibling's software or identifier state must never leak.
            replies = access_replies(name='Same Name')
            other = access_replies(software='Yes', name='Same Name', count=2, item='dataset-b')
            # Blank rows around partially filled tools must not renumber or
            # swallow them, and stale replies outside the list stay inactive.
            listing = next(key for key in other if key.endswith(IDS['publishedSpecSwUseWhatQUuid']))
            other[listing] = ['empty-before', 'tool-0', 'tool-1', 'empty-after']
            other[path(listing, 'tool-1', 'publishedSpecSwUseWhatPIDQUuid')] = 'https://example.org/location-only'
            other.pop(path(listing, 'tool-0', 'publishedSpecSwUseWhatPIDQUuid'))
            other[path(listing, 'deleted', 'publishedSpecSwUseWhatNameQUuid')] = 'Deleted tool'
            replies.update({k: v for k, v in other.items() if k != LISTING})
            replies[LISTING].append('dataset-b')
            deleted = access_replies(software='Yes', name='Deleted dataset', count=2, item='deleted')
            replies.update({k: v for k, v in deleted.items() if k != LISTING})
            soup = render(access, replies, profile)
            assert len(soup.select('.dataset-section')) == 2 and 'Deleted dataset' not in soup.get_text()
            assert not soup.select('[data-item-id="dataset-a"] .required-software')
            tools = soup.select('[data-item-id="dataset-b"] .required-software > li')
            assert [tool['data-item-id'] for tool in tools] == (other[listing] if profile == 'review' else ['tool-0', 'tool-1'])
            assert 'Deleted tool' not in soup.get_text()
            if profile == 'submission':
                expected = 'Software tool 3' if language == 'en' else '軟體工具 3'
                assert tools[1].strong.get_text() == expected
                assert 'https://example.org/location-only' in tools[1].get_text()
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
