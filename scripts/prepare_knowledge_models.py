"""Verify vendored public test bundles without downloading or changing them."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = {
    'root-2.7.0.km': 'aabca6f7de8ad41cf9989afd25d4827f3de134fb8f0d965fcc6c336cfeb3e965',
    'root-zh-hant-2.7.0.km': 'a3030cb9048a8842fe43ebac9ece00011e26936111789443d85422473c4cae47',
}


def prepare(directory=ROOT / 'fixtures/knowledge-models'):
    directory = Path(directory)
    for name, expected in BUNDLES.items():
        target = directory / name
        if not target.is_file():
            raise FileNotFoundError(f'Missing vendored public KM fixture: {target}; restore it from the English source checkout')
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Public KM checksum mismatch: {name}; vendored fixture was not changed')
        print(f'Public KM verified: {name}')


if __name__ == '__main__':
    prepare()
