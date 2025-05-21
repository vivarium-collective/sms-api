.PHONY: gateway 
gateway:
	@uvicorn gateway.app:app --reload --port 8080 --host 0.0.0.0

.PHONY: clean 
clean:
	@uv cache clean && rm -f uv.lock && rm -rf .venv

.PHONY: lock	
lock:
	@uv lock

.PHONY: sync 
sync:
	@make lock && uv sync --all-extras && pip install -e ../genEcoli && pip install -e ../vEcoli && pip install -e ../ecoli-notebooks && pip install -e ../../spatio-flux && make kernel

.PHONY: kernel
kernel:
	@rm -rf /Users/alexanderpatrie/Library/Jupyter/kernels/sms && uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=SMS

.PHONY: notebook
notebook:
	@make kernel && uv run --with jupyter jupyter lab

.PHONY: test 
test:
	@pytest -s tests/deliverables.py

.PHONY: install
install:
	@make clean && uv venv && uv sync && uv pip install pip