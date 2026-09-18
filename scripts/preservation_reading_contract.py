"""Exact, independently projected Q11 label delta; preserve all other AST/XML."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '3c4827a440ab148aca815b6830dab7dc1469d0b1'
FILTER = 'src/word/preservation-reading.lua'
STYLE = 'PilotPreservationSummary'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
STYLE_BLOCK = '''    # BEGIN bounded preservation label style
    preservation = document.styles.add_style("Pilot Preservation Summary", WD_STYLE_TYPE.PARAGRAPH)
    preservation.base_style = document.styles["Body Text"]
    preservation.paragraph_format.keep_with_next = False
    preservation.paragraph_format.keep_together = True
    # END bounded preservation label style
'''


def historic(path): return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE+':'+path])


def source_delta():
    old = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', BASELINE, 'src'], text=True).splitlines()
    current = {str(p.relative_to(ROOT)) for p in (ROOT/'src').rglob('*') if p.is_file()}
    assert current-set(old) == {FILTER} and not set(old)-current
    for name in old: assert (ROOT/name).read_bytes() == historic(name), name
    before = json.loads(historic('template.json')); after = json.loads((ROOT/'template.json').read_text())
    assert before['version'] == '0.3.38'; before['version'] = '0.3.39'
    selected = 0
    for fmt in before['formats']:
        for step in fmt['steps']:
            if step['name'] == 'pandoc' and step['options'].get('to') == 'docx':
                args = step['options']['args']; anchor = '--lua-filter=src/word/pilot.lua'
                assert args.count(anchor) == 1
                step['options']['args'] = args.replace(anchor, anchor+' --lua-filter='+FILTER)
                selected += 1
    assert selected == 2 and before == after, 'Only both Word filter chains and version may change'
    preparation = (ROOT/'scripts/prepare_layout.py').read_text()
    assert preparation.count(STYLE_BLOCK) == 1
    assert preparation.replace(STYLE_BLOCK, '').encode() == historic('scripts/prepare_layout.py')
    return dict(baseline=BASELINE, version='0.3.39', new_source=FILTER,
        filter_sha256=hashlib.sha256((ROOT/FILTER).read_bytes()).hexdigest(),
        style_block_sha256=hashlib.sha256(STYLE_BLOCK.encode()).hexdigest())


def old_reference(root, language):
    """Rebuild the frozen pre-change reference without changing current files."""
    with tempfile.TemporaryDirectory(prefix='preservation-prior-reference-') as temp:
        folder = Path(temp); (folder/'src/word').mkdir(parents=True)
        (folder/'src/word/reference.docx').write_bytes(historic('src/word/reference.docx'))
        (folder/'src/layout.css').write_bytes(historic('src/layout.css'))
        namespace = {'__name__': 'frozen_reference_preparation'}
        exec(compile(historic('scripts/prepare_layout.py'), BASELINE+'/scripts/prepare_layout.py', 'exec'), namespace)
        font = root/'src/fonts/PilotTC.ttf'
        if not font.is_file():
            font = folder/'reference-only-font.ttf'; font.write_bytes(b'Not rendered; reference preparation only')
        namespace['prepare_layout'](folder, font, language)
        return (folder/'src/word/reference.docx').read_bytes()


def project_prepared(root, actual_hashes, language):
    """Verify new files/style, then present exact old hashes to historic gates."""
    source_delta()
    assert (root/FILTER).read_bytes() == (ROOT/FILTER).read_bytes(), 'Translated filter must remain identical'
    before = old_reference(root, language)
    prior_reference(before, (root/'src/word/reference.docx').read_bytes())
    result = dict(actual_hashes)
    assert result.pop(FILTER) == hashlib.sha256((ROOT/FILTER).read_bytes()).hexdigest()
    result['src/word/reference.docx'] = hashlib.sha256(before).hexdigest()
    return result


def xml(node): return E.tostring(node, method='c14n', exclusive=True)


def expected_ast(before, identifiers):
    result = copy.deepcopy(before); seen = []
    def visit(value):
        if isinstance(value, dict):
            if value.get('t') == 'Div' and value['c'][0][0] == 'q-data-preservation':
                for answer in value['c'][1]:
                    if answer['t'] != 'Div' or answer['c'][0][1] != ['answer']: continue
                    for dataset in answer['c'][1]:
                        if dataset['t'] != 'Div' or dataset['c'][0][1] != ['dataset-section']: continue
                        identifier = dict(dataset['c'][0][2]).get('item-id')
                        if identifier not in identifiers: continue
                        label, policy = dataset['c'][1][:2]
                        assert label['t'] == 'Header' and label['c'][0] == 5
                        assert policy['t'] == 'Div' and policy['c'][0][1] == ['preservation-summary', 'dataset-policy']
                        summary, = policy['c'][1]; assert summary['t'] == 'Para'
                        name = label['c'][2]
                        if label['c'][1][0]: name = [{'t': 'Span', 'c': [label['c'][1], name]}]
                        para = {'t': 'Para', 'c': [{'t': 'Strong', 'c': name}, {'t': 'LineBreak'}]+summary['c']}
                        policy['c'][1] = [{'t': 'Div', 'c': [['', [], [['custom-style', 'Pilot Preservation Summary']]], [para]]}]
                        dataset['c'][1].pop(0); seen.append(identifier)
                return
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(result)
    assert sorted(seen) == sorted(identifiers), ('Missing/duplicate selected dataset', seen, identifiers)
    return result


def prior_reference(before, after):
    """Exactly one new, bounded paragraph style; every other ZIP part unchanged."""
    with zipfile.ZipFile(io.BytesIO(before)) as old, zipfile.ZipFile(io.BytesIO(after)) as new:
        assert set(old.namelist()) == set(new.namelist())
        for name in old.namelist():
            if name != 'word/styles.xml': assert old.read(name) == new.read(name), name
        first, second = [E.fromstring(z.read('word/styles.xml')) for z in (old, new)]
        assert not [s for s in first if s.get(W+'styleId') == STYLE]
        added = [s for s in second if s.get(W+'styleId') == STYLE]; assert len(added) == 1
        expected = E.fromstring(('<w:style xmlns:w="'+W[1:-1]+'" w:type="paragraph" w:customStyle="1" w:styleId="'+STYLE+'">'
            '<w:name w:val="Pilot Preservation Summary"/><w:basedOn w:val="BodyText"/><w:pPr>'
            '<w:keepNext w:val="0"/><w:keepLines/></w:pPr></w:style>').encode())
        assert xml(added[0]) == xml(expected), 'Unreviewed preservation style'
        second.remove(added[0]); assert xml(first) == xml(second), 'An existing style changed'


def text(node): return ''.join(n.text or '' for n in node.iter(W+'t'))


def selected_anchors(ast, identifiers):
    result = []
    def visit(value):
        if isinstance(value, dict):
            if value.get('t') == 'Div' and value['c'][0][1] == ['dataset-section'] and dict(value['c'][0][2]).get('item-id') in identifiers:
                heading = value['c'][1][0]; assert heading['t'] == 'Header'
                result.append(heading['c'][1][0])
                return
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(ast)
    assert len(result) == len(identifiers) and len(result) == len(set(result))
    return result


def word_anchors(ast, identifiers, document):
    """Bind by heading order; do not reimplement Pandoc's long-ID hashing."""
    selected = selected_anchors(ast, identifiers); headings = []
    def visit(value):
        if isinstance(value, dict):
            if value.get('t') == 'Header' and value['c'][0] == 5: headings.append(value['c'][1][0])
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(ast)
    paras = [p for p in E.fromstring(document).iter(W+'p') if p.find(W+'pPr/'+W+'pStyle') is not None
        and p.find(W+'pPr/'+W+'pStyle').get(W+'val') == 'Heading5']
    assert len(headings) == len(paras)
    result = []
    for anchor, para in zip(headings, paras):
        if anchor in selected:
            mark = para.getprevious(); assert mark is not None and mark.tag == W+'bookmarkStart'
            result.append(mark.get(W+'name'))
    assert len(result) == len(identifiers)
    return result


