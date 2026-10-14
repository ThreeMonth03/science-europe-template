"""Current Q3 ownership checks; the existing body adapter supplies Markdown HTML."""
import itertools
from pathlib import Path
import sys
import unittest
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, PREFIX, environment, path

Q3 = 'src/questions/03-docs-metadata.html.j2'
PARENT = path('processingCUuid', 'storageConvQUuid')
BASE = path(PARENT, 'storageConvExploreAUuid')
AUTHORED = ('<p>Keep v1.2 and <strong>station_YYYYMMDD.csv</strong>; A&amp;B.</p>'
            '<p>Separate authored paragraph!</p><ul><li>Keep the original record.</li>'
            '<li>Record each correction.</li></ul><table><tbody><tr><td>Original.csv</td>'
            '<td>0 TWD</td></tr></tbody></table><p>Keep the authored ending.</p>')
LABELS = dict(capacity='Storage capacity', filesystem='File system and version management',
              **{'object-store': 'Object and document storage', 'database': 'Database storage'})


def fixture(space='Little', size='', fs='Yes', obj='Yes', db='Yes', mode='Crud'):
    replies = {PARENT: IDS['storageConvExploreAUuid']}
    for question, choice, stem in [('storageSpaceQUuid', space, 'storageSpace'),
            ('storageConvFSysQUuid', fs, 'storageConvFSys'),
            ('storageConvObjStoreQUuid', obj, 'storageConvObjStore'),
            ('storageConvRelDbQUuid', db, 'storageConvRelDb')]:
        if choice is not None:
            replies[path(BASE, question)] = IDS.get(stem + choice + 'AUuid', choice)
    replies[path(BASE, 'storageSpaceQUuid', 'storageSpaceSpecifyAUuid', 'storageSpaceSpecifyQUuid')] = size
    replies[path(BASE, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid')] = AUTHORED
    replies[path(BASE, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scDocumentVersioningQUuid')] = IDS['scDocumentVersioningYesAUuid']
    replies[path(BASE, 'storageConvObjStoreQUuid', 'storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid')] = AUTHORED
    if mode:
        replies[path(BASE, 'storageConvRelDbQUuid', 'storageConvRelDbYesAUuid', 'scRelDbHandleChangesQUuid')] = IDS['scRelDb' + mode + 'AnswerUuid']
    return replies


class Q3StorageGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.envs = {escape: environment(ROOT, escape) for escape in (False, True)}
        cls.templates = {escape: env.from_string(PREFIX + "{% include '" + Q3 + "' %}")
                         for escape, env in cls.envs.items()}

    def render(self, replies, escape, profile, **extra):
        return html.fragment_fromstring(self.templates[escape].render(
            repliesMap=replies, output_profile=profile, **extra), create_parent=True)

    def groups(self, document):
        return {node.get('data-storage-group'): node for node in document.xpath('.//div[@class="q3-storage-group"]')}

    def test_four_owned_groups_keep_distinct_authored_answers_and_only_fixed_object_lead(self):
        metadata = path('accessCUuid', 'metadataOpenQUuid')
        for escape, profile in itertools.product((False, True), ('review', 'submission')):
            replies = fixture(space='Specify', size='2048')
            replies.update({metadata: IDS['metadataOpenNoAUuid'],
                path(metadata, 'metadataOpenNoAUuid', 'metadataOpenNoExplainQUuid'): AUTHORED})
            document = self.render(replies, escape, profile)
            outer, = document.xpath('.//div[@class="storage-conventions-policy"]')
            self.assertEqual([n.get('data-storage-group') for n in outer], list(LABELS))
            groups = self.groups(document)
            for name, node in groups.items():
                self.assertEqual(node.attrib, {'class': 'q3-storage-group', 'data-storage-group': name})
                self.assertEqual([n.tag for n in node], ['h5', 'div'])
                self.assertEqual(node[0].text, LABELS[name])
                self.assertEqual(node[1].attrib, {'class': 'dataset-policy'})
            expected = [html.tostring(n, with_tail=False) for n in html.fragments_fromstring(AUTHORED)]
            for fact in ('metadata-access-explanation', 'file-naming', 'object-naming'):
                detail, = document.xpath('.//div[@data-fact-id="' + fact + '"]')
                payload = [n for n in detail if n.get('class') != 'answer-lead']
                self.assertEqual([html.tostring(n, with_tail=False) for n in payload], expected)
            policy = groups['object-store'][1]
            self.assertEqual(policy[0].attrib, {'class': 'answer-lead'})
            self.assertEqual([n.tag for n in policy[0]], ['p'])
            self.assertEqual(policy[1].get('data-fact-id'), 'object-naming')
            self.assertFalse(document.xpath('.//div[@data-fact-id="metadata-access-explanation"]/ancestor::div[@class="storage-conventions-policy"]'))

    def test_system_yes_no_missing_unknown_and_stale_answers_are_local(self):
        for escape, profile, fs, obj, db in itertools.product((False, True), ('review', 'submission'),
                (None, 'No', 'Yes', 'unknown'), (None, 'No', 'Yes', 'unknown'), (None, 'No', 'Yes', 'unknown')):
            with self.subTest(escape=escape, profile=profile, fs=fs, obj=obj, db=db):
                document = self.render(fixture(fs=fs, obj=obj, db=db), escape, profile)
                expected = {'capacity'} | {name for name, choice in [('filesystem', fs), ('object-store', obj), ('database', db)] if choice in ('Yes', 'No')}
                self.assertEqual(set(self.groups(document)), expected)
                self.assertEqual(bool(document.xpath('.//*[@data-fact-id="file-naming"]')), fs == 'Yes')
                self.assertEqual(bool(document.xpath('.//*[@data-fact-id="object-naming"]')), obj == 'Yes')
                if fs == 'No':
                    self.assertIn('We will not use a filesystem with files and folders.', ''.join(self.groups(document)['filesystem'].itertext()))
                if obj == 'No':
                    self.assertFalse(self.groups(document)['object-store'].xpath('.//div[@class="answer-lead"]'))
                if profile == 'submission': self.assertFalse(document.xpath('.//*[@class="data-gap"]'))

    def test_capacity_is_independent_and_omitted_submission_body_has_no_empty_heading(self):
        for escape, profile, choice, size in itertools.product((False, True), ('review', 'submission'),
                (None, 'Little', 'Specify', 'unknown'), ('', '0', '2048')):
            document = self.render(fixture(choice, size, fs=None, obj=None, db=None), escape, profile)
            visible = choice == 'Little' or (choice == 'Specify' and (bool(size) or profile == 'review'))
            self.assertEqual(set(self.groups(document)), {'capacity'} if visible else set())
            if choice == 'Specify' and size:
                self.assertIn(size + ' gigabytes.', ''.join(self.groups(document)['capacity'].itertext()))
            if choice == 'Specify' and not size:
                self.assertEqual(bool(document.xpath('.//*[@data-fact-id="storage-capacity"]')), profile == 'review')

    def test_database_modes_and_absent_object_naming_preserve_existing_conditions(self):
        phrases = {'ReadOnly': 'Data in the database will be read-only.',
                   'Crud': 'We will be allowing Create, Update and Delete operations for data in the database.',
                   'Expire': 'Modifications will be made by Expiring the existing data and Adding updated data.'}
        for escape, profile, mode in itertools.product((False, True), ('review', 'submission'), (*phrases, None)):
            replies = fixture(fs='No', mode=mode)
            replies[path(BASE, 'storageConvObjStoreQUuid', 'storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid')] = ''
            groups = self.groups(self.render(replies, escape, profile))
            self.assertFalse(groups['object-store'].xpath('.//div[@class="answer-lead"]'))
            text = ''.join(groups['database'].itertext())
            for name, phrase in phrases.items(): self.assertEqual(phrase in text, name == mode)

    def test_folder_conventions_and_versioning_stay_inside_filesystem(self):
        for escape, profile, version in itertools.product((False, True), ('review', 'submission'), ('Yes', 'No', None)):
            replies = fixture()
            for kind in ('Subj', 'Analysis', 'WorkflowStep'):
                question = path(BASE, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scFSys' + kind + 'FoldersQUuid')
                replies[question] = IDS['scFSys' + kind + 'FoldersYesAUuid']
                replies[path(question, 'scFSys' + kind + 'FoldersYesAUuid', 'scFSys' + kind + 'FoldersConvsQUuid')] = AUTHORED
            key = path(BASE, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scDocumentVersioningQUuid')
            if version is None: replies.pop(key)
            else: replies[key] = IDS['scDocumentVersioning' + version + 'AUuid']
            group = self.groups(self.render(replies, escape, profile))['filesystem']
            self.assertEqual(len(group.xpath('./div/ul/li')), 3)
            self.assertEqual(len(group.xpath('.//table')), 4)  # Three folder answers plus file naming.
            text = ''.join(group.itertext())
            self.assertEqual('We document how we manage file versioning' in text, version == 'Yes')
            self.assertEqual('We have not documented how we manage file versioning' in text, version == 'No')

    def test_independent_project_file_naming_remains_outside_storage_groups(self):
        from check_answer_mapping import chapter, question, schema
        for escape, profile in itertools.product((False, True), ('review', 'submission')):
            env = self.envs[escape]; followups = env.get_template('src/full-km-followups.j2').module
            km = schema(); children = chapter(km, followups.namingChapter)
            replies, trail = fixture(fs='No', obj=None, db=None), [followups.namingChapter]
            for qid, aid in followups.namingBranch:
                question(km, children, qid, 'OptionsQuestion', [aid])
                replies[path(*trail, qid)] = aid; trail += [qid, aid]
                children = km['entities']['answers'][aid]['followUpUuids']
            question(km, children, followups.namingLeaf, 'ValueQuestion')
            replies[path(*trail, followups.namingLeaf)] = AUTHORED
            document = self.render(replies, escape, profile, km=km)
            actual, = document.xpath('.//div[@data-fact-id="project-file-naming"]')
            standalone = html.fragment_fromstring(env.from_string(PREFIX + "{% include 'src/project-file-naming.html.j2' %}").render(repliesMap=replies, output_profile=profile, km=km), create_parent=True)
            expected, = standalone.xpath('.//div[@data-fact-id="project-file-naming"]')
            self.assertEqual(html.tostring(actual, with_tail=False), html.tostring(expected, with_tail=False))
            self.assertFalse(actual.xpath('ancestor::div[@class="q3-storage-group"]'))


if __name__ == '__main__': unittest.main()
