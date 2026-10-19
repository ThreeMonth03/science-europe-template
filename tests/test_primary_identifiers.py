"""Q13 retains active primary identifiers without inferring repository guarantees."""
from copy import deepcopy
import itertools
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_answer_mapping import chapter, question, schema
from current_support import IDS, PREFIX, environment, identifier_replies, path

Q13 = 'src/questions/13-persistent-identifier.html.j2'
DATASETS = path('preservingCUuid', 'producedDataQUuid')
DATASET = path(DATASETS, 'dataset-a')
IDENTIFIERS = path(DATASET, 'producedDataIdentifiersQUuid')
IDENTIFIER = path(IDENTIFIERS, 'identifier-a')
TYPE = path(IDENTIFIER, 'dataIdentifierTypeQUuid')
VALUE = path(IDENTIFIER, 'dataIdentifierIdentifierQUuid')
OTHER = path(TYPE, 'dataIdentifierTypeOtherAUuid', 'dataIdentifierTypeOtherTypeQUuid')
LABELS = dict(Handle='Handle', Doi='DOI', Ark='ARK', Url='URL', Other='Local <A> & "B"')
RECORDED = 'ark:/12345/record<A>&B'
NO_PID = 'We do not assign persistent identifiers to this dataset.'


def primary_schema():
    km = schema()
    children = chapter(km, IDS['preservingCUuid'])
    children = question(km, children, IDS['producedDataQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, children, IDS['producedDataNameQUuid'], 'ValueQuestion')
    question(km, children, IDS['isPublishedDataQUuid'], 'OptionsQuestion',
             [IDS['isPublishedDataYesAUuid'], IDS['isPublishedDataNoAUuid']])
    identifiers = question(km, children, IDS['producedDataIdentifiersQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    question(km, identifiers, IDS['dataIdentifierTypeQUuid'], 'OptionsQuestion',
             [IDS['dataIdentifierType' + kind + 'AUuid'] for kind in (*LABELS, 'NoPid')])
    question(km, km['entities']['answers'][IDS['dataIdentifierTypeOtherAUuid']]['followUpUuids'],
             IDS['dataIdentifierTypeOtherTypeQUuid'], 'ValueQuestion')
    question(km, identifiers, IDS['dataIdentifierIdentifierQUuid'], 'ValueQuestion')
    return km


def primary_replies(kind='Ark', value=RECORDED, publication=None):
    replies = {DATASETS: ['dataset-a'], IDENTIFIERS: ['identifier-a'],
               OTHER: LABELS['Other']}
    if kind is not None:
        replies[TYPE] = IDS.get('dataIdentifierType' + kind + 'AUuid', kind)
    if value is not None:
        replies[VALUE] = value
    if publication is not None:
        replies[path(DATASET, 'isPublishedDataQUuid')] = IDS.get('isPublishedData' + publication + 'AUuid', publication)
    return replies


class PrimaryIdentifierTests(unittest.TestCase):
    def render(self, template, replies, profile, km=None):
        context = {} if km is None else dict(km=km)
        soup = BeautifulSoup(template.render(repliesMap=replies, output_profile=profile, **context), 'html.parser')
        self.assertFalse(soup.select('p p,p div,p ul,p table,script,img,ul:empty,li:empty'))
        if profile == 'submission':
            self.assertFalse(soup.select('.data-gap,.data-review,.empty-value'))
        return soup

    def test_primary_type_and_value_are_independent_of_publication(self):
        km = primary_schema()
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include '" + Q13 + "' %}")
            for profile, known_km, publication, kind, value in itertools.product(
                    ('review', 'submission'), (False, True), ('Yes', 'No', None, 'unknown'),
                    (*LABELS, 'NoPid', None, 'unknown'), (None, ' \t\n\u3000', RECORDED)):
                with self.subTest(escape=escape, profile=profile, km=known_km, publication=publication, kind=kind, value=value):
                    soup = self.render(template, primary_replies(kind, value, publication), profile, km if known_km else None)
                    block = soup.select_one('.primary-identifiers')
                    actual_value = (value or '').strip()
                    self.assertEqual(bool(block), kind in (*LABELS, 'NoPid') or bool(actual_value))
                    self.assertEqual(NO_PID in soup.get_text(), kind == 'NoPid')
                    self.assertEqual('This dataset will not be published.' in soup.get_text(), publication == 'No')
                    self.assertFalse(soup.select('[data-fact-id="persistent-identifier"], [data-fact-id="identifier-assigner"], [data-fact-id="identifier-resolution"]'))
                    self.assertNotIn('will be assigned', soup.get_text())
                    if not block:
                        continue
                    self.assertEqual(['identifier-a'], [node['data-item-id'] for node in block.select('li')])
                    combined = block.select_one('[data-fact-id="primary-identifier-record"]')
                    self.assertEqual(bool(combined), kind in LABELS and bool(actual_value))
                    if combined:
                        self.assertEqual(LABELS[kind] + ': ' + actual_value, combined.get_text())
                        self.assertEqual(['strong'], [node.name for node in combined.find_all(True)])
                    type_fact = block.select_one('[data-fact-id="primary-identifier-type"]')
                    self.assertEqual(bool(type_fact), kind in LABELS and not actual_value)
                    if type_fact:
                        self.assertEqual('Identifier type: ' + LABELS[kind] + '.', type_fact.get_text())
                        self.assertFalse(type_fact.find(True), 'Authored identifier types must be escaped as text')
                    value_fact = combined or block.select_one('[data-fact-id="primary-identifier-value"][data-status="complete"]')
                    self.assertEqual(bool(value_fact), bool(actual_value))
                    if value_fact:
                        self.assertEqual(actual_value, value_fact.strong.get_text())
                        self.assertFalse(value_fact.strong.find(True), 'Identifier values must not become HTML')
                    self.assertEqual(bool(block.select('.data-gap')), profile == 'review' and kind in LABELS and not actual_value)
                    self.assertEqual(bool(block.select('[data-status="explicit-no"]')), kind == 'NoPid')
                    if profile == 'submission':
                        self.assertIsNotNone(soup.select_one('h5 .dataset-label[data-list-index="1"]'))

    def test_primary_record_and_future_repository_plan_remain_separate(self):
        for escape, profile, parent, resolves in itertools.product(
                (False, True), ('review', 'submission'), ('Yes', 'No', None), ('Yes', 'No', None)):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include '" + Q13 + "' %}")
            replies = primary_replies(publication='Yes')
            replies.update(identifier_replies(identifier=parent, resolves=resolves, count=1))
            soup = self.render(template, replies, profile, primary_schema())
            primary = soup.select_one('.primary-identifiers')
            self.assertEqual(RECORDED, primary.select_one('[data-fact-id="primary-identifier-record"] strong').get_text())
            self.assertFalse(primary.select('[data-fact-id="identifier-assigner"], [data-fact-id="identifier-resolution"]'))
            self.assertEqual(bool(soup.select('.identifier-arrangement')), parent == 'Yes')
            self.assertEqual(bool(soup.select('.identifier-arrangement [data-fact-id="identifier-resolution"]')), parent == 'Yes' and resolves in ('Yes', 'No'))
            self.assertEqual('Within this repository, unique and persistent identifiers will not be applied.' in soup.get_text(), parent == 'No')
            if parent == 'Yes':
                self.assertIn('will assign the persistent identifier', soup.select_one('.identifier-arrangement').get_text())

    def test_inactive_list_fields_options_and_deleted_records_are_not_resurrected(self):
        for escape, profile, mutation in itertools.product((False, True), ('review', 'submission'),
                ('chapter-filtered', 'produced-list-filtered', 'identifier-list-filtered', 'identifier-list-removed',
                 'identifier-list-wrong-type', 'dataset-deleted', 'identifier-deleted', 'list-missing',
                 'type-filtered', 'type-wrong-type', 'type-choice-filtered', 'type-answer-removed',
                 'value-filtered', 'value-wrong-type', 'other-filtered', 'other-unselected')):
            km, replies = primary_schema(), primary_replies(kind='Other')
            produced_children = km['entities']['questions'][IDS['producedDataQUuid']]['itemTemplateQuestionUuids']
            children = km['entities']['questions'][IDS['producedDataIdentifiersQUuid']]['itemTemplateQuestionUuids']
            if mutation == 'chapter-filtered': km['chapterUuids'].clear()
            elif mutation == 'produced-list-filtered': km['entities']['chapters'][IDS['preservingCUuid']]['questionUuids'].clear()
            elif mutation == 'identifier-list-filtered': produced_children.remove(IDS['producedDataIdentifiersQUuid'])
            elif mutation == 'identifier-list-removed': del km['entities']['questions'][IDS['producedDataIdentifiersQUuid']]
            elif mutation == 'identifier-list-wrong-type': km['entities']['questions'][IDS['producedDataIdentifiersQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'dataset-deleted': replies[DATASETS] = []
            elif mutation == 'identifier-deleted': replies[IDENTIFIERS] = []
            elif mutation == 'list-missing': replies.pop(IDENTIFIERS)
            elif mutation == 'type-filtered': children.remove(IDS['dataIdentifierTypeQUuid'])
            elif mutation == 'type-wrong-type': km['entities']['questions'][IDS['dataIdentifierTypeQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'type-choice-filtered': km['entities']['questions'][IDS['dataIdentifierTypeQUuid']]['answerUuids'].remove(IDS['dataIdentifierTypeOtherAUuid'])
            elif mutation == 'type-answer-removed': del km['entities']['answers'][IDS['dataIdentifierTypeOtherAUuid']]
            elif mutation == 'value-filtered': children.remove(IDS['dataIdentifierIdentifierQUuid'])
            elif mutation == 'value-wrong-type': km['entities']['questions'][IDS['dataIdentifierIdentifierQUuid']]['questionType'] = 'OptionsQuestion'
            elif mutation == 'other-filtered': km['entities']['answers'][IDS['dataIdentifierTypeOtherAUuid']]['followUpUuids'].clear()
            elif mutation == 'other-unselected': replies[TYPE] = IDS['dataIdentifierTypeArkAUuid']
            template = environment(ROOT, escape).from_string(PREFIX + "{% include '" + Q13 + "' %}")
            soup = self.render(template, replies, profile, km)
            with self.subTest(escape=escape, profile=profile, mutation=mutation):
                hidden = mutation in ('chapter-filtered', 'produced-list-filtered', 'identifier-list-filtered', 'identifier-list-removed',
                                      'identifier-list-wrong-type', 'dataset-deleted', 'identifier-deleted', 'list-missing')
                self.assertEqual(bool(soup.select('.primary-identifiers')), not hidden)
                self.assertEqual(RECORDED in soup.get_text(), not hidden and mutation not in ('value-filtered', 'value-wrong-type'))
                no_type = hidden or mutation in ('type-filtered', 'type-wrong-type', 'type-choice-filtered', 'type-answer-removed')
                self.assertEqual(bool(soup.select('[data-fact-id="primary-identifier-type"], [data-fact-id="primary-identifier-record"]')), not no_type)
                self.assertEqual(LABELS['Other'] in soup.get_text(), not no_type and mutation not in ('other-filtered', 'other-unselected'))
                self.assertNotIn(NO_PID, soup.get_text())

    def test_actual_reply_envelopes_require_the_expected_reply_types(self):
        env = environment(ROOT)
        flat_value, flat_items = env.filters['reply_str_value'], env.filters['reply_items']
        env.filters['reply_str_value'] = lambda r: r['value'].get('value', '') if isinstance(r, dict) and isinstance(r.get('value'), dict) else flat_value(r)
        env.filters['reply_items'] = lambda r: r['value'].get('value', []) if isinstance(r, dict) and isinstance(r.get('value'), dict) else flat_items(r)
        template = env.from_string(PREFIX + "{% include '" + Q13 + "' %}")
        correct_types = {DATASETS: 'ItemListReply', IDENTIFIERS: 'ItemListReply', TYPE: 'AnswerReply', VALUE: 'StringReply', OTHER: 'StringReply'}
        base = {key: {'value': {'type': correct_types[key], 'value': value}} for key, value in primary_replies(kind='Other').items()}
        for profile, wrong_path in itertools.product(('review', 'submission'), (None, *correct_types)):
            replies = deepcopy(base)
            if wrong_path:
                replies[wrong_path]['value']['type'] = 'AnswerReply' if correct_types[wrong_path] != 'AnswerReply' else 'StringReply'
            soup = self.render(template, replies, profile, primary_schema())
            hidden = wrong_path in (DATASETS, IDENTIFIERS)
            self.assertEqual(bool(soup.select('.primary-identifiers')), not hidden)
            self.assertEqual(RECORDED in soup.get_text(), not hidden and wrong_path != VALUE)
            self.assertEqual(bool(soup.select('[data-fact-id="primary-identifier-type"], [data-fact-id="primary-identifier-record"]')), not hidden and wrong_path != TYPE)
            self.assertEqual(LABELS['Other'] in soup.get_text(), not hidden and wrong_path not in (TYPE, OTHER))

    def test_equal_names_keep_record_identity_and_unnamed_submission_uses_original_index(self):
        for escape, profile, named in itertools.product((False, True), ('review', 'submission'), (False, True)):
            replies = primary_replies()
            replies.update({key.replace('dataset-a', 'dataset-b'): value for key, value in list(replies.items())})
            replies[DATASETS] = ['empty-before', 'dataset-b', 'dataset-a', 'empty-after']
            if named:
                for item in ('dataset-a', 'dataset-b'):
                    replies[path(DATASETS, item, 'producedDataNameQUuid')] = 'Same <A> & "B"'
            replies[path(DATASETS, 'deleted', 'producedDataIdentifiersQUuid')] = ['identifier-a']
            replies[path(DATASETS, 'deleted', 'producedDataIdentifiersQUuid', 'identifier-a', 'dataIdentifierIdentifierQUuid')] = 'Stale-deleted-identifier'
            template = environment(ROOT, escape).from_string(PREFIX + "{% include '" + Q13 + "' %}")
            soup = self.render(template, replies, profile, primary_schema())
            records = [node for node in soup.select('.dataset-section') if node.select_one('.primary-identifiers')]
            self.assertEqual(['dataset-b', 'dataset-a'], [node['data-item-id'] for node in records])
            self.assertEqual(2, len(soup.select('[data-fact-id="primary-identifier-record"][data-status="complete"]')))
            self.assertNotIn('Stale-deleted-identifier', soup.get_text())
            for index, record in enumerate(records, 2):
                if named:
                    self.assertEqual('Same <A> & "B"', record.h5.get_text())
                    self.assertFalse(record.h5.find(True))
                elif profile == 'submission':
                    self.assertEqual(str(index), record.h5.select_one('.dataset-label')['data-list-index'])


if __name__ == '__main__':
    unittest.main()