def word_content(before, after, anchors):
    """Exact runs plus bold names and one line break; preserve all other body XML.

    Pandoc moves a heading's bookmark into the new inline span. Normalize only
    those selected bookmark positions after checking their names and full set.
    """
    parser = E.XMLParser(remove_blank_text=True)
    old, new = [E.fromstring(value, parser) for value in (before, after)]
    assert [n.text for n in old.iter(W+'t')] == [n.text for n in new.iter(W+'t')]
    # Selected native IDs are output-specific counters; retain the complete
    # bookmark names, then ignore their numeric identifiers and location only
    # for the precisely selected label anchor.
    all_names = lambda root: sorted(n.get(W+'name') for n in root.iter(W+'bookmarkStart'))
    assert all_names(old) == all_names(new), 'Bookmark target lost/added'
    body, revised = old.find(W+'body'), new.find(W+'body')
    def style(p):
        node = p.find(W+'pPr/'+W+'pStyle')
        return None if node is None else node.get(W+'val')
    selected = [p for p in body if p.tag == W+'p' and style(p) == 'Heading5' and p.getprevious() is not None
        and p.getprevious().tag == W+'bookmarkStart' and p.getprevious().get(W+'name') in anchors]
    assert len(selected) == len(anchors), 'Ambiguous selected label'
    for label in selected:
        # Heading bookmark starts follow the Heading3 and precede Heading5 in
        # Pandoc output. Require the adjacent marker, never blanket-strip IDs.
        start = label.getprevious(); assert start.tag == W+'bookmarkStart'
        ident, name = start.get(W+'id'), start.get(W+'name')
        for root in (old, new):
            starts = [n for n in root.iter(W+'bookmarkStart') if n.get(W+'name') == name]
            assert len(starts) == 1
            key = starts[0].get(W+'id')
            ends = [n for n in root.iter(W+'bookmarkEnd') if n.get(W+'id') == key]
            assert len(ends) == 1
            starts[0].getparent().remove(starts[0]); ends[0].getparent().remove(ends[0])
        summary = label.getnext(); assert summary.tag == W+'p' and style(summary) == 'FirstParagraph'
        assert all(n.tag in (W+'pPr', W+'r') for n in label)
        props = label.find(W+'pPr'); props.find(W+'pStyle').set(W+'val', STYLE)
        for run in label.findall(W+'r'):
            properties = run.find(W+'rPr')
            if properties is None: properties = E.Element(W+'rPr'); run.insert(0, properties)
            assert properties.find(W+'b') is None and properties.find(W+'bCs') is None
            position = 1 if properties.find(W+'rFonts') is not None else 0
            properties.insert(position, E.Element(W+'b'))
            properties.insert(position+1, E.Element(W+'bCs'))
        E.SubElement(E.SubElement(label, W+'r'), W+'br')
        for run in list(summary):
            if run.tag != W+'pPr': label.append(run)
        body.remove(summary)
    assert xml(old) == xml(new), 'Unreviewed Word XML delta'
