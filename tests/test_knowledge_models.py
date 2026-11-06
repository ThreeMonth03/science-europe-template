"""The English repository owns fixed public KM fixtures; no download fallback."""
import contextlib
import hashlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_knowledge_models import BUNDLES, prepare


class KnowledgeModelFixtureTests(unittest.TestCase):
    def test_vendored_bundles_match_the_original_checksums_without_rewriting(self):
        directory = ROOT / 'fixtures/knowledge-models'
        before = {name: (hashlib.sha256((directory / name).read_bytes()).hexdigest(),
                         (directory / name).stat().st_mtime_ns) for name in BUNDLES}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            prepare(directory)
        for name, expected in BUNDLES.items():
            self.assertEqual(expected, before[name][0])
            self.assertEqual(before[name], (hashlib.sha256((directory / name).read_bytes()).hexdigest(),
                                          (directory / name).stat().st_mtime_ns))
            self.assertIn('Public KM verified: ' + name, output.getvalue())

    def test_missing_directory_is_not_created_or_populated(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'missing'
            with self.assertRaisesRegex(FileNotFoundError, 'Missing vendored public KM fixture'):
                prepare(directory)
            self.assertFalse(directory.exists())

    def test_missing_bundle_is_not_downloaded_or_restored(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first, missing = BUNDLES
            shutil.copyfile(ROOT / 'fixtures/knowledge-models' / first, directory / first)
            original = (directory / first).read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(FileNotFoundError, missing):
                    prepare(directory)
            self.assertEqual(original, (directory / first).read_bytes())
            self.assertFalse((directory / missing).exists())

    def test_corrupt_bundle_is_rejected_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            name = next(iter(BUNDLES))
            target = directory / name
            original = b'Corrupt local fixture: do not replace.'
            target.write_bytes(original)
            with self.assertRaisesRegex(ValueError, 'Public KM checksum mismatch: ' + name):
                prepare(directory)
            self.assertEqual(original, target.read_bytes())
            self.assertEqual([name], [path.name for path in directory.iterdir()])


if __name__ == '__main__':
    unittest.main()
