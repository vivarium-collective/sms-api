.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@poetry install
	@ poetry run pre-commit install
	@poetry shell

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@poetry run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@poetry run deptry .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@poetry run pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@poetry build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@rm -rf dist

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@poetry run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@poetry run mkdocs serve

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: ssh
ssh:
	@ssh -i $(key) svc_vivarium@login.hpc.cam.uchc.edu

.PHONY: new-build
new-build:
	@./kustomize/scripts/build_and_push.sh

.PHONY: apply-build
apply-build:
	@kubectl kustomize kustomize/overlays/sms-api-local | kubectl apply -f -

.PHONY: check-minikube
check-minikube:
	@is_minikube=$$(poetry run python -c "import os; print(str('minikube' in os.getenv('KUBECONFIG', '')).lower())"); \
	if [ $$is_minikube = "true" ]; then \
		echo "You're using minikube"; \
	else \
		echo "Not using minikube. Exiting."; \
		exit 1; \
	fi

.PHONY: new
new:
	@make check-minikube
	@make new-build
	@make apply-build

.PHONY: apply
apply:
	@cd kustomize
	@kubectl kustomize overlays/sms-api-local | kubectl apply -f -
	@cd ..

.PHONY: write-latest-commit
write-latest-commit:
	@poetry run python sms_api/latest_commit.py

.PHONY: repl
repl:
	@poetry run python -m asyncio

.PHONY: setkube
setkube:
	@export KUBECONFIG=$(path)
	@echo "You're now using the kubeconfig path: $${KUBECONFIG}"

.PHONY: whichkube
whichkube:
	@echo $${KUBECONFIG}

.DEFAULT_GOAL := help
