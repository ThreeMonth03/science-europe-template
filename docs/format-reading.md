# Q2 format reading — 0.3.31

Branch: `fix/format-reading`, based on English 0.3.30 (`acf13ba`).
Only `src/questions/02-what-data.html.j2` changes at runtime. CSS, fonts, Word
Lua/reference styles, KM bindings and Science Europe question coverage stay fixed.

Two complete facts may share a sentence: standardized + archival-suitable; or
file count + average size. Independent missing/unknown/no answers do not merge
into invented statements. Total-volume and small-volume prose is shorter.
Numeric input remains verbatim, including zero; no multiplication or rounding.
Non-standard reasons and all other authored blocks remain untouched.

`format_reading_contract.py` independently projects the frozen 0.3.30 DOM and
checks the entire question (264 cases including autoescape on/off). Mutation
tests reject edits to quantities, formatting, missing prompts and authored text.
The bilingual repository checks the Chinese projection and exact translation
delta, then compares same-fixture native HTML/PDF/Word output separately.

Chinese remains generated from the locked English source through the existing
translation tree. The companion branch locks an exact English commit, not a
moving branch. No production deployment or full-DMP acceptance is implied.
