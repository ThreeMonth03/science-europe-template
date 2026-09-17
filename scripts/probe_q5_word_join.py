"""Pinned Pandoc regression for one bounded Q5 paragraph join; not native layout QA."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from jinja2 import Environment, FileSystemLoader
from lxml import etree as ET
from probe_budget_word import ROOT, IMAGE
from probe_q8_word import RUNNER
from q5_word_join_contract import W, prior_lua, check_ast, check_word
from storage_context_contract import fragment, fragments


def cases(root):
    helper = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do']).get_template('src/storage-reading.html.j2').module
    rows = [(name, '<div id="q-store-backup"><h3>5. Storage?</h3>' + str(helper.answer(html)) + '</div>', selected)
            for name, html, selected in fragments()]
    rows += [('other-question', rows[0][1].replace('q-store-backup', 'q-other'), False),
             ('missing-hint', rows[0][1].replace(' q5-short-context', ''), False),
             ('punctuation', '<div id="q-store-backup"><h3>5. Storage?</h3>' + str(helper.answer(fragment('Keep 0 GB; Original.csv &amp; A-B.', 'Review: 0.05.', '地點未定。', 'Schedule unknown.'))) + '</div>', True)]
    rows += [(name + '-forged-hint', html.replace('class="answer"', 'class="answer q5-short-context"'), False)
             for name, html, selected in list(rows) if not selected and 'class="answer"' in html
             and (name.startswith(('ascii-', 'cjk-')) or name in ('link', 'strong', 'break', 'extra', 'archive', 'authored'))]
    multiple = fragment().replace('Policy.</p>', 'Policy.</p><p data-requirement-id="SE-3a" data-fact-id="backup-reliability" data-status="complete">Second policy.</p>')
    # The existing dataset-policy handler already joins adjacent owned facts.
    # Their original combined runs must survive this later Q5-only join too.
    rows.append(('multiple-owned-policy-facts', '<div id="q-store-backup"><h3>5. Storage?</h3>' + str(helper.answer(multiple)) + '</div>', True))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    matrix = cases(a.source_dir)
    html = ''.join('<div id="' + name + '"><h2>CASE: ' + name + '</h2>' + body + '</div>' for name, body, _ in matrix)
    lua = (a.source_dir / 'src/word/pilot.lua').read_text()
    result = []
    for code in (prior_lua(lua), lua):
        payload = dict(html=html, lua=code, reference=base64.b64encode((a.source_dir / 'src/word/reference.docx').read_bytes()).decode())
        result.append(json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER], input=json.dumps(payload).encode())))
    asts = [{block['c'][0][0]: block for block in r['ast']['blocks']} for r in result]
    def groups(r):
        grouped = {'prefix': []}; key = 'prefix'
        for block in r['word_blocks']:
            node = ET.fromstring(block); value = ''.join(n.text or '' for n in node.iter(W + 't'))
            if value.startswith('CASE: '): key = value[6:]; grouped[key] = []
            grouped[key].append(block)
        return grouped
    words = list(map(groups, result)); assert words[0]['prefix'] == words[1]['prefix']
    rows = []
    for name, _, selected in matrix:
        try:
            check_ast(asts[0][name], asts[1][name], selected)
            count = check_word(words[0][name], words[1][name], selected)
        except AssertionError as error:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(dict(passed=False, case=name, selected=selected, release_acceptance=False,
                error=str(error), before=asts[0][name], after=asts[1][name], word_before=words[0][name], word_after=words[1][name]), indent=2) + '\n')
            raise AssertionError((name, str(error))) from error
        rows.append(dict(case=name, selected=selected, joined_pairs=count, passed=True))
    digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    report = dict(passed=True, release_acceptance=False, rows=rows, worker_image=IMAGE,
                  checker_sha256=digest(Path(__file__)), contract_sha256=digest(ROOT / 'scripts/q5_word_join_contract.py'),
                  lua_sha256=digest(a.source_dir / 'src/word/pilot.lua'),
                  limits=['Pinned AST/DOCX structure only; native PDF/Word and Microsoft Word acceptance remain separate'])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, cases=len(rows), joined_pairs=sum(r['joined_pairs'] for r in rows))))


if __name__ == '__main__': main()
