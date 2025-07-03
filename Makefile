LOCAL_POSTGRES_USER:=$(USER)
LOCAL_POSTGRES_PASSWORD=dev
LOCAL_POSTGRES_DB=sms
LOCAL_POSTGRES_HOST=localhost
LOCAL_POSTGRES_PORT=65432

LATEST_COMMIT_PATH=assets/latest_commit.txt
POSTGRES_PORT=5432
GATEWAY_PORT=8000

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@poetry install
	@ poetry run pre-commit install
	@poetry shell

.PHONY: check
check: ## Run code quality tools.
	@poetry run pre-commit gc
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@poetry run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@poetry run deptry .
	@make spec

.PHONY: clean
clean:
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@find . -name '__pycache__' -exec rm -r {} + -o -name '*.pyc' -delete

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@make write-latest-commit
	@poetry run pytest --cov --cov-config=pyproject.toml --cov-report=xml
	@poetry run python tests/connection/test_ssh.py

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

.PHONY: new-build
new-build:
	@./kustomize/scripts/build_and_push.sh

.PHONY: check-minikube
check-minikube:
	@is_minikube=$$(poetry run python -c "import os; print(str('minikube' in os.getenv('KUBECONFIG', '')).lower())"); \
	if [ $$is_minikube = "true" ]; then \
		echo "You're using minikube"; \
	else \
		echo "Not using minikube. Exiting."; \
		exit 1; \
	fi

.PHONY: spec
spec:
	@poetry run python ./sms_api/api/openapi_spec.py

.PHONY: new
new:
	@make check-minikube
	@make latest-commit
	@make spec
	@make new-build
	@make apply

.PHONY: whichkube
whichkube:
	@echo $${KUBECONFIG}

.PHONY: gateway
gateway:
	@make spec
	@poetry run uvicorn sms_api.api.main:app \
		--env-file assets/dev/config/.dev_env \
		--host 0.0.0.0 \
		--port 8000 \
		--reload

.PHONY: pginit
pginit:
	@initdb -D $(path)

.PHONY: pgup
pgup:
	@touch "$(path)/.log"
	@pg_ctl -D $(path) -l "$(path)/.log" -o "-p $(port)" start

.PHONY: pgdown
pgdown:
	@pg_ctl stop -D $(dbname)

.PHONY: pgdb-new
pgdb-new:
	@createdb $(dbname)

.PHONY: pgdb-conn
pgdb-conn:
	@psql $(dbname)

.PHONY: pgdb-drop
pgdb-drop:
	@dropdb $(dbname)

usr:
	@echo

# --name postgresql
.PHONY: dbup
dbup:
	@service_name="pgdb"; \
	[ -z "$(port)" ] && port=${LOCAL_POSTGRES_PORT} || port=$(port); \
	[ -z "$(password)" ] && password=${LOCAL_POSTGRES_PASSWORD} || password=$(password); \
	docker run -d \
		--name $$service_name \
		-e POSTGRES_PASSWORD=$$password \
		-e POSTGRES_USER=${LOCAL_POSTGRES_USER} \
		-e POSTGRES_HOST=localhost \
		-e POSTGRES_DB=${LOCAL_POSTGRES_DB} \
		-p $$port:${POSTGRES_PORT} \
		postgres:17

.PHONY: dbdown
dbdown:
	@make rmcont name="pgdb"

.PHONY: mongoup
mongoup:
	@docker run -d \
		--name mongodb \
		-p $(port):$(port) \
		mongo


# this command should run psql -h localhost -p 65432 -U alexanderpatrie sms
.PHONY: pingpg
pingpg:
	@[ -z "$(user)" ] && user=${LOCAL_POSTGRES_USER} || user=$(user); \
	[ -z "$(port)" ] && port=${LOCAL_POSTGRES_PORT} || port=$(port); \
	psql -h localhost -p $$port -U ${LOCAL_POSTGRES_USER} sms;

.PHONY: write-latest-commit
write-latest-commit:
	@poetry run python sms_api/latest_commit.py

.PHONY: get-latest-simulator
get-latest-simulator:
	@latest=$$( \
		curl -s https://api.github.com/repos/CovertLab/vEcoli/commits/master \
		| jq -r '"\(.sha[0:7]) \(.commit.author.date)"' \
	); \
	echo $${latest} | awk '{print $$1}'

.PHONY: latest-simulator
latest-simulator:
	@latest_commit=$$(make get-latest-simulator | awk '{print $1}'); \
	latest_known=$$(cat ${LATEST_COMMIT_PATH}); \
	if [ $$latest_commit != $$latest_known ]; then \
		echo $$latest_commit > ${LATEST_COMMIT_PATH}; \
	else \
		echo "You have the latest commit."; \
	fi; \
	cat ${LATEST_COMMIT_PATH}

.DEFAULT_GOAL := help
