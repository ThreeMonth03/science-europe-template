# Science Europe DMP

> **Local experiment:** this repository is based on the official
> `dsw:science-europe:1.30.1` template and is testing an explicit completeness
> contract. It packages as
> `threemonth03:science-europe-enhanced:0.3.6`, so it cannot overwrite
> the official template accidentally.

The experiment keeps the upstream Jinja structure but changes how incomplete
answers are rendered in the Q1/Q5/Q15 pilot. Covered unanswered branches display
**Information not provided** instead of being omitted or treated as negative.
This is not yet implemented or audited for every branch or all 15 questions.
Stable `data-requirement-id`, `data-fact-id`, and
`data-status` attributes also give the English and translated outputs a
deterministic alignment key.

The next experimental iteration improves whole-document readability. See
[the owned changes and upgrade boundaries](docs/readability-pass.md). This is
not a release or a claim that all fifteen questions have been fully audited.

The 0.2.1 [answer-retention experiment](docs/answer-retention-experiment.md)
fixes selected Q3/Q12 omissions and misleading negatives, preserves case-sensitive
file names, and adds a broader synthetic scenario plus KM-binding diagnostics.
All fifteen output questions are exercised, not all their branches or SE topics.

The 0.2.2 [structure and binding experiment](docs/structure-and-bindings.md)
repairs selected Q8/Q9/Q11/Q13 HTML blocks and answer-loss conditions. It is
still experimental and does not claim complete SE coverage or runtime table support.

The 0.3.0 [storage and sharing experiment](docs/storage-sharing.md) maps selected
during-project archival facts, preserves partially specified publication
arrangements, and replaces Q10–Q13 outer list scaffolding with reading blocks.

The 0.3.1 [narrative and pagination experiment](docs/narrative-pagination.md)
consolidates archival facts in Q5, preserves the independent Q6 security gap,
and tests bounded reading units and long free answers in PDF and Word.

The 0.3.5 [reading-polish experiment](docs/reading-polish.md) consolidates Q2
missing-field prompts, keeps short quantities together, and joins only owned
Q10 sentences. Navigation updates here do not change bilingual package content;
the stable package description is maintained in `PACKAGE_README.md`.

The 0.3.6 [sharing/preservation experiment](docs/sharing-preservation.md) joins
bounded licence and preservation prose, retains custom process paragraphs and
missing decisions, and prevents line breaks inside marked licence dates.

