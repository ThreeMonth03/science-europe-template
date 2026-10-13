import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
from test_answer_retention import IDS, path
from current_support import environment, identifier_replies
from check_access_reading import reuse_schema

Q13 = 'src/questions/13-persistent-identifier.html.j2'


def render(replies): return BeautifulSoup(render_question(Q13, replies, km=reuse_schema()), 'html.parser')


class IdentifierReadingTests(unittest.TestCase):
    def test_qualified_reference_decision_survives_empty_details_only_when_active(self):
        import copy
        from check_answer_mapping import schema, chapter, question

        q10 = 'src/questions/10-share-restrictions.html.j2'
        km = schema()
        children = chapter(km, IDS['preservingCUuid'])
        children = question(km, children, IDS['producedDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, children, IDS['isPublishedDataQUuid'], 'OptionsQuestion',
                 [IDS['isPublishedDataYesAUuid'], IDS['isPublishedDataNoAUuid']])
        published = km['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids']
        question(km, published, IDS['publishedQReferencesQUuid'], 'OptionsQuestion',
                 [IDS['publishedQReferencesYesAUuid'], IDS['publishedQReferencesNoAUuid']])
        references = km['entities']['answers'][IDS['publishedQReferencesYesAUuid']]['followUpUuids']
        leaves = question(km, references, IDS['publishedQReferencesItemQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        for name in ('publishedQReferenceIdQUuid', 'publishedQReferenceRelQUuid'):
            question(km, leaves, IDS[name], 'ValueQuestion')
        identifier_children = question(km, children, IDS['producedDataIdentifiersQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, identifier_children, IDS['dataIdentifierTypeQUuid'], 'OptionsQuestion', [IDS['dataIdentifierTypeArkAUuid']])

        datasets = path('preservingCUuid', 'producedDataQUuid')
        publication = path(datasets, 'dataset-a', 'isPublishedDataQUuid')
        decision = path(publication, 'isPublishedDataYesAUuid', 'publishedQReferencesQUuid')
        listing = path(decision, 'publishedQReferencesYesAUuid', 'publishedQReferencesItemQUuid')
        identifier = path(datasets, 'dataset-a', 'producedDataIdentifiersQUuid')
        id_path = path(listing, 'reference-a', 'publishedQReferenceIdQUuid')
        relation_path = path(listing, 'reference-a', 'publishedQReferenceRelQUuid')
        yes = 'This dataset has qualified references to other datasets.'
        no = 'This dataset has no qualified references to other datasets.'
        authored = '<p>Derived from <em>reference A</em>.</p><ul><li>Keep original relation.</li></ul>'
        base = {datasets: ['dataset-a'], publication: IDS['isPublishedDataYesAUuid'],
                identifier: ['identifier-a'], path(identifier, 'identifier-a', 'dataIdentifierTypeQUuid'): IDS['dataIdentifierTypeArkAUuid']}
        cases = [
            ('Yes', None, None, None), ('Yes', [], None, None),
            ('Yes', ['reference-a'], ' \t\n\u3000', ' \t\n\u3000'),
            ('Yes', ['reference-a'], 'Reference-01', None),
            ('Yes', ['reference-a'], None, authored),
            ('Yes', ['reference-a'], 'Reference-01', authored),
            ('No', ['reference-a'], 'Reference-01', authored),
            (None, ['reference-a'], 'Reference-01', authored),
            ('unknown', ['reference-a'], 'Reference-01', authored),
        ]
        for profile in ('review', 'submission'):
            for context in ({}, {'km': km}):
                for choice, items, ref_id, relation in cases:
                    with self.subTest(profile=profile, compiled=bool(context), choice=choice, items=items,
                                      ref_id=ref_id, relation=bool(relation)):
                        replies = dict(base)
                        if choice is not None: replies[decision] = IDS.get('publishedQReferences'+choice+'AUuid', choice)
                        if items is not None: replies[listing] = items
                        if ref_id is not None: replies[id_path] = ref_id
                        if relation is not None: replies[relation_path] = relation
                        soup = BeautifulSoup(render_question(q10, replies, output_profile=profile, **context), 'html.parser')
                        owner = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
                        detail_visible = choice == 'Yes' and bool((ref_id or '').strip() or (relation or '').strip())
                        fact = owner.select_one('[data-fact-id="qualified-references"]')
                        expected_fact = yes if choice == 'Yes' and not detail_visible else no if choice == 'No' else None
                        self.assertEqual(expected_fact, fact.get_text() if fact else None)
                        if fact:
                            self.assertEqual('explicit-no' if choice == 'No' else 'complete', fact['data-status'])
                            self.assertEqual(1, owner.get_text().count(expected_fact))
                        self.assertEqual(detail_visible and bool((ref_id or '').strip()), 'Reference-01' in owner.get_text())
                        detail = owner.select_one('.answer-detail')
                        self.assertEqual(detail_visible and bool((relation or '').strip()), bool(detail))
                        if detail:
                            # The body-test identity adapter receives the original
                            # authored value; real parser behaviour is checked separately.
                            self.assertEqual(authored, detail.decode_contents())
                        self.assertIn('ARK', owner.get_text())
                        self.assertFalse(soup.select('p p, p div, p ul'))
                        if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

            for choice in ('Yes', 'No'):
                for state in ('publication-missing', 'publication-no', 'publication-unknown', 'removed-dataset',
                              'removed-list', 'wrong-list-type', 'removed-question', 'wrong-type',
                              'removed-choice', 'dangling-answer', 'removed-followup', 'dangling-publication'):
                    with self.subTest(profile=profile, choice=choice, invalid=state):
                        current, replies = copy.deepcopy(km), dict(base)
                        replies.update({decision: IDS['publishedQReferences'+choice+'AUuid'], listing: ['reference-a'],
                                        id_path: 'Reference-01', relation_path: authored})
                        if state == 'publication-missing': replies.pop(publication)
                        elif state == 'publication-no': replies[publication] = IDS['isPublishedDataNoAUuid']
                        elif state == 'publication-unknown': replies[publication] = 'obsolete-option'
                        elif state == 'removed-dataset': replies[datasets] = []
                        elif state == 'removed-list': current['entities']['chapters'][IDS['preservingCUuid']]['questionUuids'] = []
                        elif state == 'wrong-list-type': current['entities']['questions'][IDS['producedDataQUuid']]['questionType'] = 'ValueQuestion'
                        elif state == 'removed-question': current['entities']['questions'].pop(IDS['publishedQReferencesQUuid'])
                        elif state == 'wrong-type': current['entities']['questions'][IDS['publishedQReferencesQUuid']]['questionType'] = 'ValueQuestion'
                        elif state == 'removed-choice': current['entities']['questions'][IDS['publishedQReferencesQUuid']]['answerUuids'].remove(IDS['publishedQReferences'+choice+'AUuid'])
                        elif state == 'dangling-answer': current['entities']['answers'].pop(IDS['publishedQReferences'+choice+'AUuid'])
                        elif state == 'removed-followup': current['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids'] = []
                        else: current['entities']['answers'].pop(IDS['isPublishedDataYesAUuid'])
                        soup = BeautifulSoup(render_question(q10, replies, km=current, output_profile=profile), 'html.parser')
                        self.assertFalse(soup.select('[data-fact-id="qualified-references"]'))
                        self.assertNotIn('References to other datasets:', soup.get_text())
                        self.assertNotIn('Reference-01', soup.get_text())
                        self.assertNotIn('Keep original relation.', soup.get_text())
                        if state != 'removed-dataset': self.assertIn('ARK', soup.get_text())

            # Identically named records retain separate decisions and original ordinal labels.
            other = publication.replace('dataset-a', 'dataset-b')
            other_decision = decision.replace('dataset-a', 'dataset-b')
            replies = {**base, datasets: ['dataset-a', 'dataset-b'], decision: IDS['publishedQReferencesYesAUuid'],
                       other: IDS['isPublishedDataYesAUuid'], other_decision: IDS['publishedQReferencesNoAUuid']}
            soup = BeautifulSoup(render_question(q10, replies, km=km, output_profile=profile), 'html.parser')
            owners = soup.select('.dataset-section')
            self.assertEqual(['dataset-a', 'dataset-b'], [owner['data-item-id'] for owner in owners])
            self.assertEqual([yes, no], [owner.select_one('[data-fact-id="qualified-references"]').get_text() for owner in owners])
            if profile == 'submission':
                self.assertEqual(['Produced dataset 1', 'Produced dataset 2'], [owner.h5.get_text(' ', strip=True) for owner in owners])

            # Local typed adapter exposes the UUID, so the production ReplyType
            # guard (not an accidental dict string) decides whether it is valid.
            from jinja2 import Undefined
            from current_support import PREFIX
            env = environment(ROOT)
            env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
            template = env.from_string(PREFIX + "{% include '" + q10 + "' %}")
            for choice in ('Yes', 'No'):
                for reply_type in ('AnswerReply', 'StringReply'):
                    replies = {**base, decision: {'value': {'type': reply_type, 'value': IDS['publishedQReferences'+choice+'AUuid']}}}
                    soup = BeautifulSoup(template.render(repliesMap=replies, km=km, output_profile=profile), 'html.parser')
                    fact = soup.select_one('[data-fact-id="qualified-references"]')
                    self.assertEqual(reply_type == 'AnswerReply', bool(fact))
                    if fact: self.assertEqual(yes if choice == 'Yes' else no, fact.get_text())

    def test_dataset_no_pid_is_active_and_independent_of_publication(self):
        import copy
        from check_answer_mapping import schema, chapter, question

        km = schema()
        children = chapter(km, IDS['preservingCUuid'])
        children = question(km, children, IDS['producedDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        children = question(km, children, IDS['producedDataIdentifiersQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, children, IDS['dataIdentifierTypeQUuid'], 'OptionsQuestion',
                 [IDS['dataIdentifierTypeNoPidAUuid'], IDS['dataIdentifierTypeArkAUuid']])
        question(km, children, IDS['dataIdentifierIdentifierQUuid'], 'ValueQuestion')
        datasets = path('preservingCUuid', 'producedDataQUuid')
        listing = path(datasets, 'dataset-a', 'producedDataIdentifiersQUuid')
        option = path(listing, 'identifier-a', 'dataIdentifierTypeQUuid')
        value_path = path(listing, 'identifier-a', 'dataIdentifierIdentifierQUuid')
        publication = path(datasets, 'dataset-a', 'isPublishedDataQUuid')
        sentence = 'We do not assign persistent identifiers to this dataset.'
        authored = 'identifier <A> & "B"'
        base = {datasets: ['dataset-a'], listing: ['identifier-a'],
                option: IDS['dataIdentifierTypeNoPidAUuid']}

        for profile in ('submission', 'review'):
            for pub in (None, IDS['isPublishedDataNoAUuid'], IDS['isPublishedDataYesAUuid']):
                for value in (' \n ', authored):
                    with self.subTest(profile=profile, publication=pub, value=value):
                        replies = {**base, value_path: value}
                        if pub is not None:
                            replies[publication] = pub
                        soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                            replies, km=km, output_profile=profile), 'html.parser')
                        facts = [p for p in soup.find_all('p') if p.get_text() == sentence]
                        self.assertEqual(1, len(facts))
                        self.assertEqual('dataset-a', facts[0].find_parent(class_='dataset-section')['data-item-id'])
                        entry = facts[0].parent
                        self.assertEqual('li', entry.name)
                        self.assertEqual(2 if value.strip() else 1, len(entry.find_all('p', recursive=False)))
                        if value.strip():
                            self.assertEqual('Recorded identifier: ' + authored, entry.find_all('p')[1].get_text())
                            self.assertEqual(authored, entry.strong.get_text())
                            self.assertFalse(entry.select('a, script'))
                            self.assertIn('&lt;A&gt; &amp;', entry.decode_contents())
                        else:
                            self.assertNotIn('Recorded identifier:', entry.get_text())
                        if profile == 'submission':
                            self.assertFalse(soup.select('.data-gap, .data-review'))

            # Flat legacy contexts have no compiled KM; live list membership
            # still scopes the answer, as for the existing identifier entries.
            for value in ('', authored):
                with self.subTest(profile=profile, schema='flat', value=value):
                    soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                        {**base, value_path: value, publication: IDS['isPublishedDataNoAUuid']},
                        output_profile=profile), 'html.parser')
                    self.assertEqual(1, soup.get_text().count(sentence))
                    self.assertEqual(bool(value), 'Recorded identifier:' in soup.get_text())
                    if value:
                        self.assertIn(authored, soup.get_text())
                        self.assertIn('&lt;A&gt; &amp;', soup.decode_contents())

            for state in ('missing', 'unknown', 'removed-item', 'removed-dataset', 'removed-choice',
                          'removed-answer', 'removed-question', 'wrong-type', 'removed-list'):
                with self.subTest(profile=profile, state=state):
                    current, replies = copy.deepcopy(km), dict(base)
                    if state == 'missing': replies.pop(option)
                    if state == 'unknown': replies[option] = 'obsolete-option'
                    if state == 'removed-item': replies[listing] = []
                    if state == 'removed-dataset': replies[datasets] = []
                    if state == 'removed-choice':
                        current['entities']['questions'][IDS['dataIdentifierTypeQUuid']]['answerUuids'].remove(IDS['dataIdentifierTypeNoPidAUuid'])
                    if state == 'removed-answer':
                        current['entities']['answers'].pop(IDS['dataIdentifierTypeNoPidAUuid'])
                    if state == 'removed-question':
                        current['entities']['questions'][IDS['producedDataIdentifiersQUuid']]['itemTemplateQuestionUuids'].remove(IDS['dataIdentifierTypeQUuid'])
                    if state == 'wrong-type':
                        current['entities']['questions'][IDS['dataIdentifierTypeQUuid']]['questionType'] = 'ValueQuestion'
                    if state == 'removed-list':
                        current['entities']['questions'][IDS['producedDataQUuid']]['itemTemplateQuestionUuids'].remove(IDS['producedDataIdentifiersQUuid'])
                    soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                        replies, km=current, output_profile=profile), 'html.parser')
                    self.assertNotIn(sentence, soup.get_text())

            # Existing type-only entries must stay literal labels, not NoPID prose.
            soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                {**base, option: IDS['dataIdentifierTypeArkAUuid']}, km=km, output_profile=profile), 'html.parser')
            entries = soup.select('.dataset-section > ul > li')
            self.assertEqual(['ARK'], [entry.get_text() for entry in entries])
            self.assertNotIn(sentence, soup.get_text())

    def test_known_assigner_states_assignment_once_with_both_facts(self):
        soup = render(identifier_replies())
        for index, distro in enumerate(soup.select('.distribution-section'), 1):
            heading = distro.select_one('.identifier-heading')
            self.assertEqual([f'Distribution {index}', 'Institutional repository'],
                             [p.get_text(strip=True) for p in heading.find_all('p', recursive=False)])
            policy = distro.select_one('.identifier-arrangement.dataset-policy')
            self.assertEqual(1, len(policy.find_all('p', recursive=False)))
            parent = policy.select_one('[data-fact-id="persistent-identifier"]')
            self.assertIs(parent.parent, policy)
            self.assertIs(parent.select_one('[data-fact-id="identifier-assigner"]').parent, parent)
            self.assertNotIn('Persistent identifiers will be assigned.', policy.get_text())
            unit=distro.select_one('.identifier-followup-unit.short-reading-unit')
            self.assertIs(heading.find_next_sibling(), unit)
            self.assertIs(policy.parent,unit)
        self.assertFalse(soup.select('p p, p div, p ul'))

    def test_single_distribution_retains_type_without_number(self):
        soup = render(identifier_replies(count=1))
        self.assertNotIn('Distribution 1', soup.get_text())
        self.assertEqual('Institutional repository', soup.select_one('.identifier-heading').get_text(strip=True))

    def test_whitespace_name_and_missing_repository_do_not_emit_empty_headings(self):
        replies = identifier_replies(repository=None, count=1)
        dataset = path('preservingCUuid', 'producedDataQUuid')
        replies[path(dataset, 'dataset-a', 'producedDataNameQUuid')] = '  \n '
        review = render(replies)
        self.assertEqual('(no name given)', review.select_one('.dataset-section > h5').get_text(strip=True))
        self.assertFalse(review.select('.identifier-heading'))
        self.assertFalse([node for node in review.find_all(['p', 'h5']) if not node.get_text(strip=True)])

        env = environment(ROOT)
        wrapper = env.from_string(
            "{% import 'src/macros.html.j2' as macros with context %}"
            "{% import 'src/uuids.j2' as uuids with context %}"
            "{% include 'src/questions/13-persistent-identifier.html.j2' with context %}"
        )
        submission = BeautifulSoup(
            wrapper.render(repliesMap=replies, output_profile='submission'), 'html.parser'
        )
        self.assertEqual('Produced dataset 1', submission.select_one('.dataset-section > h5').get_text(' ', strip=True))
        self.assertFalse([node for node in submission.find_all(['p', 'h5']) if not node.get_text(strip=True)])

    def test_no_missing_and_unknown_identifier_do_not_leak_stale_yes_children(self):
        for choice in ['No', None, 'unsupported']:
            soup = render(identifier_replies(identifier=choice))
            self.assertFalse(soup.select('.identifier-arrangement'))
            self.assertNotIn('will assign the persistent identifier', soup.get_text())
            self.assertNotIn('can be resolved', soup.get_text())
            self.assertEqual(choice != 'No', bool(soup.select('.distribution-section .data-gap')))

    def test_missing_or_negative_children_are_not_inferred_positive(self):
        soup = render(identifier_replies(assigns=None, resolves=None))
        self.assertTrue(all(len(p.find_all('p')) == 1 for p in soup.select('.identifier-arrangement')))
        soup = render(identifier_replies(resolves='No'))
        self.assertEqual(2, soup.get_text().count('will not guarantee'))

    def test_inactive_publication_discards_identifier_headings_and_stale_answers(self):
        for choice in [None, 'No']:
            replies = identifier_replies()
            key = next(p for p in replies if p.endswith(IDS['isPublishedDataQUuid']))
            replies[key] = IDS['isPublishedDataNoAUuid'] if choice else ''
            soup = render(replies)
            self.assertFalse(soup.select('.identifier-heading, .identifier-arrangement, .distribution-section'))

    def test_unrelated_authored_reuse_blocks_and_duplicate_names_are_not_joined(self):
        replies = identifier_replies()
        measured = path('creatingCUuid', 'measuredQUuid')
        replies[measured] = IDS['measuredYesAUuid']
        items = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        replies[items] = ['first', 'second']
        authored = '<p>First author paragraph.</p><ul><li>Author item.</li></ul><p>Last author paragraph.</p>'
        for item in replies[items]:
            base = path(items, item)
            replies[path(base, 'measuredDataNameQUuid')] = 'Same name'
            reuse = path(base, 'measuredDataReuseQUuid')
            replies[reuse] = IDS['measuredDataReuseOtherFieldAUuid']
            replies[path(reuse, 'measuredDataReuseOtherFieldAUuid', 'measuredDataReuseOtherFieldHowQUuid')] = authored
        soup = render(replies)
        self.assertEqual(2, len(soup.select('.answer-detail')))
        for node in soup.select('.answer-detail'):
            self.assertIn(authored, node.decode_contents())
            self.assertIsNone(node.find_parent(class_='identifier-arrangement'))
            self.assertIsNone(node.find_parent(class_='identifier-heading'))
