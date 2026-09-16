"""Permit only the reviewed three-column Word width change, never text/styles."""
import copy
from lxml import etree

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(name): return '{'+W+'}'+name
def xml(node): return etree.tostring(node,method='c14n',exclusive=True)
OLD=[4514,1346,2059]
NEW=[3880,1980,2059]


def compare_blocks(before,after):
    assert len(before)==len(after)
    changed=0
    for left,right in zip(before,after):
        if xml(left)==xml(right):continue
        assert left.tag==right.tag==q('tbl'),'Only table column widths may change'
        old=left.find(q('tblGrid'));new=right.find(q('tblGrid'))
        assert [int(c.get(q('w'))) for c in old]==OLD
        assert [int(c.get(q('w'))) for c in new]==NEW
        restored=copy.deepcopy(right)
        grid=restored.find(q('tblGrid'));restored.replace(grid,copy.deepcopy(old))
        assert xml(left)==xml(restored),'Other table XML changed'
        changed+=1
    return changed


def compare_ast(before,after):
    if before==after:return 0
    if isinstance(before,dict) and isinstance(after,dict):
        if before.get('t')==after.get('t')=='Table':
            restored=copy.deepcopy(after)
            classes=before['c'][0][1]
            assert 'resource-table' in classes and 'word-short-budget' in classes
            spec=lambda values:[[{'t':'AlignLeft'},{'t':'ColWidth','c':v}] for v in values]
            assert before['c'][2]==spec([.57,.17,.26])
            assert after['c'][2]==spec([.49,.25,.26])
            restored['c'][2]=before['c'][2]
            assert restored==before,'Other table AST changed'
            return 1
        assert before.keys()==after.keys()
        return sum(compare_ast(before[k],after[k]) for k in before)
    if isinstance(before,list) and isinstance(after,list):
        assert len(before)==len(after)
        return sum(compare_ast(a,b) for a,b in zip(before,after))
    raise AssertionError('Unexpected AST change')
