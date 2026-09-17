"""Exact reversible 0.3.34 -> joined Q5 Word delta; no relaxed historic gates."""
import copy
from lxml import etree as ET

OLD = '''  policy.content[1] = pandoc.Div({paragraphs[1]}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Lead"}))
  limits.content[1] = pandoc.Div({paragraphs[2]}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Lead"}))
'''
NEW = '''  -- BEGIN joined Q5 Word lead
  -- One bounded owned paragraph, with a visible line boundary before limitations.
  -- Keep the independent HTML facts and all authored/long fallbacks unchanged.
  local joined = pandoc.List()
  joined:extend(paragraphs[1].content)
  joined:insert(pandoc.LineBreak())
  joined:extend(paragraphs[2].content)
  policy.content[1] = pandoc.Div({pandoc.Para(joined)}, pandoc.Attr("", {}, {["custom-style"] = "Pilot Lead"}))
  -- END joined Q5 Word lead
'''
REMOVE = '''  -- BEGIN remove joined Q5 introduction
  limits.content:remove(1)
  -- END remove joined Q5 introduction
'''
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def prior_lua(source):
    assert source.count(NEW) == source.count(REMOVE) == 1, 'Missing/changed/duplicate Q5 join delta'
    assert OLD not in source
    return source.replace(NEW, OLD).replace(REMOVE, '')


def xml(node):
    return ET.tostring(node, method='c14n', exclusive=True)


def expected_ast(before):
    result = copy.deepcopy(before)
    found = []
    def walk(node):
        if isinstance(node, dict):
            if node.get('t') == 'Div' and node['c'][0][0] == 'q-store-backup': found.append(node)
            for child in node.values(): walk(child)
        elif isinstance(node, list):
            for child in node: walk(child)
    walk(result)
    assert len(found) == 1
    heading, answer = found[0]['c'][1]
    assert heading['t'] == 'Header' and answer['t'] == 'Div'
    assert 'q5-short-context' in answer['c'][0][1]
    policy, limits = answer['c'][1]
    assert 'workspace-policy' in policy['c'][0][1] and 'storage-detail-limits' in limits['c'][0][1]
    lead, = policy['c'][1]
    intro, items = limits['c'][1]
    assert items['t'] == 'BulletList' and len(items['c']) == 2
    for paragraph in (lead, intro):
        assert paragraph['t'] == 'Div' and paragraph['c'][0] == ['', [], [['custom-style', 'Pilot Lead']]]
        assert len(paragraph['c'][1]) == 1 and paragraph['c'][1][0]['t'] == 'Para'
        assert all(i['t'] in ('Str', 'Space', 'SoftBreak') for i in paragraph['c'][1][0]['c'])
    lead['c'][1][0]['c'] += [{'t': 'LineBreak'}] + intro['c'][1][0]['c']
    limits['c'][1].pop(0)
    return result


def check_ast(before, after, selected):
    assert after == (expected_ast(before) if selected else before), 'Unexpected Q5 AST change'
    return int(selected)


def check_word(before, after, selected):
    """Require the exact old runs plus one plain line break; retain all other XML."""
    parser = ET.XMLParser(remove_blank_text=True)
    def parsed(value):
        return ET.fromstring(value if isinstance(value, (str, bytes)) else ET.tostring(value), parser)
    expected = [parsed(n) for n in before]
    actual = [parsed(n) for n in after]
    if selected:
        def lead(node):
            props = node.find(W + 'pPr')
            style = None if props is None else props.find(W + 'pStyle')
            return node.tag == W + 'p' and style is not None and style.get(W + 'val') == 'PilotLead'
        positions = [i for i in range(len(expected) - 1) if lead(expected[i]) and lead(expected[i + 1])]
        assert len(positions) == 1, 'Require exactly one adjacent owned lead pair'
        index = positions[0]; policy, intro = expected[index:index + 2]
        assert policy.attrib == intro.attrib
        assert xml(policy.find(W + 'pPr')) == xml(intro.find(W + 'pPr'))
        for paragraph in (policy, intro):
            assert paragraph.find('.//' + W + 't') is not None
            assert all(n.tag in (W + 'pPr', W + 'r') for n in paragraph), 'Unexpected rich block'
            assert not list(paragraph.iter(W + 'br')), 'Authored breaks must not join'
        run = ET.SubElement(policy, W + 'r'); ET.SubElement(run, W + 'br')
        for child in intro:
            if child.tag != W + 'pPr': policy.append(copy.deepcopy(child))
        expected.pop(index + 1)
    assert list(map(xml, expected)) == list(map(xml, actual)), 'Unexpected Word join, run, style or other XML change'
    return int(selected)
