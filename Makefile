.PHONY: test verify check check-current package audit-upstream knowledge-models
.DEFAULT_GOAL := test

PYTHON ?= python3
DSW_TDK ?= dsw-tdk

knowledge-models:
	$(PYTHON) scripts/prepare_knowledge_models.py

test: knowledge-models
	$(PYTHON) -m unittest discover -s tests -v

verify:
	$(DSW_TDK) --no-config verify .

check: test verify

check-current:
	$(PYTHON) scripts/check_current.py

package:
	$(DSW_TDK) --no-config package .

audit-upstream:
	$(PYTHON) scripts/audit_upstream.py --target upstream/main