This is a customized derivative of the official DSW Science Europe template,
not an officially endorsed Science Europe template. Its content contract refers
to the [Science Europe Guidance Document](https://scienceeurope.org/media/4brkxxe5/se_rdm_practical_guide_extended_final.pdf).
It uses questionnaire replies in [Data Stewardship Wizard](https://ds-wizard.org);
no runtime LLM generates or invents the answers.


## Usage

This experimental custom template is not published in the DSW Registry.
The official upstream template is available through the
[DSW Registry](https://registry.ds-wizard.org/templates).

Build reviewed bilingual candidates with
[`ThreeMonth03/science-europe-template-zhtw`](https://github.com/ThreeMonth03/science-europe-template-zhtw).
That build prepares embedded PDF fonts and language-specific Word reference
styles before packaging; a raw `make package` is not the reviewed bilingual build.


## Local experiment and development

The first vertical slice covers Science Europe requirements **SE-1a**
(collection/re-use), **SE-3a** (storage/backup), and **SE-6b** (resources).
The machine-readable source of truth for all 15 Science Europe questions is
[`requirements/science-europe-2021.json`](requirements/science-europe-2021.json).
See [`docs/completeness-experiment.md`](docs/completeness-experiment.md) for
the hypotheses and acceptance criteria.

```bash
python -m pip install -r requirements-dev.txt
make check
```

The official repository is configured locally as the `upstream` Git remote.
Before adopting a new release, follow
[`docs/upstream-upgrades.md`](docs/upstream-upgrades.md) and run:

```bash
git fetch --no-tags upstream '+refs/heads/main:refs/remotes/upstream/main' 'refs/tags/*:refs/tags/upstream/*'
python scripts/audit_upstream.py --target upstream/main
```


## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [ds-wizard/science-europe-template](https://github.com/ds-wizard/science-europe-template), you can [report issues](https://github.com/ds-wizard/science-europe-template/issues) there and fork it for customizations or contributions.


### Contributors

* **Marek Suchánek** <[marek.suchanek@ds-wizard.org](mailto:marek.suchanek@ds-wizard.org)>
  * ORCID: [0000-0001-7525-9218](https://orcid.org/0000-0001-7525-9218)
  * GitHub: [@MarekSuchanek](https://github.com/MarekSuchanek)
* **Kryštof Komanec** <[krystof.komanec@ds-wizard.org](mailto:krystof.komanec@ds-wizard.org)>
  * ORCID: [0000-0003-3856-1682](https://orcid.org/0000-0003-3856-1682)
  * GitHub: [@krystofkomanec](https://github.com/krystofkomanec)
* **Rob Hooft** <[rob.hooft@health-ri.nl](mailto:rob.hooft@health-ri.nl)>
  * ORCID: [0000-0001-6825-9439](https://orcid.org/0000-0001-6825-9439)
  * GitHub: [@rwwh](https://github.com/rwwh)
* **Jana Martínková** <[jana.martinkova@ds-wizard.org](mailto:jana.martinkova@ds-wizard.org)>
  * ORCID: [0000-0001-8575-6533](https://orcid.org/0000-0001-8575-6533/)
  * GitHub: [@jmartinkova](https://github.com/jmartinkova)


## Changelog

### 1.30.1

- Fixed text value type questions rendering with markdown

### 1.30.0

- Adjust to template metamodel version 18.0 (released in DSW 4.29.0)

### 1.29.1

- Adjust to template metamodel version 17.1 (released in DSW 4.26.0)
- Fix affiliation on front page

### 1.29.0

- Fixed rendering risks
- Improved qualified references part
- Updated reused dataset name to use reply string value instead FAIRsharing integration
- Updated dependency on KM to 2.7.0
- Fixed the published dataset to reflect future-oriented statement

### 1.28.0

- Improved affiliation
- Improved text

### 1.27.0

- Updated dependency on KM to 2.6.13
- Fixed legacy integration type

### 1.26.0

- Updated integrations to metamodel version 17.0 (released in DSW 4.22.0)
- Improved minor text flow

### 1.25.0

- Adjusted to template metamodel version 17.0 (released in DSW 4.22.0)
- Fixed typos

### 1.24.0

- Added "General-purpose repository" option to repository type descriptions

### 1.23.0

- Added ORCID Integration
- Added compatible knowledge models to README

### 1.22.0

- Improved Authors of DMP

### 1.21.0

- Adjusted to template metamodel version 16 (released in DSW 4.13.0)

### 1.20.0

- Adjusted to template metamodel version 15 (released in DSW 4.12.0)

### 1.19.1

- Fix issue with `createdBy`

### 1.19.0

- Adjusted to template metamodel version 14 (released in DSW 4.10.0)

### 1.18.1

- Fixed nested bullet points would display unwanted characters

### 1.18.0

- Updated according to the Science Europe DMP template, including the project number, access to private data, and project costs
- Fixed the question regarding data versions to allow for multiple choices
- Corrected the version table and front page

### 1.17.0

- Adjusted to template metamodel version 13 (released in DSW 4.3.0)

### 1.16.1

- Fixed broken images in Word

### 1.16.0

- Adjusted to template metamodel version 12 (released in DSW 4.1.0)

### 1.15.2

- Removed unused code
- Improved wording of storage conventions

### 1.15.1

- Fixed extra `endif`

### 1.15.0

- Updated for `dsw:root:2.5.0`

### 1.14.0

- Switched from `wkhtmltopdf` to `weasyprint` for PDF
- Improved styling for PDF and HTML
- Fixed (non-)reference data in data summary
- Aligned data openness with the KM

### 1.13.0

- Adjusted to template metamodel version 11 (released in DSW 3.20.0)
- Added versions overview / change tracker table

### 1.12.0

- Adjusted to template metamodel version 10 (released in DSW 3.12.0)

### 1.11.0

- Adjusted to template metamodel version 9 (released in DSW 3.10.0)

### 1.10.1

- Fixed Jinja template nesting error

### 1.10.0

- Compatible with `dsw:root:2.4.0`

### 1.9.0

- Adjusted to template metamodel version 8 (released in DSW 3.8.0)

### 1.8.0

- Adjusted to template metamodel version 7 (released in DSW 3.7.0)

### 1.7.0

- Adjusted to template metamodel version 6 (released in DSW 3.6.0)

### 1.6.0

- Adjusted to template metamodel version 5 (released in DSW 3.5.0)

### 1.5.0

- Adjusted to template metamodel version 4 (released in DSW 3.2.0)

### 1.4.1

- Fixed displaying answers related to measured datasets

### 1.4.0

- Adjusted to template metamodel version 3 (released in DSW 2.12.0)

### 1.3.0

- Compatible with `dsw:root:2.3.0`

### 1.2.0

- Adjusted to template metamodel version 2

### 1.1.0

- Compatible with `dsw:root:2.2.0`
- Updated projects and front page as there can be multiple projects specified for a single DMP
- Questions 8, 9, and 10 updated according to DMP Common Standard with dataset - distribution - license hierarchy

### 1.0.0

- Compatible with `dsw:root:2.0.0` and up to `dsw:root:2.1.0`
- Initial version of DMP template created during [ELIXIR BioHackathon Europe 2019](https://www.biohackathon-europe.org)
