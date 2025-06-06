def endpoint_prefix(version: str, api_name: str | None = None):
    url = f"/api/{version}"
    return (url + f"/{api_name}") if api_name is not None else url



