POSTGRES_USER=sms
POSTGRES_DB=sms
LOCAL_POSTGRES_HOST=localhost
LOCAL_POSTGRES_PORT=5555
LOCAL_GATEWAY_PORT=8888

LATEST_COMMIT_PATH=assets/latest_commit.txt
POSTGRES_PORT=5432


# "postgresql://sms:$$pw@localhost:$(port)/sms?sslmode=disable""postgresql://sms:$$pw@localhost:$(port)/sms?sslmode=disable"

.PHONY: install
install: ## Install the uv environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry .

.PHONY: clean
clean:
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@find . -name '__pycache__' -exec rm -r {} + -o -name '*.pyc' -delete

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest -ra --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: logtest
logtest: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest \
		--cov \
		--cov-config=pyproject.toml \
		--cov-report=xml \
		--log-file=tests/.pytest.log \
		--log-file-level=ERROR

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@uv run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@uv run mkdocs serve

PHONY: generate-docs
generate-docs: ## Build and serve the documentation
	@cd documentation && uv run make clean && uv run sphinx-apidoc -o source ../sms_api && uv run make html

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.PHONY: new-build
new-build:
	@./kustomize/scripts/build_and_push.sh

.PHONY: check-minikube
check-minikube:
	@is_minikube=$$(uv run python -c "import os; print(str('minikube' in os.getenv('KUBECONFIG', '')).lower())"); \
	if [ $$is_minikube = "true" ]; then \
		echo "You're using minikube"; \
	else \
		echo "Not using minikube. Exiting."; \
		exit 1; \
	fi

.PHONY: spec
spec:
	@uv run python ./sms_api/api/openapi_spec.py

.PHONY: new
new:
	@make check-minikube
	@make write-latest-commit
	@make spec
	@make new-build
	@kubectl kustomize kustomize/overlays/sms-api-local | kubectl apply -f -

.PHONY: whichkube
whichkube:
	@echo $${KUBECONFIG}

.PHONY: gateway
gateway:
	@make spec
	@uv run uvicorn sms_api.api.main:app \
		--env-file assets/dev/config/.dev_env \
		--host 0.0.0.0 \
		--port ${LOCAL_GATEWAY_PORT} \
		--reload

.PHONY: edit-app
edit-app:
	@uv run marimo edit app/ui/$(ui).py

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

# --name postgresql
.PHONY: dbup
dbup:
	@service_name="pgdb"; \
	[ -z "$(port)" ] && port=${LOCAL_POSTGRES_PORT} || port=$(port); \
	[ -z "$(password)" ] && password=${LOCAL_POSTGRES_PASSWORD} || password=$(password); \
	docker run -d \
		--name $$service_name \
		-e POSTGRES_PASSWORD=$$password \
		-e POSTGRES_USER=${POSTGRES_USER} \
		-e POSTGRES_HOST=localhost \
		-e POSTGRES_DB=${POSTGRES_DB} \
		-p $$port:${POSTGRES_PORT} \
		postgres:17

.PHONY: dbdown
dbdown:
	@docker rm -f pgdb

.PHONY: mongoup
mongoup:
	@docker run -d \
		--name mongodb \
		-p $(port):$(port) \
		mongo

.PHONY: natsup
natsup:
	@[ -z "$(port)" ] && port=30050 || port=$(port); \
	docker run -d --name nats --rm -p $$port:$$port nats

# this command should run psql -h localhost -p 65432 -U alexanderpatrie sms
.PHONY: pingpg
pingpg:
	@[ -z "$(user)" ] && user=${LOCAL_POSTGRES_USER} || user=$(user); \
	[ -z "$(port)" ] && port=${LOCAL_POSTGRES_PORT} || port=$(port); \
	psql -h localhost -p $$port -U ${LOCAL_POSTGRES_USER} sms;

.PHONY: pingdb
pingdb:
	@uri=$$(make pguri); \
	psql $$uri

.PHONY: write-latest-commit
write-latest-commit:
	@uv run python sms_api/latest_commit.py

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

.PHONY: test-mod
testmod:
	@uv run python -m pytest -s $(m)

.PHONY: run-workflow
workflow:
	curl -X POST \
		-H "Authorization: token $(token)" \
		-H "Accept: application/vnd.github.v3+json" \
		https://api.github.com/repos/vivarium-collective/sms-api/actions/workflows/build-and-push.yml/dispatches \
		-d '{"ref": $(branch)}'

.PHONY: generate-client
generate-client:
	@make spec
	@uv run ./scripts/generate-api-client.sh

.PHONY: pguri
pguri:
	@pg_user=sms; \
	pg_password=$$(uv run python -c "import dotenv;import os;dotenv.load_dotenv('assets/dev/config/.dev_env');print(os.getenv('POSTGRES_PASSWORD'))"); \
	echo postgresql://${POSTGRES_USER}:$$pg_password@${LOCAL_POSTGRES_HOST}:${LOCAL_POSTGRES_PORT}/${POSTGRES_DB}

.PHONY: py
py:
	@uv run python -m asyncio

.PHONY: set-wip
set-wip:
	@module=$(ui); \
	cp app/ui/$$module.py app/ui/wip_$$module.py; \
	echo Set WIP at app/ui/wip_$$module.py

.PHONY: transfer-wip
transfer-wip:
	@module=$(ui); \
	cp app/ui/wip_$$module.py app/ui/$$module.py; \
	cp app/ui/layouts/wip_$$module.grid.json app/ui/layouts/$$module.grid.json

.DEFAULT_GOAL := help
