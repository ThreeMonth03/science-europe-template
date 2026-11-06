# Testing the current bilingual template

## Source ownership

English owns shared Jinja, answer bindings, language-aware layout, fonts, public
KM test snapshots, English packaging and the DSW 4.34 compatibility exporter.
The companion Chinese repository owns the only editable `locales/zh-Hant.po`
and pins the exact English source and official build dependencies in
`pipeline.yml`. Neither build needs a Tool checkout or editable Tool install.
Do not edit generated Chinese packages, MO files or render trees.

The compatibility exporter is active functionality, even though its filename
contains `legacy`: stock DSW 4.34 needs the embedded-catalog profile. It is not
the retired pre-PO Jinja-rewriting pipeline.

## Current checks

Install `requirements-dev.txt` in an isolated environment. Run `make check` for
the retained current tests and TDK verification. `make check-current` runs the
eight current English answer/reading suites; the Chinese workflow runs the same
suites against both prepared language packages. `make test-compat434` verifies
the active compatibility exporter.

`make knowledge-models` verifies the two repository-owned public snapshots,
offline. Missing or changed snapshots fail without replacing the input. Package
tests cover source immutability, single layout preparation, deterministic ZIPs,
history-derived timestamps and refusal to overwrite earlier output.

Native parser and pagination checks require Docker and the stock Worker images
pinned by the existing workflow. They cover bounded contracts, not every
possible project. CI has current unit/native lanes and a required aggregate
check; retired historical replay is no longer a selectable mode.

`make pot POT_OUTPUT=outputs/template-NEW.pot` exports the marked messages using
official DSW 4.35 extraction. A clean, identified English commit is required;
failed parsing, empty sources and an existing output path are rejected. The
English catalog tests cover extraction, provenance and the shared catalog
validator without requiring a Chinese checkout.

Chinese CI consumes this English-produced POT before building. It checks the
template coordinate and exact source commit against `pipeline.yml`, then checks
the authoritative PO for missing or extra active keys, untranslated/fuzzy
entries and mismatched named parameters. The Chinese refresh script does not
extract or parse Jinja. These checks concern marked messages, not the semantics
of every translation or every human-readable literal.

## Building runtime deliveries

Build English independently from a clean checkout with full Git history:

```sh
make package PACKAGE_OUTPUT=outputs/english-NEW
```

`scripts/build_package.py` owns source copying, font/Word reference preparation,
official TDK verification/packaging and canonical ZIP bytes. It uses only this
repository's fonts and prepares the package exactly once. A new output directory
is required; local dirty-source rehearsals must explicitly use the CLI's
`--preview` option and are not release candidates.

For paired English/Chinese deliveries, follow the Chinese repository's build
instructions. Its orchestrator calls this same English builder, then reviews
and exports the Chinese compatibility package; it does not prepare a second
Word reference or implement a second English packager.

For an explicit compatibility export from that prepared package:

```sh
make export-compat434 \
  ENGLISH_ZIP=/path/to/english.zip \
  PO=/path/to/science-europe-template-zhtw/locales/zh-Hant.po \
  COMPAT_VERSION=NEW_IMMUTABLE_VERSION \
  COMPAT_OUTPUT=/path/to/new-output.zip
```

The exporter keeps shared Jinja and existing assets unchanged, adds the compiled
MO, fixes the generated language helper to `zh-Hant` and exposes the six
review/submission HTML, PDF and Word formats. LaTeX and ODT are not part of the
4.34 Chinese compatibility delivery. The output path must not already exist.
Plural messages require an explicitly reviewed rule and are currently rejected.

For native DSW 4.35, attach the approved PO to the exact installed English DT
version and select `zh-Hant` when generating Chinese documents. Do not use the
4.34 compatibility package as the native-PO installation.

## Document acceptance

Before publishing a changed source/PO pair, compare English and Chinese PDF and
DOCX using the same answers. Include complete, partial, empty, explicit-No,
unnamed and long/rich-text cases. Check:

- all original questions and meaningful authored facts remain;
- missing is not treated as No, inactive stale children are not printed;
- submission has no internal gap prompts, while review keeps its notices;
- headings, lists, tables, fonts and page transitions remain readable.

Funding sources belong to the research overview. When visible overview or
contributor content exists, Section 1 starts on a new page; a title alone does
not create a cover page. Dataset attributes use one shallow indent. Only bounded
short records or fixed terminal pairs stay together; long authored answers flow.

Inspect rendered pages, not just extracted text or a test count. A LibreOffice
DOCX preview is useful evidence but is not native Microsoft Word certification.
A build or CI pass does not authorize deployment, overwrite a published version,
or establish arbitrary-input bug-free output.

## Reproducibility

Keep `template.json`, `src/`, `scripts/prepare_layout.py`,
`PACKAGE_README.md` and `LICENSE` as the declared package inputs. Navigation
docs and tests must not advance the package timestamp. The builder requires full
English Git history so it can identify the last package-input commit correctly.
Use new immutable versions for published changes and retain the old installation
for rollback. Never overwrite an installed template coordinate.
