# ragdoll — shorthands. Run `make` or `make help` for the list.
# Everything here runs locally. Nothing deploys.

.DEFAULT_GOAL := help
.PHONY: help 

UV := uv

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

