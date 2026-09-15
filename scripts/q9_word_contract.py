"""Exact allowed Word XML projection: Q9 label keep + two plain fixed flags joined."""
import copy
from lxml import etree

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def text(node):return ''.join(t.text or '' for t in node.iter(W+'t'))


def style(node):
    p=node.find(W+'pPr');s=p.find(W+'pStyle') if p is not None else None
    return s.get(W+'val') if s is not None else None


def xml(node):return etree.tostring(node,method='c14n',exclusive=True)


def separator(left,right):return '' if ord(left[-1])>=0x2E80 and ord(right[0])>=0x2E80 else ' '


def set_style(node,name):
    props=node.find(W+'pPr');assert props is not None
    s=props.find(W+'pStyle');assert s is not None;s.set(W+'val',name)


def set_plain_text(node,value):
    assert node.tag==W+'p' and [n.tag for n in node]==[W+'pPr',W+'r']
    run=node.find(W+'r');assert [n.tag for n in run] in [[W+'t'],[W+'rPr',W+'t']]
    props=run.find(W+'rPr')
    if props is not None:
        assert len(props)==1 and props[0].tag==W+'rFonts' and props[0].attrib=={W+'hint':'eastAsia'}
    run.find(W+'t').text=value


def expected_blocks(blocks,groups):
    """No content outside each named Q9 group can change, including tables."""
    remaining=list(groups);result=[];active=False;i=0;labels=joined=0
    while i<len(blocks):
        node=blocks[i]
        if style(node)=='Heading3':active=text(node).startswith('9. ')
        if active and remaining and text(node)==remaining[0][0]:
            name,flags=remaining.pop(0);assert 1<=len(flags)<=2
            assert node.tag==W+'p' and style(node)=='Compact'
            label=copy.deepcopy(node);set_style(label,'PilotListLead');result.append(label);labels+=1
            originals=blocks[i+1:i+1+len(flags)];assert len(originals)==len(flags)
            assert [text(n) for n in originals]==flags
            assert all(style(n) in ['Compact','PilotListLead'] for n in originals)
            if len(flags)==2:
                # Their numbering/formatting must already match; only the first
                # flag's existing keep style and literal text may differ.
                assert style(originals[-1])=='Compact'
                normalized=[]
                for n in originals:
                    c=copy.deepcopy(n);set_style(c,'Compact');set_plain_text(c,'FLAG');normalized.append(xml(c))
                assert normalized[0]==normalized[1]
                combined=copy.deepcopy(originals[-1]);set_plain_text(combined,flags[0]+separator(*flags)+flags[1]);result.append(combined);joined+=1
            else:result.extend(originals)
            i+=1+len(flags)
        else:result.append(node);i+=1
    assert not remaining,('Expected Q9 groups missing',remaining)
    return result,{'styled_labels':labels,'joined_flag_pairs':joined}
