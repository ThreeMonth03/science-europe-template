"""Synthetic font diagnostics, run inside the pinned offline worker, not a fix.

The PDF/HTML contain synthetic samples only. Never run against authored text.
No production CSS, fonts, translations or Word assets are changed.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from weasyprint import HTML

SAMPLES = {
    'adjacent': '資料儲存庫管理）。下一句。',
    'list': '資料、後設資料、文件；查核：完成。',
    'quotes': '「資料」（校正後）。',
    'joined': '我們將記錄資料。我們將納入關鍵字。',
    'spaced': '我們將記錄資料。 我們將納入關鍵字。',
    'mixed': 'Dublin Core v1.2、W3C PROV；1.25 TB；https://example.org/a?x=1&y=2',
    'english': 'First sentence. Second sentence (metadata).',
}


def run(font_path, output):
    assert font_path.is_file() and not output.exists()
    output.mkdir(parents=True)
    font = TTFont(font_path)
    features = {table: sorted({r.FeatureTag for r in font[table].table.FeatureList.FeatureRecord})
                for table in ['GSUB', 'GPOS']}
    cmap = font.getBestCmap()
    metrics = {c: list(font['hmtx'].metrics[cmap[ord(c)]]) for c in '資料（）。、，：；！？ABC'}
    body = []
    for variant in ['normal', 'chws', 'halt', 'palt']:
        setting = 'normal' if variant == 'normal' else '"' + variant + '" 1'
        body.append('<section><h1>' + variant + ' (diagnostic only)</h1>')
        for name, sample in SAMPLES.items():
            body.append('<h2>' + name + '</h2><p id="' + variant + '-' + name
                        + '" style=\'font-feature-settings:' + setting + '\'>' + html.escape(sample) + '</p>')
        body.append('</section>')
    source = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>
@font-face {font-family: Pilot; src:url("''' + font_path.as_uri() + '''");}
@page {size:A4; margin:18mm;}
body {font-family:"DejaVu Sans",Pilot,sans-serif; font-size:12pt;}
section {break-after:page;} section:last-child {break-after:auto;}
h1 {font-size:16pt;} h2 {font-size:10pt; margin:18pt 0 4pt;}
p {margin:0; white-space:pre; font-size:12pt;}
</style><body>''' + ''.join(body) + '</body></html>'
    (output / 'samples.html').write_text(source)
    document = HTML(string=source, base_url=str(font_path.parent)).render()
    document.write_pdf(output / 'samples.pdf')
    rows = {}
    for page in document.pages:
        for box in page._page_box.descendants():
            element = box.element
            key = element.get('id') if element is not None else None
            if key and type(box).__name__ == 'TextBox':
                rows.setdefault(key, []).append(dict(text=box.text, width=box.width, height=box.height))
    assert len(rows) == 4 * len(SAMPLES)
    for variant in ['normal', 'chws', 'halt', 'palt']:
        for name, sample in SAMPLES.items():
            assert ''.join(r['text'] for r in rows[variant + '-' + name]) == sample
    comparisons = {}
    for variant in ['chws', 'halt', 'palt']:
        comparisons[variant] = {name: dict(identical=rows[variant+'-'+name] == rows['normal-'+name],
            width_delta=sum(r['width'] for r in rows[variant+'-'+name])-sum(r['width'] for r in rows['normal-'+name]))
            for name in SAMPLES}
    assert 'chws' not in features['GPOS']
    assert all(r['identical'] for r in comparisons['chws'].values()), 'Unexpected shaping support: revisit diagnosis'
    result = dict(diagnostic_only=True, adopted=False,
        font_sha256=hashlib.sha256(font_path.read_bytes()).hexdigest(), units_per_em=font['head'].unitsPerEm,
        features=features, advance_and_lsb=metrics, logical_text_unchanged=True,
        literal_adjacent_punctuation='）。', literal_codepoints=['U+FF09', 'U+3002'],
        pages=len(document.pages), rows=rows, comparisons=comparisons)
    (output / 'metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(passed=True, pages=len(document.pages), font_sha256=result['font_sha256'],
        chws_has_no_effect=True, font_compression_adopted=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.font.resolve(), args.output.resolve())
