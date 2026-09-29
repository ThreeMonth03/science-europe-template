"""Fetch public test bundles from a fixed commit, never from private DSW projects."""
import hashlib
from pathlib import Path
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('https://raw.githubusercontent.com/ThreeMonth03/dsw-document-template-tool/'
          '25e339fbdfb1d20796471055790aad6a4226b6ed/fixtures/knowledge-models/')
BUNDLES = {
    'root-2.7.0.km': 'aabca6f7de8ad41cf9989afd25d4827f3de134fb8f0d965fcc6c336cfeb3e965',
    'root-zh-hant-2.7.0.km': 'a3030cb9048a8842fe43ebac9ece00011e26936111789443d85422473c4cae47',
}


def prepare(directory=ROOT / 'fixtures/knowledge-models'):
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in BUNDLES.items():
        target = directory / name
        cached = target.is_file()
        if cached:
            content = target.read_bytes()
        else:
            with urlopen(SOURCE + name, timeout=60) as response:
                content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f'Public KM checksum mismatch: {name}; existing cache was not changed')
        if not cached:
            with tempfile.NamedTemporaryFile(dir=directory, prefix=name + '.', delete=False) as temporary:
                temporary_path = Path(temporary.name)
                try:
                    temporary.write(content)
                    temporary.close()
                    temporary_path.replace(target)
                finally:
                    temporary_path.unlink(missing_ok=True)
        print(f'Public KM verified: {name}')


if __name__ == '__main__':
    prepare()
