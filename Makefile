# ragdoll — shorthands. Run `make` or `make help` for the list.
# Everything here runs locally. Nothing deploys.

.DEFAULT_GOAL := help
.PHONY: help install ingest ingest-offline route test lint fmt typecheck check clean explainer

UV := uv

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Sync the virtualenv from the lockfile
	$(UV) sync

ingest: ## Parse the corpus, count tokens, print the routing decision
	$(UV) run ragdoll ingest corpus

ingest-offline: ## Same, but approximate counts and no API calls
	$(UV) run ragdoll ingest corpus --offline

ingest-fresh: ## Same as ingest, ignoring the cache
	$(UV) run ragdoll ingest corpus --no-cache

route: ## Probe the routing rule: make route N=199000
	$(UV) run ragdoll route $(N)

test: ## Run the test suite
	$(UV) run pytest

lint: ## Lint with ruff
	$(UV) run ruff check .

fmt: ## Format with ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck: ## Type check with ty
	$(UV) run ty check

check: lint typecheck test ## Everything the CI would run

explainer: ## Open the newest HTML explainer
	./open-explainer

clean: ## Remove caches and build artefacts
	rm -rf .ragdoll .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
