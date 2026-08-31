PYTHON ?= python3

.PHONY: test validate feed-fixture site collect-live local-latest clean

test:
	PYTHONPATH=. $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

validate:
	PYTHONPATH=. $(PYTHON) scripts/validate_repo.py

feed-fixture:
	PYTHONPATH=. $(PYTHON) -m radar feed-fixture --output dist/events.json

site:
	PYTHONPATH=. $(PYTHON) -m radar site --feed tests/fixtures/feed-valid.json --output dist

collect-live:
	PYTHONPATH=. SOURCE_REVISION=$$(git rev-parse --verify HEAD) $(PYTHON) -m radar collect

local-latest: validate
	@bash scripts/sync_local_plugin.sh

clean:
	@echo "Remove the untracked dist/ directory manually when its generated artifacts are no longer needed."
