PYTHON ?= python3

.PHONY: test validate feed-fixture site collect-live local-latest local-downgrade local-behind clean

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

# Downgrade the installed plugin for Update-button testing.
#   make local-downgrade           # one commit back
#   make local-downgrade N=3       # N commits back
#   make local-downgrade REF=tag   # exact tag/commit/ref
local-downgrade:
	@N="$(N)" REF="$(REF)" bash scripts/downgrade_local_plugin.sh

# Advance source by an empty commit without moving the install (keeps Update UI).
local-behind:
	@bash scripts/mark_local_plugin_behind.sh

clean:
	@echo "Remove the untracked dist/ directory manually when its generated artifacts are no longer needed."
