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

.PHONY: server 
server:
	@uv run server/main.py 

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
	@make kernel && uv run --with jupyter jupyter lab --NotebookApp.token=dev --port=8888

.PHONY: cleanInstall
cleanInstall:
	@make clean
	@uv sync
	@uv pip install pip
	@uv pip install fastapi pydantic python-multipart python-dotenv aiohttp fsspec h5py ipykernel rustworkx cryptography uvicorn networkx sseclient-py equilibrator-api equilibrator-assets
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

.PHONY: demo 
demo:
	@make gateway & make notebook

.PHONY: py 
py:
	@uv run python

.PHONY: mongo
mongo:
	@docker run -d --name mongodb -p 27017:27017 mongo 

.PHONY: redis 
redis:
	@docker run -d --name redis -p 6379:6379 redis

.PHONY: nats 
nats:
	@docker run -d --name nats -p 4222:4222 nats