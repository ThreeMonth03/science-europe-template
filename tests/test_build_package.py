"""English-owned package preparation, immutable source, and reproducible bytes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('standalone_english_builder', ROOT / 'scripts/build_package.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class EnglishPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / 'english'
        for path in ('src/fonts', 'src/word', 'scripts'):
            (self.source / path).mkdir(parents=True, exist_ok=True)
        self.metadata = dict(organizationId='example', templateId='template', version='1.2.3',
                             language='en', formats=[])
        files = {
            'template.json': json.dumps(self.metadata),
            'LICENSE': 'Template license\n',
            'PACKAGE_README.md': 'Stable package documentation\n',
            'README.md': 'Repository navigation only\n',
            '.gitignore': 'outputs/\n__pycache__/\n',
            'src/main.j2': 'Original English template\n',
            'src/fonts/NotoSansTC-Variable.ttf': 'Opaque font fixture\n',
            'src/fonts/OFL.txt': 'Font fixture license\n',
            'src/layout.css': 'Original styles\n',
            'src/word/reference.docx': 'Opaque reference fixture\n',
            'scripts/prepare_layout.py': '''import argparse
from pathlib import Path
import shutil
parser = argparse.ArgumentParser()
parser.add_argument('--template', type=Path, required=True)
parser.add_argument('--font', type=Path, required=True)
parser.add_argument('--language', required=True)
args = parser.parse_args()
assert args.language == 'en'
shutil.copyfile(args.font, args.template / 'src/fonts/PilotTC.ttf')
with (args.template / 'src/layout.css').open('a') as stream:
    stream.write('Prepared exactly once\\n')
''',
        }
        for name, content in files.items():
            (self.source / name).write_text(content, encoding='utf-8')
        shutil.copyfile(ROOT / 'scripts/build_package.py', self.source / 'scripts/build_package.py')
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'English package test')
        self.git('config', 'user.email', 'package@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.commit(1)
        self.tdk = self.base / 'fake-tdk'
        self.tdk.write_text(f'#!{sys.executable}\n' + '''import json
import os
from pathlib import Path
import sys
import uuid
import zipfile
if sys.argv[1:] == ['--version']:
    print('DSW TDK version 4.35.0')
    raise SystemExit(0)
assert sys.argv[1:3] == ['--no-config', '--no-dot-env']
operation = sys.argv[3]
print(operation + ' stdout')
print(operation + ' stderr', file=sys.stderr)
if os.environ.get('FAKE_MUTATE_SOURCE'):
    Path(os.environ['FAKE_MUTATE_SOURCE']).write_text('Changed during build\\n')
if os.environ.get('FAKE_FAIL_OPERATION') == operation:
    raise SystemExit(7)
if operation == 'package':
    prepared, output = Path(sys.argv[4]), Path(sys.argv[-1])
    payload = json.loads((prepared / 'template.json').read_text())
    payload.update(id='example:template:1.2.3', createdAt=str(uuid.uuid4()),
                   updatedAt=str(uuid.uuid4()), files=[], assets=[])
    with zipfile.ZipFile(output, 'w') as archive:
        for path in sorted((prepared / 'src').rglob('*')):
            if path.is_file():
                name = path.relative_to(prepared).as_posix()
                item = dict(fileName=name, uuid=str(uuid.uuid4()))
                if path.suffix == '.j2':
                    item['content'] = path.read_text()
                    payload['files'].append(item)
                else:
                    payload['assets'].append(item)
                    archive.writestr('template/assets/' + name, path.read_bytes())
        archive.writestr('template/template.json', json.dumps(payload))
''', encoding='utf-8')
        self.tdk.chmod(0o755)

    def git(self, *arguments, env=None):
        return subprocess.check_output(
            ['git', '-C', str(self.source), '-c', 'core.hooksPath=/dev/null', *arguments],
            text=True, stderr=subprocess.PIPE, env=env,
        ).strip()

    def commit(self, day):
        self.git('add', '.')
        date = f'2026-01-{day:02d}T00:00:00Z'
        self.git('commit', '--quiet', '-m', f'Package fixture {day}',
                 env={**os.environ, 'GIT_AUTHOR_DATE': date, 'GIT_COMMITTER_DATE': date})

    def test_package_uses_english_assets_and_stable_docs_without_mutating_source(self):
        before = builder._source_state(self.source)
        output = self.base / 'build'
        output.mkdir()
        (output / 'unrelated.txt').write_text('Keep unrelated orchestration inputs')
        report = builder.build_package(self.source, output, self.tdk)
        self.assertEqual('2026-01-01T00:00:00Z', report['package_timestamp'])
        self.assertEqual({'executable': str(self.tdk), 'version': '4.35.0'}, report['tdk'])
        self.assertEqual(before, builder._source_state(self.source))
        prepared = output / 'en'
        self.assertEqual((self.source / 'PACKAGE_README.md').read_bytes(), (prepared / 'README.md').read_bytes())
        self.assertEqual(self.metadata, json.loads((prepared / 'template.json').read_text()))
        for name in ('NotoSansTC-Variable.ttf', 'OFL.txt'):
            self.assertEqual((self.source / 'src/fonts' / name).read_bytes(),
                             (prepared / 'src/fonts' / name).read_bytes())
        self.assertEqual((self.source / 'src/fonts/NotoSansTC-Variable.ttf').read_bytes(),
                         (prepared / 'src/fonts/PilotTC.ttf').read_bytes())
        self.assertEqual(1, (prepared / 'src/layout.css').read_text().count('Prepared exactly once'))
        self.assertTrue((output / 'unrelated.txt').exists())
        for operation in ('verify', 'package'):
            self.assertEqual(f'{operation} stdout\n{operation} stderr\n',
                             (output / f'english-{operation}.log').read_text())

    def test_repeated_packages_have_identical_bytes(self):
        for name in ('first', 'second'):
            builder.build_package(self.source, self.base / name, self.tdk)
        self.assertEqual((self.base / 'first/english.zip').read_bytes(),
                         (self.base / 'second/english.zip').read_bytes())

    def test_refuses_existing_package_targets_including_dangling_symlinks(self):
        for name in builder.PACKAGE_OUTPUT_PATHS:
            with self.subTest(target=name):
                output = self.base / name.replace('.', '-')
                output.mkdir()
                target = output / name
                target.symlink_to(self.base / 'missing-target')
                with self.assertRaises(FileExistsError):
                    builder.build_package(self.source, output, self.tdk)
                self.assertTrue(target.is_symlink())
                self.assertEqual([target], list(output.iterdir()))

    def test_navigation_readme_cannot_replace_package_documentation(self):
        package = self.source / 'PACKAGE_README.md'
        package.unlink()
        with self.assertRaisesRegex(ValueError, 'Non-empty package README'):
            builder.package_readme(self.source)
        package.write_text(' \n')
        with self.assertRaises(ValueError):
            builder.package_readme(self.source)

    def test_only_existing_package_input_paths_advance_timestamp(self):
        first = builder.package_timestamp(self.source)
        (self.source / 'README.md').write_text('Changed navigation')
        self.commit(2)
        self.assertEqual(first, builder.package_timestamp(self.source))
        with (self.source / 'scripts/build_package.py').open('a') as stream:
            stream.write('\n# Packaging ownership change, not changed output.\n')
        self.commit(3)
        self.assertEqual(first, builder.package_timestamp(self.source))
        for day, name in ((4, 'scripts/prepare_layout.py'), (5, 'src/main.j2'),
                          (6, 'PACKAGE_README.md'), (7, 'LICENSE')):
            with (self.source / name).open('a') as stream:
                stream.write('\nChanged package input\n')
            self.commit(day)
            self.assertEqual(f'2026-01-{day:02d}T00:00:00Z', builder.package_timestamp(self.source))

    def test_shallow_history_is_rejected_until_unshallow_fetch(self):
        (self.source / 'README.md').write_text('Navigation-only commit')
        self.commit(2)
        shallow = self.base / 'shallow'
        subprocess.run(['git', 'clone', '--quiet', '--depth', '1', self.source.as_uri(), str(shallow)],
                       check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, 'Full English history required'):
            builder.package_timestamp(shallow)
        subprocess.run(['git', '-C', str(shallow), 'fetch', '--quiet', '--unshallow'],
                       check=True, capture_output=True)
        self.assertEqual(builder.package_timestamp(self.source), builder.package_timestamp(shallow))

    def test_tdk_failures_keep_logs_and_do_not_run_later_operations(self):
        for operation in ('verify', 'package'):
            with self.subTest(operation=operation), patch.dict(os.environ, {'FAKE_FAIL_OPERATION': operation}):
                output = self.base / f'failed-{operation}'
                with self.assertRaisesRegex(ValueError, f'TDK english-{operation} failed'):
                    builder.build_package(self.source, output, self.tdk)
                self.assertIn(operation + ' stderr', (output / f'english-{operation}.log').read_text())
                self.assertFalse((output / 'english.zip').exists())
                if operation == 'verify':
                    self.assertFalse((output / 'english-package.log').exists())

    def test_source_change_is_detected_even_if_checkout_was_already_dirty(self):
        source = self.source / 'src/main.j2'
        source.write_text('Dirty preview before build\n')
        with patch.dict(os.environ, {'FAKE_MUTATE_SOURCE': str(source)}):
            with self.assertRaisesRegex(ValueError, 'checkout state changed during build'):
                builder.build_package(self.source, self.base / 'changed', self.tdk)

    def test_standalone_command_requires_explicit_dirty_preview(self):
        (self.source / 'src/main.j2').write_text('Dirty preview source\n')
        output = self.base / 'preview'
        command = [sys.executable, str(self.source / 'scripts/build_package.py'),
                   '--output', str(output), '--tdk', str(self.tdk)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('use --preview', result.stderr)
        self.assertFalse(output.exists())
        result = subprocess.run([*command, '--preview'], text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('4.35.0', json.loads(result.stdout)['tdk']['version'])
        self.assertTrue((output / 'english.zip').exists())

    def test_standalone_command_refuses_existing_directory_and_symlink(self):
        existing = self.base / 'existing'
        existing.mkdir()
        sentinel = existing / 'sentinel.txt'
        sentinel.write_text('Keep existing output\n')
        link = self.base / 'dangling'
        link.symlink_to(self.base / 'missing')
        for output in (existing, link):
            with self.subTest(output=output):
                result = subprocess.run(
                    [sys.executable, str(self.source / 'scripts/build_package.py'),
                     '--output', str(output), '--tdk', str(self.tdk)], text=True, capture_output=True,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn('output directory already exists', result.stderr)
        self.assertEqual('Keep existing output\n', sentinel.read_text())
        self.assertTrue(link.is_symlink())

    def test_output_cannot_overlap_source_inputs(self):
        before = builder._source_state(self.source)
        for output in (self.source, self.source / 'src/generated', self.source / 'scripts/generated'):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'outside source inputs'):
                builder.build_package(self.source, output, self.tdk)
        self.assertEqual(before, builder._source_state(self.source))
        self.assertFalse((self.source / 'src/generated').exists())
        self.assertFalse((self.source / 'scripts/generated').exists())
        # Ignored local build artifacts remain the supported in-repository path.
        builder.build_package(self.source, self.source / 'outputs/local', self.tdk)
        self.assertEqual(before, builder._source_state(self.source))

    def test_tdk_selection_and_invalid_provenance(self):
        self.assertEqual(self.tdk, builder.select_tdk(self.tdk))
        with patch.object(builder.sys, 'executable', str(self.base / 'environment/bin/python')):
            self.assertEqual(self.base / 'environment/bin/dsw-tdk', builder.select_tdk())
        with patch.object(builder.subprocess, 'check_output', return_value='Unidentified executable'):
            with self.assertRaisesRegex(ValueError, 'Cannot identify TDK version'):
                builder.tdk_provenance(self.tdk)

    def test_canonicalization_preserves_deterministic_metadata_and_member_order(self):
        for number in (1, 2):
            path = self.base / f'{number}.zip'
            payload = dict(id='example:template:1.2.3', createdAt=str(number), updatedAt=str(number),
                           files=[dict(fileName='src/main.j2', uuid=str(number), content='Hello')], assets=[])
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('z.txt', 'Last')
                archive.writestr('template/template.json', json.dumps(payload))
            builder.canonicalize_zip(path, '2026-01-01T00:00:00Z')
        self.assertEqual((self.base / '1.zip').read_bytes(), (self.base / '2.zip').read_bytes())
        with zipfile.ZipFile(self.base / '1.zip') as archive:
            self.assertEqual(sorted(archive.namelist()), archive.namelist())
            self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))


if __name__ == '__main__':
    unittest.main()
