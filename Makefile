.PHONY: gateway 
gateway:
	@uvicorn gateway.app:app --reload --port 8080 --host 0.0.0.0

.PHONY: clean 
clean:
	@uv cache clean

.PHONY: lock	
lock:
	@uv cache clean && uv lock

.PHONY: sync 
sync:
	@make lock && uv sync --all-extras && pip install -e ../genEcoli && pip install -e ../vEcoli && pip install -e ../ecoli-notebooks && pip install -e ../../spatio-flux && make kernel

.PHONY: kernel
kernel:
	@rm -rf /Users/alexanderpatrie/Library/Jupyter/kernels/sms-api && python -m ipykernel install --user --name sms-api --display-name "Python(SMS)"

.PHONY: test 
test:
	@pytest -s tests/deliverables.py

.PHONY: install
install:
	@make lock && uv sync && python scripts/install.py