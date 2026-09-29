"""Process-local CSS compilation for the pinned, synthetic layout probes.

Each exact CSS/media pair owns its font configuration; no rendered result is
cached. Callers retain an empty style element at the original stylesheet site
so structural selectors still see the same element order. This is test tooling,
not the template's production renderer.
"""

CACHED_RENDERER = '''
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
_probe_styles = {}
def render_cached(source, css, media='print'):
    key = (css, media)
    if key not in _probe_styles:
        fonts = FontConfiguration()
        _probe_styles[key] = (CSS(string=css, media_type=media, font_config=fonts), fonts)
    style, fonts = _probe_styles[key]
    return HTML(string=source, media_type=media).render(stylesheets=[style], font_config=fonts)
'''
