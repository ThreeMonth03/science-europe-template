"""Validate current marked PO keys with official DSW 4.35 extraction.

Checks marked-message coverage and substitution safety, not linguistic quality
or native-document acceptance. Does not modify the authoritative catalog.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import re

import polib
from babel.messages.catalog import Message
from template_catalog import ROOT, extract_template_catalog


def _require(condition, message):
    if not condition:
        raise ValueError(str(message))


def _check_substitutions(entry):
    token = r'%\(([^)]+)\)([-+#0 ]*\d*(?:\.\d+)?[diouxXeEfFgGcrsa])'
    parameters = lambda value: [(m.group(1), m.group(2)) for m in re.finditer(r'%%|' + token, value)
                                if m.group(1) is not None]
    names = lambda value: Counter(parameters(value))
    _require(names(entry.msgid) == names(entry.msgstr), f'Placeholder mismatch: {entry.msgid}')
    for value in (entry.msgid, entry.msgstr):
        # Babel permits some bare-percent strings that fail newstyle gettext
        # at runtime. Only named printf parameters and escaped %% are valid.
        _require('%' not in re.sub(r'%%|' + token, '', value), f'Unsafe percent syntax: {entry.msgid}')
        bindings = {name: ('example' if conversion[-1] in 'sra' else 'A' if conversion[-1] == 'c' else 7)
                    for name, conversion in parameters(value)}
        value % bindings
    errors = Message(entry.msgid, entry.msgstr, flags=['python-format'], context=entry.msgctxt).check()
    _require(not errors, f'Invalid translation substitutions: {entry.msgid}: {errors}')


def validate(po_path, english=ROOT):
    source = extract_template_catalog(english)
    extracted = source.result
    po = polib.pofile(str(po_path))
    _require(po.metadata.get('Language', '').strip(), 'PO Language metadata is required')
    live = [entry for entry in po if not entry.obsolete]
    _require(not any(entry.msgid_plural for entry in live)
             and not any(isinstance(message.id, tuple) for message in extracted.catalog),
             'Plural messages are not supported by the current template compatibility contract')
    # Stock DSW 4.35 passes Babel's pgettext keyword mapping ((1, 'c'), 2)
    # through to Catalog.add(context=...). Match the PO context as well as its
    # English message; identical English in different contexts is intentional.
    # None is the original gettext namespace, not an empty-string context.
    keys = [(entry.msgctxt, entry.msgid) for entry in live]
    _require(len(keys) == len(set(keys)), 'Duplicate active (msgctxt, msgid) pairs')
    marked = {(message.context, message.id) for message in extracted.catalog if message.id}
    describe = lambda pairs: [dict(msgctxt=context, msgid=msgid) for context, msgid in
                             sorted(pairs, key=lambda pair: (pair[0] is not None, pair[0] or '', pair[1]))]
    _require(marked == set(keys), {'missing': describe(marked - set(keys)), 'obsolete': describe(set(keys) - marked)})
    for entry in live:
        _require(entry.msgstr.strip() and 'fuzzy' not in entry.flags,
                 f'Empty or unreviewed translation: {entry.msgid}')
        _check_substitutions(entry)
    return {'passed': True, 'marked_messages': len(keys), 'parsed_template_files': len(source.files),
            'template': source.coordinate, 'language': po.metadata['Language'],
            'contexted_messages': sum(context is not None for context, _ in keys),
            'uncontexted_messages': sum(context is None for context, _ in keys),
            'dsw_templating': importlib.metadata.version('dsw-templating'),
            'coverage': 'All marked messages only; not a linguistic or document-layout acceptance check.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--po', type=Path, required=True, help='Target-language PO catalog to validate')
    print(json.dumps(validate(parser.parse_args().po), ensure_ascii=False))
