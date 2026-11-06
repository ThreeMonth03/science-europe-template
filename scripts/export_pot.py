"""Publish the English POT from a clean, committed template checkout.

The official DSW extractor preserves marked messages, contexts and translator
comments.  Added metadata binds the translation source to its full template
coordinate and Git commit; no authoritative target-language PO is read here.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

import polib
from dsw.templating.pot import render_pot_file

from template_catalog import ROOT, extract_template_catalog


def _git(root, *arguments):
    try:
        return subprocess.run(['git', '-C', str(root), *arguments], check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f'English source must be a Git checkout with a committed HEAD: {root}') from exc


def _source_provenance(source):
    root = source.root
    if Path(_git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('English source must be the root of its Git checkout')
    commit = _git(root, 'rev-parse', '--verify', 'HEAD^{commit}')
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
        raise ValueError('Cannot identify the full committed English source revision')
    if _git(root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('English source checkout is dirty; commit or move pending changes before exporting a POT')
    tracked = set(_git(root, 'ls-files', '-z').split('\0'))
    required = ('template.json', *source.files)
    if any(name not in tracked or (root / name).is_symlink() for name in required):
        raise ValueError('All English template inputs must be tracked regular files, not ignored files or symlinks')
    timestamp = int(_git(root, 'show', '-s', '--format=%ct', 'HEAD'))
    return commit, datetime.fromtimestamp(timestamp, timezone.utc)


def export_pot(output, english=ROOT):
    """Create a new POT; never replace an existing file or symbolic link."""
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError(f'POT output already exists; choose a new path: {output}')
    initial_commit = _git(Path(english).resolve(), 'rev-parse', '--verify', 'HEAD^{commit}')
    source = extract_template_catalog(english)
    commit, created_at = _source_provenance(source)
    if commit != initial_commit:
        raise ValueError('English source HEAD changed during extraction; retry from a stable checkout')
    source.result.catalog.creation_date = created_at
    pot = polib.pofile(render_pot_file(source.result).decode('utf-8'))
    pot.metadata.update({'Language': 'en', 'X-DSW-Template': source.coordinate,
                         'X-DSW-Source-Commit': commit})
    data = str(pot).encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against another process publishing here.
    with output.open('xb') as stream:
        stream.write(data)
    return {'output': str(output), 'template': source.coordinate, 'source_commit': commit,
            'marked_messages': len(pot), 'parsed_template_files': len(source.files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/template.pot',
                        help='New POT path; an existing file is never overwritten')
    args = parser.parse_args()
    try:
        report = export_pot(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'POT export failed: {exc}\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
