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
    # Stock DSW 4.35 passes Babel's pgettext keyword mapping ((1, 'c'), 2)
    # through to Catalog.add(context=...). Match the PO context as well as its
    # English message; identical English in different contexts is intentional.
    # None is the original gettext namespace, not an empty-string context.
    keys = [(entry.msgctxt, entry.msgid) for entry in live]
    assert len(keys) == len(set(keys)), 'Duplicate active (msgctxt, msgid) pairs'
    marked = {(message.context, message.id) for message in extracted.catalog if message.id}
    describe = lambda pairs: [dict(msgctxt=context, msgid=msgid) for context, msgid in
                             sorted(pairs, key=lambda pair: (pair[0] is not None, pair[0] or '', pair[1]))]
    assert marked == set(keys), {'missing': describe(marked - set(keys)), 'obsolete': describe(set(keys) - marked)}
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
        assert not Message(entry.msgid, entry.msgstr, flags=['python-format'], context=entry.msgctxt).check(), entry.msgid
    return {'passed': True, 'marked_messages': len(keys), 'parsed_template_files': len(files),
            'contexted_messages': sum(context is not None for context, _ in keys),
            'uncontexted_messages': sum(context is None for context, _ in keys),
            'dsw_templating': importlib.metadata.version('dsw-templating'),
            'coverage': 'All marked messages only; not a complete Chinese locale.'}


if __name__ == '__main__':
    print(json.dumps(validate(ROOT / 'locales/zh-Hant.po'), ensure_ascii=False))
