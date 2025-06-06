.PHONY: freeze
freeze:
	@uv pip freeze

.PHONY: add
dep:
	@uv pip install $(pkg)
	@echo $(uv pip freeze | grep typer) >> requirements.txt

.PHONY: exportEnv
exportEnv:
	@uv pip freeze > requirements.txt

.PHONY: clean
clean:
	@rm -rf uv.lock && rm -rf .venv && rm -rf sms_api_server.egg-info && uv run pip cache purge && uv cache clean

.PHONY: lock
lock:
	@rm -rf uv.lock && uv lock

.PHONY: kernel
kernel:
	@rm -rf /Users/alexanderpatrie/Library/Jupyter/kernels/sms-gateway && uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=sms-gateway

.PHONY: notebook
notebook:
	@make kernel && uv run --with jupyter jupyter lab --NotebookApp.token=dev --port=8888

.PHONY: cleanInstall
cleanInstall:
	@make clean
	@uv sync
	@uv pip install pip
	@uv pip install fastapi pydantic python-multipart python-dotenv aiohttp fsspec h5py pysimdjson websockets
	@uv pip install --editable ./vEcoli
	@uv pip freeze > requirements.txt
	@uv add -r requirements.txt
# @uv pip install ../../bigraph-schema
# @uv pip install ../../process-bigraph

.PHONY: install
install:
	@uv sync

.PHONY: py
py:
	@uv run python

.PHONY: simulations
simulations:
	@uv run python controller/run_simulation.py

.PHONY: results
results:
	@uv run python controller/get_results.py

.PHONY: server
server:
	@make simulations & make results
