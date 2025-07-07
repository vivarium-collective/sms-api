import marimo

__generated_with = "0.14.10"
app = marimo.App(width="medium")


@app.cell
def _():
    from typing import Callable

    import httpx
    import requests

    from sms_api.common.gateway.models import ServerMode

    client = httpx.Client()
    aioclient = httpx.AsyncClient()
    session = requests.Session()
    return Callable, ServerMode, aioclient, httpx


@app.cell
def _(ServerMode, httpx):
    def endpoint(path: str, mode: ServerMode | None = None):
        root = httpx.URL(mode or ServerMode.DEV)
        return root.join(path)

    return


@app.cell
def _(Callable, aioclient, httpx):
    async def request(func: Callable[..., httpx.Response], path: str, **kwargs):
        global aioclient
        try:
            url = httpx.URL(f"http://localhost:8000{path}")
            response = await func(url=url, **kwargs)
            response.raise_for_status()
            payload = response.json()
            return payload
        except Exception as e:
            raise httpx.HTTPError(message=e)

    async def get(path: str, **kwargs):
        return await request(aioclient.get, path=path, **kwargs)

    async def post(path: str, **kwargs):
        return await request(aioclient.post, path=path, **kwargs)

    return (get,)


@app.cell
async def _(get):
    from sms_api.simulation.models import EcoliSimulationRequest, SimulatorVersion

    await get("/")
    return EcoliSimulationRequest, SimulatorVersion


@app.cell
async def _(EcoliSimulationRequest, SimulatorVersion, httpx):
    import json

    async def run_simulation():
        async with httpx.AsyncClient() as client:
            simulator = await client.get("http://localhost:8000/core/simulator/versions")
            simulator = simulator.json()
            data = EcoliSimulationRequest(
                simulator=SimulatorVersion(**simulator["versions"][0]), parca_dataset_id=1, variant_config={}
            )
            response = await client.post(
                "http://localhost:8000/core/simulation/run",
                content=json.dumps(data.model_dump()),
                headers={"Content-Type": "application/json"},
            )
            return response.json()

    await run_simulation()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
