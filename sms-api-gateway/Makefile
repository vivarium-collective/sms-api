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

.PHONY: gateway
gateway:
	@uv run uvicorn gateway.main:app --reload --port 8080 --host 0.0.0.0 --ws websockets --ws-max-size 10000000

.PHONY: clean
clean:
	@rm -rf uv.lock && rm -rf .venv && rm -rf sms-api.egg-info && uv run pip cache purge && uv cache clean

.PHONY: lock
lock:
	@rm -rf uv.lock && uv lock

.PHONY: kernel
kernel:
	@rm -rf /Users/alexanderpatrie/Library/Jupyter/kernels/sms-gateway && uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=sms-gateway

.PHONY: notebook
notebook:
	@make kernel && uv run --with jupyter jupyter lab

.PHONY: cleanInstall
cleanInstall:
	@make clean
	@uv sync
	@uv pip install pip
	@uv pip install fastapi pydantic python-multipart python-dotenv aiohttp fsspec h5py ipykernel rustworkx cryptography redis broadcaster websockets uvicorn
	@uv pip install ../../vEcoli
	@uv pip install ../../genEcoli
	@uv pip install ../../bigraph-schema
	@uv pip install ../../process-bigraph
	@uv pip freeze > requirements.txt
	@uv add -r requirements.txt

.PHONY: runSim
runSim:
	@uv run tests/test_client.py

.PHONY: socket 
socket:
	@uv run uvicorn gateway.broadcasting:app --reload --port 8080 --host 0.0.0.0
