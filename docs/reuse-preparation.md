# Integrated Q1 preparation prose (0.3.49)

Only `src/questions/01-how-data.html.j2` and the package version change among
production package inputs. The Q1 source is byte-identical to the bounded
prototype at `57f79b33feaec4f3daf30a33841c59cb58d41b0e` applied to exact 0.3.48
(`678787f2fdf047a3d6cc3577d4589d64ba2cd846`).

Machine-readable branches emit complete English sentences. This removes this
paragraph's dependence on the translation tool's literal upstream rewrite;
it does not remove every upstream-specific rule in that tool. Chinese still
comes from the existing locked pipeline, with nine reviewed replacement units.
Paths, answer states, user labels and links, paragraph count, CSS and Word
format steps are preserved. No new promises or missing-answer notices are added.

`scripts/reuse_preparation_contract.py` checks all current sources/assets,
metadata and the frozen recipe before providing an exact 0.3.48 view for
historical tests. The new behavior is tested on actual production Q1 sources;
older projections are not presented as current-behavior validation.

The paired Chinese repo locks the full English commit and version 0.3.49.
Use short-lived `fix/reuse-preparation-integration`; review/submission remain
formats, not permanent branches. No push or deployment is implied. See the
paired repo's integration record for native PDF/Word and CI scope.
