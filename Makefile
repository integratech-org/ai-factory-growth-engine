# ==========================================
# Setup commands
# ==========================================

.PHONY: setup
setup:
	@./scripts/setup.sh

# ===========================================
# Pre-commit Hooks
# ===========================================

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-update: ## Update pre-commit hooks to latest versions
	uv run pre-commit autoupdate

pre-commit-all: ## Run pre-commit on all files
	uv run pre-commit run --all-files
