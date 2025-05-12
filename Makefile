.PHONY: gateway 
gateway:
	@uvicorn gateway.app:app --reload --port 8080 --host 0.0.0.0