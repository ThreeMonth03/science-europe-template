import copy
import unittest
from test_identifier_reading import identifier_replies, render, IDS


class IdentifierFollowupTests(unittest.TestCase):
    def test_two_missing_fields_share_one_warning_outside_policy(self):
        soup=render(identifier_replies(assigns=None,resolves=None))
        for distro in soup.select('.distribution-section'):
            gap=distro.select_one('.identifier-followups')
            self.assertEqual(1,len(gap.select('p')))
            self.assertEqual(['identifier-assigner','identifier-resolution'],[s['data-fact-id'] for s in gap.select('span')])
            self.assertEqual(['missing','missing'],[s['data-status'] for s in gap.select('span')])
            self.assertIs(gap.find_previous_sibling(),distro.select_one('.identifier-arrangement'))
            self.assertFalse(distro.select('.identifier-arrangement .data-gap'))

    def test_known_sibling_and_explicit_no_survive_missing_followup(self):
        for assigns,resolves,fact in [(None,'No','identifier-resolution'),('Repository',None,'identifier-assigner')]:
            soup=render(identifier_replies(assigns=assigns,resolves=resolves))
            for distro in soup.select('.distribution-section'):
                node=distro.select_one(f'.identifier-arrangement [data-fact-id="{fact}"]')
                self.assertEqual('explicit-no' if resolves=='No' else 'complete',node['data-status'])
                self.assertEqual(1,len(distro.select('.identifier-followups span')))

    def test_unknown_and_missing_are_separate_without_echoing_raw_values(self):
        soup=render(identifier_replies(assigns='<script>future-choice</script>',resolves=None))
        self.assertNotIn('future-choice',str(soup))
        for distro in soup.select('.distribution-section'):
            self.assertEqual(2,len(distro.select('.identifier-followups p')))
            self.assertEqual(['missing','needs-review'],[n['data-status'] for n in distro.select('.identifier-followups span')])
            self.assertIn('cannot interpret',distro.select('.identifier-followups p')[1].get_text())

    def test_whitespace_is_missing_but_padded_valid_choice_is_review(self):
        soup=render(identifier_replies(assigns=' \n\t',resolves=' ' + IDS['publishedDataIdentifierResolvableYesAUuid']))
        for distro in soup.select('.distribution-section'):
            self.assertEqual('missing',distro.select_one('[data-fact-id="identifier-assigner"]')['data-status'])
            self.assertEqual('needs-review',distro.select_one('[data-fact-id="identifier-resolution"]')['data-status'])

    def test_false_unknown_and_missing_parents_do_not_emit_child_prompts(self):
        for parent in ['No',None,'future-parent']:
            soup=render(identifier_replies(identifier=parent,assigns=None,resolves=None))
            self.assertFalse(soup.select('.identifier-followups,[data-fact-id="identifier-assigner"],[data-fact-id="identifier-resolution"]'))

    def test_complete_has_no_empty_warning_and_resolution_no_is_not_a_gap(self):
        for value in ['Yes','No']:
            soup=render(identifier_replies(resolves=value))
            self.assertFalse(soup.select('.identifier-followups'))
            self.assertEqual(4,len(soup.select('[data-fact-id="identifier-assigner"],[data-fact-id="identifier-resolution"]')))

    def test_each_distribution_resets_warning_lists(self):
        replies=identifier_replies()
        for key in list(replies):
            if 'distro-0' in key and key.endswith((IDS['publishedDataIdentifierAssignsQUuid'],IDS['publishedDataIdentifierResolvableQUuid'])):
                replies.pop(key)
        soup=render(replies)
        self.assertEqual(1,len(soup.select('.identifier-followups')))
        self.assertEqual('distro-0',soup.select_one('.identifier-followups').parent['data-item-id'])

    def test_duplicate_dataset_names_do_not_mix_child_states(self):
        replies=identifier_replies(assigns=None,resolves='No')
        data=IDS['preservingCUuid']+'.'+IDS['producedDataQUuid']
        replies[data].append('dataset-b')
        for key,value in list(replies.items()):
            if key.startswith(data+'.dataset-a.'):
                replies[key.replace('.dataset-a.','.dataset-b.',1)]=copy.deepcopy(value)
        for item in ['dataset-a','dataset-b']: replies[data+'.'+item+'.'+IDS['producedDataNameQUuid']]='Same name'
        for key in list(replies):
            if '.dataset-b.' in key and key.endswith(IDS['publishedDataIdentifierQUuid']): replies[key]=IDS['publishedDataIdentifierNoAUuid']
        soup=render(replies)
        self.assertTrue(soup.select_one('[data-item-id="dataset-a"] .identifier-followups'))
        self.assertFalse(soup.select('[data-item-id="dataset-b"] .identifier-followups'))
