# Testing the current bilingual template

## Source ownership

English owns shared Jinja, answer bindings, language-aware layout and the DSW
4.34 compatibility exporter. The companion Chinese repository owns the only
editable `locales/zh-Hant.po` and pins exact source and Tool commits in
`pipeline.yml`. Do not edit generated Chinese packages, MO files or render trees.

The compatibility exporter is active functionality, even though its filename
contains `legacy`: stock DSW 4.34 needs the embedded-catalog profile. It is not
the retired pre-PO Jinja-rewriting pipeline.

## Current checks

Install `requirements-dev.txt` in an isolated environment. Run `make check` for
the retained current tests and TDK verification. `make check-current` runs the
eight current English answer/reading suites; the Chinese workflow runs the same
suites against both prepared language packages. `make test-compat434` verifies
the active compatibility exporter.

Native parser and pagination checks require Docker and the stock Worker images
pinned by the existing workflow. They cover bounded contracts, not every
possible project. CI has current unit/native lanes and a required aggregate
check; retired historical replay is no longer a selectable mode.

Chinese package checks additionally verify the PO against official DSW 4.35
extraction. Missing or extra active keys, untranslated/fuzzy entries and mismatched
named parameters fail rather than silently approving a source/translation mismatch.
This checks marked messages, not the semantics of every translation or every
human-readable literal.

## Building runtime deliveries

Use the Chinese repository's current build instructions. The English package must
already have its fonts and Word reference prepared exactly once.

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
