.PHONY: test verify check package audit-upstream

PYTHON ?= python3
DSW_TDK ?= dsw-tdk

test:
	$(PYTHON) -m unittest discover -s tests -v

verify:
	$(DSW_TDK) --no-config verify .

check: test verify

package:
	$(DSW_TDK) --no-config package .

audit-upstream:
	$(PYTHON) scripts/audit_upstream.py --target upstream/main
