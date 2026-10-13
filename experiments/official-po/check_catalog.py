"""Run with stock DSW 4.35 dependencies; validate the marked, partial PO scope.

This does not claim that every human-readable template string is marked, or that
translations are semantically correct. The local prototype is not a release.
"""
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import re
from types import SimpleNamespace

import polib
from babel.messages.catalog import Message
from dsw.templating.pot import extract_catalog

ROOT = Path(__file__).resolve().parents[2]


def validate(po_path):
    files = [SimpleNamespace(file_name=str(p.relative_to(ROOT)), content=p.read_text())
             for p in (ROOT / 'src').rglob('*')
             if p.suffix in {'.j2', '.jinja', '.jinja2', '.jnj'}]
    extracted = extract_catalog(files, project='science-europe-enhanced', version='0.3.78', language='en')
    assert not extracted.failed_files, extracted.failed_files
    po = polib.pofile(str(po_path))
    assert po.metadata['Language'] == 'zh-Hant'
    live = [entry for entry in po if not entry.obsolete]
    ids = [entry.msgid for entry in live]
    assert len(ids) == len(set(ids)), 'Duplicate active message IDs'
    marked = {m.id for m in extracted.catalog if m.id}
    assert marked == set(ids), {'missing': sorted(marked - set(ids)), 'obsolete': sorted(set(ids) - marked)}
    for entry in live:
        assert entry.msgstr.strip() and 'fuzzy' not in entry.flags, entry.msgid
        token = r'%\(([^)]+)\)([-+#0 ]*\d*(?:\.\d+)?[diouxXeEfFgGcrsa])'
        parameters = lambda value: [(m.group(1), m.group(2)) for m in re.finditer(r'%%|' + token, value) if m.group(1) is not None]
        names = lambda value: Counter(parameters(value))
        assert names(entry.msgid) == names(entry.msgstr), entry.msgid
        for value in (entry.msgid, entry.msgstr):
            # Babel permits some bare-percent strings that fail newstyle gettext
            # at runtime. Only named printf parameters and escaped %% are valid.
            assert '%' not in re.sub(r'%%|' + token, '', value), entry.msgid
            bindings = {name: ('example' if conversion[-1] in 'sra' else 'A' if conversion[-1] == 'c' else 7)
                        for name, conversion in parameters(value)}
            value % bindings
        assert not Message(entry.msgid, entry.msgstr, flags=['python-format']).check(), entry.msgid
    return {'passed': True, 'marked_messages': len(ids), 'parsed_template_files': len(files),
            'dsw_templating': importlib.metadata.version('dsw-templating'),
            'coverage': 'All marked messages only; not a complete Chinese locale.'}


if __name__ == '__main__':
    print(json.dumps(validate(ROOT / 'locales/zh-Hant.po'), ensure_ascii=False))
