"""Exact incremental CSS gate; prior content and layout contracts stay intact."""
import hashlib

BEGIN = '/* BEGIN metadata gap panel:'
END = '/* END metadata gap panel */'
SELECTOR = ('html body #q-docs-metadata > .answer > .metadata-policy > .reading-gap'
    ':has(> p.data-gap[data-fact-id="metadata-access-instructions"][data-status="missing"]:first-child:not(:has(*)))'
    ':has(> p.data-gap[data-fact-id="metadata-harvestable"][data-status="missing"]:nth-child(2):last-child:not(:has(*)))')


def split_css(css):
    assert css.count(BEGIN) == css.count(END) == 1
    left, rest = css.split(BEGIN)
    block, right = rest.split(END)
    return left + right.removeprefix('\n'), BEGIN + block + END


def legacy_block():
    return ('/* BEGIN metadata gap panel: only the two unanswered publication follow-ups. */\n'
        '@media print {\n' + SELECTOR + ' { border: 1px solid #8a6d3b; border-left: 3px solid #95651b; background: #fff8e8; padding: .45em .65em; break-inside: avoid; }\n'
        + SELECTOR + ' > p.data-gap { border: 0; padding: 0; background: transparent; }\n'
        + SELECTOR + ' > p.data-gap:first-child { margin-bottom: .25em; }\n}\n' + END)
def prior_css(css):
    before, block = split_css(css)
    assert block == legacy_block(), 'Unreviewed Q3 metadata panel CSS'
    return before


def historical_css(css):
    """Restore the retired panel only for historical probes, never packaging."""
    if BEGIN in css:
        prior_css(css)
        return css
    assert END not in css
    return css + legacy_block() + '\n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
