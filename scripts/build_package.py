"""Prepare and package the English template without importing translation tooling.

Layout preparation operates only on a disposable copy.  The public Python API
is also used by the Chinese repository's bilingual delivery orchestration.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INPUT_PATHS = ('template.json', 'src', 'scripts/prepare_layout.py', 'PACKAGE_README.md', 'LICENSE')
PACKAGE_OUTPUT_PATHS = ('en', 'english.zip', 'english-verify.log', 'english-package.log')


def _git(source: Path, *arguments: str) -> str:
    try:
        return subprocess.check_output(
            ['git', '-C', str(source), *arguments], text=True, stderr=subprocess.PIPE,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f'Identified English Git checkout required: {source}') from exc


def package_readme(root: Path) -> Path:
    path = root / 'PACKAGE_README.md'
    if not path.is_file() or not path.read_text(encoding='utf-8').strip():
        raise ValueError(f'Non-empty package README required: {path}')
    return path


def package_timestamp(source: Path) -> str:
    # Navigation docs, tests and review archives are not package inputs.  A
    # shallow boundary falsely makes a tests-only commit modify the whole tree.
    if _git(source, 'rev-parse', '--is-shallow-repository') != 'false':
        raise ValueError('Full English history required for reproducible package timestamps; fetch with --unshallow or use fetch-depth: 0')
    value = _git(source, 'log', '-1', '--format=%cI', 'HEAD', '--', *PACKAGE_INPUT_PATHS)
    if not value:
        raise ValueError('No committed English package inputs found')
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def canonicalize_zip(path: Path, timestamp: str) -> None:
    """Retain the existing byte contract for package metadata and archive order."""
    result = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(result, 'w') as target:
        for name in sorted(source.namelist()):
            content = source.read(name)
            if name == 'template/template.json':
                payload = json.loads(content)
                payload['createdAt'] = payload['updatedAt'] = timestamp
                for kind in ('files', 'assets'):
                    for item in payload[kind]:
                        item['uuid'] = str(uuid.uuid5(
                            uuid.NAMESPACE_URL,
                            f"dsw-template/{payload['id']}/{kind}/{item['fileName']}",
                        ))
                    payload[kind].sort(key=lambda item: item['fileName'])
                content = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, content)
    path.write_bytes(result.getvalue())


def select_tdk(override: Path | None = None) -> Path:
    """Use the current Python environment unless an executable is supplied."""
    executable = override if override is not None else Path(sys.executable).with_name('dsw-tdk')
    return Path(shutil.which(str(executable)) or executable).resolve()


def tdk_provenance(executable: Path) -> dict:
    output = subprocess.check_output([str(executable), '--version'], text=True).strip()
    match = re.search(r'\bversion\s+(\S+)\s*$', output)
    if match is None:
        raise ValueError(f'Cannot identify TDK version: {executable}')
    return {'executable': str(executable), 'version': match.group(1)}


def _source_state(source: Path) -> dict:
    if Path(_git(source, 'rev-parse', '--show-toplevel')).resolve() != source:
        raise ValueError('English source must be the root of its Git checkout')
    commit = _git(source, 'rev-parse', '--verify', 'HEAD^{commit}')
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
        raise ValueError('Identified English Git commit required')
    paths = []
    for name in PACKAGE_INPUT_PATHS:
        path = source / name
        if path.is_dir():
            paths.extend(item for item in path.rglob('*') if item.is_file())
        elif path.is_file():
            paths.append(path)
        else:
            raise ValueError(f'English package input is missing: {path}')
    return {
        'commit': commit,
        'status': _git(source, 'status', '--porcelain', '--untracked-files=all'),
        'inputs': {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(paths)},
    }


def build_package(source: Path, output: Path, tdk: Path) -> dict:
    """Build into fresh targets inside ``output`` without modifying ``source``.

    The caller owns release/preview policy; this API accepts an unchanged dirty
    preview checkout.  The standalone command below requires explicit preview.
    """
    source, output = Path(source).resolve(), Path(output).absolute()
    resolved_output = output.resolve()
    if resolved_output.is_relative_to(source) and not resolved_output.is_relative_to(source / 'outputs'):
        raise ValueError('English package output must be outside source inputs; use outputs/ or an external directory')
    for name in PACKAGE_OUTPUT_PATHS:
        if os.path.lexists(output / name):
            raise FileExistsError(f'English package output already exists: {output / name}')
    before = _source_state(source)
    metadata = json.loads((source / 'template.json').read_text(encoding='utf-8'))
    if metadata.get('language') != 'en':
        raise ValueError('English template source must declare language="en"')
    readme = package_readme(source)
    timestamp = package_timestamp(source)
    tdk = Path(tdk).resolve()
    actual_tdk = tdk_provenance(tdk)
    font = source / 'src/fonts/NotoSansTC-Variable.ttf'
    licenses = sorted(font.parent.glob('*.txt'))
    if not font.is_file() or not licenses:
        raise ValueError('English source must provide the bundled CJK font and font license')

    output.mkdir(parents=True, exist_ok=True)
    prepared = output / 'en'
    prepared.mkdir()
    shutil.copytree(source / 'src', prepared / 'src')
    for filename in ('template.json', 'LICENSE'):
        shutil.copyfile(source / filename, prepared / filename)
    shutil.copyfile(readme, prepared / 'README.md')
    (prepared / 'template.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    subprocess.run([sys.executable, str(source / 'scripts/prepare_layout.py'),
                    '--template', str(prepared), '--font', str(font), '--language', 'en'], check=True)
    for license_file in licenses:
        shutil.copyfile(license_file, prepared / 'src/fonts' / license_file.name)

    def tdk_run(label: str, *arguments: str | Path) -> None:
        result = subprocess.run([str(tdk), '--no-config', '--no-dot-env', *map(str, arguments)],
                                capture_output=True, text=True)
        log = output / (label + '.log')
        with log.open('x', encoding='utf-8') as stream:
            stream.write(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError(f'TDK {label} failed; see {log}')

    tdk_run('english-verify', 'verify', prepared)
    tdk_run('english-package', 'package', prepared, '--output', output / 'english.zip')
    canonicalize_zip(output / 'english.zip', timestamp)
    if _source_state(source) != before:
        raise ValueError('English input checkout state changed during build; discard this package')
    return {'package_timestamp': timestamp, 'tdk': actual_tdk}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Build directory with fresh package targets')
    parser.add_argument('--tdk', type=Path, help='DSW TDK executable (defaults to the current Python environment)')
    parser.add_argument('--preview', action='store_true', help='Explicitly allow an uncommitted source preview')
    args = parser.parse_args()
    try:
        if os.path.lexists(args.output):
            raise FileExistsError(f'English package output directory already exists; choose a new path: {args.output}')
        if _source_state(ROOT)['status'] and not args.preview:
            raise ValueError('Clean English checkout required; commit pending changes or use --preview')
        result = build_package(ROOT, args.output, select_tdk(args.tdk))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'English package build failed: {exc}\n')
    print(json.dumps({'output': str(args.output.absolute()), **result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
