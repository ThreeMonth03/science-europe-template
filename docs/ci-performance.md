# CI execution cost

The English and Chinese workflows retain their existing tests, assertions,
triggers, permissions and jobs. The Chinese workflow still verifies its exact
English lock with an isolated dependency environment and runs both native lanes.

The current optimizations change test execution, not template/package inputs:

- Question and profile fixtures reuse in-memory Jinja bytecode, keyed by loader
  identity and source checksum. Escaped/unescaped profile compilers are separate.
  Each cache holds at most 256 entries; answers and rendered HTML are never cached.
- Four expensive PDF probes reuse parsed CSS and font configurations per exact
  stylesheet/media pair, within a single process. Every case still renders.
  Empty style elements preserve the original DOM element order. Production DSW
  rendering is unchanged; before/after variants do not share font configurations.
- Source validity checks run before long tests. The Chinese Word preflight first
  verifies the complete current source seal, then compares the appropriate frozen
  historical view. It does not require a newly reviewed asset to equal old bytes.

Local verification includes the complete unit suites, all four affected native
probes on raw English/prepared English/prepared Chinese, comparison with the
previous successful CI reports, and 12 cached/uncached print/screen comparisons
of text, styles and every layout box. No historic fixture or acceptance assertion
is weakened. CI timing must be measured separately from local timing; the prior
successful bilingual run was 36546031947 (about 72 minutes).
