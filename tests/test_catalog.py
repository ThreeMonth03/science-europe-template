"""POT ownership, source provenance and language-neutral catalog validation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import polib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_catalog import validate
from export_pot import export_pot
from template_catalog import extract_template_catalog


class TemplateCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.english = self.base / 'english'
        self.english.mkdir()
        (self.english / 'src').mkdir()
        (self.english / 'template.json').write_text(json.dumps({
            'organizationId': 'example', 'templateId': 'custom', 'version': '1.2.3',
            'language': 'en',
        }), encoding='utf-8')
        (self.english / '.gitignore').write_text('outputs/\n', encoding='utf-8')
        self.sources = {
            'a.j2': '{# TRANSLATORS: A data source, not a document title. #}\n'
                    '{{ pgettext("dataset", "Data from %(source)s.", source="station") }}',
            'b.jinja': '{{ gettext("Title") }}',
            'c.jinja2': '{{ pgettext("document", "Title") }}',
            'd.jnj': '{% trans %}Description{% endtrans %}',
        }
        for name, text in self.sources.items():
            (self.english / 'src' / name).write_text(text, encoding='utf-8')

    def git(self, *arguments):
        return subprocess.run(['git', '-C', str(self.english), '-c', 'core.hooksPath=/dev/null',
                               *arguments], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    def commit(self):
        self.git('init', '-q')
        self.git('config', 'user.name', 'Catalog test')
        self.git('config', 'user.email', 'catalog@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('add', '.')
        self.git('commit', '-qm', 'Catalog fixture')
        return self.git('rev-parse', 'HEAD')

    def catalog(self):
        path = self.base / 'locale.po'
        po = polib.POFile()
        po.metadata = {'Language': 'fr'}
        for message in extract_template_catalog(self.english).result.catalog:
            if message.id:
                po.append(polib.POEntry(msgctxt=message.context, msgid=message.id,
                                       msgstr=message.id.replace('Data from', 'Données de')))
        po.save(str(path))
        return po, path

    def test_extracts_sorted_supported_sources_and_preserves_contexts_and_comments(self):
        source = extract_template_catalog(self.english)
        self.assertEqual('example:custom:1.2.3', source.coordinate)
        self.assertEqual(tuple('src/' + name for name in sorted(self.sources)), source.files)
        marked = {(message.context, message.id): message for message in source.result.catalog if message.id}
        self.assertIn((None, 'Title'), marked)
        self.assertIn(('document', 'Title'), marked)
        self.assertIn('A data source, not a document title.',
                      marked[('dataset', 'Data from %(source)s.')].auto_comments)

    def test_exports_official_messages_with_full_identity_and_committed_provenance(self):
        commit = self.commit()
        output = self.english / 'outputs/template.pot'
        report = export_pot(output, self.english)
        po = polib.pofile(str(output))
        self.assertEqual('en', po.metadata['Language'])
        self.assertEqual('example:custom:1.2.3', po.metadata['X-DSW-Template'])
        self.assertEqual(commit, po.metadata['X-DSW-Source-Commit'])
        self.assertEqual(commit, report['source_commit'])
        self.assertEqual(4, report['marked_messages'])
        entry = po.find('Data from %(source)s.', msgctxt='dataset')
        self.assertIn('A data source, not a document title.', entry.comment)
        self.assertEqual([('src/a.j2', '2')], entry.occurrences)
        second = self.base / 'second.pot'
        export_pot(second, self.english)
        self.assertEqual(output.read_bytes(), second.read_bytes())

    def test_refuses_existing_output_and_dangling_symlink_without_overwrite(self):
        self.commit()
        output = self.base / 'existing.pot'
        output.write_text('keep', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            export_pot(output, self.english)
        self.assertEqual('keep', output.read_text(encoding='utf-8'))
        link = self.base / 'link.pot'
        target = self.base / 'missing.pot'
        link.symlink_to(target)
        with self.assertRaises(FileExistsError):
            export_pot(link, self.english)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_failed_jinja_parse_produces_no_output_or_directory(self):
        (self.english / 'src/broken.j2').write_text('{% if %}', encoding='utf-8')
        self.commit()
        output = self.base / 'new-directory/template.pot'
        with self.assertRaisesRegex(ValueError, 'parsing failed.*broken.j2'):
            export_pot(output, self.english)
        self.assertFalse(output.parent.exists())

    def test_rejects_empty_or_unmarked_source(self):
        for name in self.sources:
            (self.english / 'src' / name).unlink()
        with self.assertRaisesRegex(ValueError, 'No supported Jinja'):
            extract_template_catalog(self.english)
        (self.english / 'src/unmarked.j2').write_text('<p>Unmarked</p>', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'no marked translation messages'):
            extract_template_catalog(self.english)

    def test_rejects_missing_or_non_english_source_language(self):
        path = self.english / 'template.json'
        metadata = json.loads(path.read_text(encoding='utf-8'))
        for language in (None, 'zh-Hant', 'fr'):
            with self.subTest(language=language):
                if language is None:
                    metadata.pop('language', None)
                else:
                    metadata['language'] = language
                path.write_text(json.dumps(metadata), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'language="en"'):
                    extract_template_catalog(self.english)

    def test_rejects_source_head_change_during_extraction(self):
        self.commit()
        output = self.base / 'template.pot'
        def changed_head(english):
            source = extract_template_catalog(english)
            self.git('commit', '--allow-empty', '-qm', 'Concurrent source update')
            return source
        with patch('export_pot.extract_template_catalog', side_effect=changed_head):
            with self.assertRaisesRegex(ValueError, 'HEAD changed during extraction'):
                export_pot(output, self.english)
        self.assertFalse(output.exists())

    def test_export_rejects_unknown_or_dirty_source(self):
        output = self.base / 'template.pot'
        with self.assertRaisesRegex(ValueError, 'Git checkout'):
            export_pot(output, self.english)
        self.assertFalse(output.exists())
        self.commit()
        source = self.english / 'src/a.j2'
        source.write_text(source.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'dirty'):
            export_pot(output, self.english)
        self.assertFalse(output.exists())
        source.write_text(self.sources['a.j2'], encoding='utf-8')
        (self.english / 'untracked.txt').write_text('pending', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'dirty'):
            export_pot(output, self.english)
        self.assertFalse(output.exists())

    def test_rejects_ignored_source_with_no_committed_provenance(self):
        (self.english / '.gitignore').write_text('outputs/\nsrc/ignored.j2\n', encoding='utf-8')
        self.commit()
        (self.english / 'src/ignored.j2').write_text('{{ _("Uncommitted") }}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'tracked regular files'):
            export_pot(self.base / 'template.pot', self.english)

    def test_validation_is_language_neutral_and_keeps_context_keys(self):
        po, path = self.catalog()
        report = validate(path, self.english)
        self.assertEqual('fr', report['language'])
        self.assertEqual(4, report['marked_messages'])
        self.assertEqual(2, report['contexted_messages'])
        self.assertEqual('example:custom:1.2.3', report['template'])

    def test_validation_rejects_missing_fuzzy_duplicate_and_unsafe_translations(self):
        def missing(po):
            po.pop()
        def fuzzy(po):
            po[0].flags.append('fuzzy')
        def duplicate(po):
            po.append(polib.POEntry(msgctxt=po[0].msgctxt, msgid=po[0].msgid, msgstr=po[0].msgstr))
        def wrong_placeholder(po):
            po.find('Data from %(source)s.', msgctxt='dataset').msgstr = 'Données de %(other)s.'
        def unsafe_percent(po):
            po.find('Title').msgstr = 'Titre 100%'
        def empty(po):
            po[0].msgstr = ''
        def language_missing(po):
            po.metadata.pop('Language')
        for mutate in (missing, fuzzy, duplicate, wrong_placeholder, unsafe_percent, empty, language_missing):
            with self.subTest(case=mutate.__name__):
                po, path = self.catalog()
                mutate(po)
                po.save(str(path))
                with self.assertRaises(ValueError):
                    validate(path, self.english)

    def test_plural_messages_fail_with_explicit_compatibility_error(self):
        (self.english / 'src/plural.j2').write_text('{{ ngettext("one item", "many items", 2) }}',
                                                  encoding='utf-8')
        path = self.base / 'plural.po'
        po = polib.POFile()
        po.metadata = {'Language': 'fr'}
        po.save(str(path))
        with self.assertRaisesRegex(ValueError, 'Plural messages are not supported'):
            validate(path, self.english)


if __name__ == '__main__':
    unittest.main()
