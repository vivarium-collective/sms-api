.PHONY: gateway
gateway:
	@uvicorn gateway.app:app --reload --port 8080 --host 0.0.0.0

.PHONY: clean
clean:
	@rm -rf uv.lock && rm -rf .venv && rm -rf sms-api.egg-info && uv cache clean

.PHONY: lock
lock:
	@rm -rf uv.lock && uv lock

.PHONY: kernel
kernel:
	@rm -rf /Users/alexanderpatrie/Library/Jupyter/kernels/smsapi && uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=smsapi

.PHONY: notebook
notebook:
	@make kernel && uv run --with jupyter jupyter lab

.PHONY: install
install:
	@make clean && uv venv && uv sync && uv pip install pip && make kernel

.PHONY: install-requirements
install-requirements:
	@make clean
	@uv sync
	@uv pip install pip
	@uv pip install fastapi pydantic python-multipart python-dotenv aiohttp fsspec h5py ipykernel rustworkx
	@uv pip install ../vEcoli
	@uv pip install ../genEcoli
	@uv pip install ../bigraph-schema
	@uv pip install ../process-bigraph
	@uv pip install ./sms-api-gateway
	@uv pip install vivarium-interface
	@uv pip freeze > requirements.txt
	@uv add -r requirements.txt

.PHONY: compose
compose:
    @docker compose -f ./sms-api-gateway/docker-compose.yml -f ./sms-api-server/docker-compose.yml up

