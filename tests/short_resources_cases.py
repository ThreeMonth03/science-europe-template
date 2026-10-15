"""Existing synthetic Q15 grammar cases reused by current budget guards."""
from bs4 import BeautifulSoup

OPENING = '<div id="q-required-resources" class="question" data-requirement-id="SE-6b">'

HINT = '<div id="q-required-resources" class="question pdf-short-resources" style="break-inside: avoid" data-requirement-id="SE-6b">'


def units(value): return sum(2 if ord(c) >= 0x2e80 else 1 for c in ' '.join(value.split()))


def fragment(rows=2, language='en'):
    words = ['15. Resources?', 'Training.', 'Prepare.', 'Files.', 'Budget', 'Funding', 'Resource', 'Purpose.', 'FAIR.', 'Funds.']
    if language != 'en': words = ['15. 資源？', '培訓。', '準備。', '資料。', '預算', '經費', '資源', '用途。', '管理。', '經費。']
    q,training,one,two,budget,funding,name,purpose,fair,funds = words
    row = lambda i: '<tr data-item-id="aa.'+str(i)+'"><td><p><strong>'+name+str(i)+'</strong></p><div class="answer-detail" data-fact-id="resource-justification" data-status="complete"><p>'+purpose+'</p></div><p>'+fair+'</p></td><td><p>0 TWD</p></td><td><div class="answer-detail"><p>'+funds+'</p></div></td></tr>'
    return ('<section>'+OPENING+'<h3>'+q+'</h3><div class="answer"><div class="answer-lead"><p data-requirement-id="SE-6b" data-fact-id="specialist-expertise" data-status="complete">'+training+'</p></div>'
        '<div class="answer-detail" data-fact-id="specialist-expertise-detail" data-status="complete"><p>Training details.</p><ul><li>'+one+'</li><li>'+two+'</li></ul></div>'
        '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="explicit-no">No equipment.</p><p>Charges.</p><h4>'+budget+'</h4><div class="project-resources" data-item-id="aa">'
        '<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead><tr><th scope="col">'+name+'</th><th scope="col">'+budget+'</th><th scope="col">'+funding+'</th></tr></thead><tbody>'
        +''.join(row(i) for i in range(rows))+'</tbody></table></div></div></div></section>')


def cases():
    base = fragment(); rows = [('english',base,True), ('chinese',fragment(language='zh'),True)]
    for n in (0,1,3,8): rows.append(('rows-'+str(n),fragment(rows=n),n==1))
    def change(name,old,new,expected=False): rows.append((name,base.replace(old,new),expected))
    for name,old,new in [
        ('unknown-status','data-status="complete"','data-status="unknown"'),
        ('missing-fact','data-status="complete"','data-status="missing"'),
        ('missing-class','<p>Charges.</p>','<p class="data-gap">Missing.</p>'),
        ('unknown-div','class="answer-lead"','class="unknown"'),
        ('author-style','<p>Purpose.</p>','<p style="height:1000px">Purpose.</p>'),
        ('link','Purpose.','<a href="https://example.org">Original</a>'),
        ('image','Purpose.','<img src="not-fetched.png" alt="Original">'),
        ('break','Purpose.','First<br>Second'),
        ('nested-table','Purpose.','<table><tr><td>Original</td></tr></table>'),
        ('nested-list','<li>Prepare.</li>','<li>Prepare.<ul><li>Nested.</li></ul></li>'),
        ('extra-list-item','</ul>','<li>Extra.</li></ul>'),
        ('extra-paragraph','Purpose.','Purpose.</p><p>Extra.'),
        ('after-budget','</table>','</table><p>More facts.</p>'),
        ('unknown-attribute','data-item-id="aa"','data-item-id="aa" data-extra="yes"'),
        ('bad-id','data-item-id="aa"','data-item-id="not-an-item"'),
        ('unbalanced-div','</table>','</table></div>'),
        ('unknown-void','Purpose.','<hr>Purpose.'),
        ('comment','Purpose.','<!-- comment -->Purpose.'),
        ('empty-paragraph','Purpose.',''),
        ('extra-col','</colgroup>','<col class="resource-funding"></colgroup>'),
        ('extra-cell','</tr></tbody>','<td><p>0</p></td></tr></tbody>'),
        ('wrong-question','q-required-resources','q-other'),
        ('unknown-root-class','class="question"','class="question unknown"')]:
        change(name,old,new)
    change('inline','Purpose.','<strong>Original.</strong> <em>Text.</em> <code>0.csv</code>',True)
    change('authored-warning','Purpose.','Information not provided: keep Original.csv.',True)
    change('chinese-authored-warning','Purpose.','尚待補充：保留 Original.csv。',True)
    for field,old,limit in [('paragraph','Purpose.',160),('funding','Funds.',80),('amount','0 TWD',40),('list','Prepare.',80),('heading','15. Resources?',360)]:
        for n in (limit,limit+1): change(field+'-'+str(n),old,'x'*n,n==limit)
        change(field+'-cjk-boundary',old,'中'*(limit//2),True)
        change(field+'-cjk-over',old,'中'*(limit//2+1))
    rows.append(('duplicate-question',base+base,False))
    rows.append(('authored-lookalike',base.replace('Purpose.',base),False))
    rows.append(('two-projects',base.replace('</table></div>','</table></div><div class="project-resources" data-item-id="bb">'+base.split('<table',1)[1].split('</table>',1)[0].join(['<table','</table>'])+'</div>',1),False))
    # A worst-case short unit, with independent whole-question boundary math.
    large = base.replace('Purpose.','p'*150).replace('FAIR.','f'*100).replace('Funds.','u'*80).replace('0 TWD','0'*40)
    large = large.replace('Training.','t'*150).replace('No equipment.','e'*150).replace('Charges.','c'*30)
    current = units(BeautifulSoup(large,'html.parser').find(id='q-required-resources').get_text())
    needed = 1200-current+len('Training details.'); assert 0 < needed <= 160
    for n in (needed,needed+1):
        source = large.replace('Training details.','v'*n)
        rows.append(('whole-'+str(1200+n-needed),source,n==needed))
    span = '<span data-fact-id="repository-charges" data-status="complete">Charges.</span>'
    joined = base.replace('No equipment.</p><p>Charges.', 'No equipment. '+span)
    rows.append(('joined-fixed-pair',joined,True))
    rows.append(('joined-cjk',joined.replace('No equipment. '+span,'不需要其他硬體或軟體。'+span.replace('Charges.','不收取服務費。')),True))
    for name, source in [
        ('joined-unknown-attribute',joined.replace('<span ', '<span title="unknown" ')),
        ('joined-missing',joined.replace('repository-charges" data-status="complete','repository-charges" data-status="missing')),
        ('joined-nested-emphasis',joined.replace('Charges.', '<strong>Charges.</strong>')),
        ('joined-duplicate-span',joined.replace(span,span+span)),
        ('joined-wrong-parent',base.replace('Purpose.',span)),
        ('joined-long',joined.replace('Charges.','x'*160)),
    ]: rows.append((name,source,False))
    return rows
