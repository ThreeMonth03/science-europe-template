"""Small current native-test helpers; no historical package projections."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS

IMAGE = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'

RUNNER='''import json,sys,tempfile,subprocess
from pathlib import Path
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/"pilot.lua";f.write_text(p["lua"])
 print(subprocess.check_output(["pandoc","--from=html","--to=json","--lua-filter="+str(f)],input=p["html"].encode()).decode())
'''

WORD_RUNNER = '''import base64,json,sys,tempfile,subprocess,zipfile
from pathlib import Path
from xml.etree import ElementTree as E
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/"pilot.lua";f.write_text(p["lua"])
 ref=Path(tmp)/"reference.docx";ref.write_bytes(base64.b64decode(p["reference"]))
 common=["pandoc","--from=html","--lua-filter="+str(f)]
 ast=json.loads(subprocess.check_output(common+["--to=json"],input=p["html"].encode()))
 doc=Path(tmp)/"probe.docx"
 subprocess.run(common+["--to=docx","--reference-doc="+str(ref),"-o",str(doc)],input=p["html"].encode(),check=True)
 with zipfile.ZipFile(doc) as z: body=E.fromstring(z.read("word/document.xml"))
 ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
 blocks=[E.tostring(n,encoding="unicode") for n in body.find("w:body",ns)]
 paragraphs=[]
 for node in body.findall(".//w:body/w:p",ns):
  style=node.find("w:pPr/w:pStyle",ns)
  value=style.get("{"+ns["w"]+"}val") if style is not None else None
  if style is not None:node.find("w:pPr",ns).remove(style)
  paragraphs.append({"text":"".join(t.text or "" for t in node.findall(".//w:t",ns)),"style":value,"other_xml":E.tostring(node,encoding="unicode")})
 print(json.dumps({"ast":ast,"paragraphs":paragraphs,"word_blocks":blocks}))
'''

def verify_row_xml(before, after, count):
    from lxml import etree as E
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    left,right=E.fromstring(before.encode()),E.fromstring(after.encode())
    added=right.findall('.//w:cantSplit',ns)
    assert len(added)==count and not left.findall('.//w:cantSplit',ns)
    for node in added:
        parent=node.getparent();parent.remove(node)
        if not len(parent):parent.getparent().remove(parent)
    assert E.tostring(left)==E.tostring(right),'Only the bounded row property may change'

def answer_markdown_steps():
    """Exact owned prefix; original entries and conversion engines stay intact."""
    return [
        {'name': 'jinja', 'options': {
            'template': 'src/answer-markdown-inputs.html.j2',
            'content-type': 'text/html', 'extension': 'html'}},
        {'name': 'pandoc', 'options': {
            'from': 'html', 'to': 'html',
            'args': '--lua-filter=src/answer-markdown.lua --wrap=none'}},
    ]

def personal_paths():
    parent = IDS['creatingCUuid'] + '.' + IDS['collectPersonalQUuid']
    gdpr = parent + '.' + IDS['collectPersonalYesAUuid'] + '.' + IDS['cpersGdprQUuid']
    explore = gdpr + '.' + IDS['cpersGdprExploreAUuid']
    legal = explore + '.' + IDS['cpersGdprLegalBasisQUuid']
    safeguards = explore + '.' + IDS['cpersGdprSafeguardsQUuid']
    detail = safeguards + '.' + IDS['cpersGdprSafeguardsAUuid']
    transfer = detail + '.' + IDS['cpersGdprSafeguardsTransferQUuid']
    return dict(parent=parent, gdpr=gdpr, legal=legal, safeguards=safeguards,
                other=legal+'.'+IDS['cpersGdprLegalBasisOtherAUuid']+'.'+IDS['cpersGdprLegalBasisOtherWhichQUuid'],
                identifiability=detail+'.'+IDS['cpersGdprSafeguardsIdentifQUuid'],
                additional=detail+'.'+IDS['cpersGdprSafeguardElaborateQUuid'], transfer=transfer,
                measures=transfer+'.'+IDS['cpersGdprSafeguardsTransferYesAUuid']+'.'+IDS['cpersGdprSafeguardsTransferMeasuresQUuid'])

PATHS = personal_paths()
QUESTION = 'src/questions/07-personal-data.html.j2'


def personal_data_cases(locale):
    assert locale == 'en'
    events = json.loads((ROOT / 'fixtures/pilot/en/personal-transfer-complete.events.json').read_text())
    return {'personal-transfer-complete': {event['path']: event['value'] for event in events}}


def personal_replies(name, locale='en'):
    return {p: ({'value': {'value': v['value']}} if v['type'] == 'IntegrationReply' else v['value'])
            for p, v in personal_data_cases(locale)[name].items()}
