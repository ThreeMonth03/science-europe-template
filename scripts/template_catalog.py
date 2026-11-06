"""English-template catalog extraction, using the official DSW implementation.

This module owns source discovery and template identity, not translations.  A
working tree may be checked while editing; publishing a POT additionally needs
the clean, committed source enforced by :mod:`export_pot`.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace

from dsw.templating.pot import ExtractionResult, extract_catalog

ROOT = Path(__file__).resolve().parents[1]
JINJA_SUFFIXES = frozenset({'.j2', '.jinja', '.jinja2', '.jnj'})


@dataclass(frozen=True)
class TemplateCatalog:
    root: Path
    coordinate: str
    files: tuple[str, ...]
    result: ExtractionResult


def extract_template_catalog(english=ROOT):
    """Extract all marked English messages, failing closed on invalid sources."""
    root = Path(english).resolve()
    try:
        metadata = json.loads((root / 'template.json').read_text(encoding='utf-8'))
        identity = [metadata[key] for key in ('organizationId', 'templateId', 'version')]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f'Cannot read template identity from {root / "template.json"}: {exc}') from exc
    if metadata.get('language') != 'en':
        raise ValueError('English template source must declare language="en" in template.json')
    if any(not isinstance(value, str) or not value.strip() or ':' in value or '\n' in value
           for value in identity):
        raise ValueError('Template organizationId, templateId and version must be nonempty coordinate components')
    paths = sorted(path for path in (root / 'src').rglob('*')
                   if path.is_file() and path.suffix in JINJA_SUFFIXES)
    if not paths:
        raise ValueError(f'No supported Jinja source files found in {root / "src"}')
    try:
        files = [SimpleNamespace(file_name=path.relative_to(root).as_posix(),
                                 content=path.read_text(encoding='utf-8')) for path in paths]
    except (OSError, UnicodeError) as exc:
        raise ValueError(f'Cannot read English template source: {exc}') from exc
    result = extract_catalog(files, project=':'.join(identity[:2]), version=identity[2], language='en')
    if result.failed_files:
        raise ValueError('Cannot export an incomplete catalog; Jinja parsing failed: '
                         + ', '.join(result.failed_files))
    if not any(message.id for message in result.catalog):
        raise ValueError('English template contains no marked translation messages')
    return TemplateCatalog(root=root, coordinate=':'.join(identity),
                           files=tuple(file.file_name for file in files), result=result)
