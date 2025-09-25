import httpx

from sms_api.api.client import Client
from sms_api.api.client.api.simulations.run_ecoli_simulation import asyncio_detailed as run_simulation_async
from sms_api.api.client.models import (
    BodyRunEcoliSimulation,
    HTTPValidationError,
    experiment_request,
)
from sms_api.api.client.types import Response
from sms_api.simulation.models import EcoliSimulationDTO


class ClientWrapper:
    """
    A wrapper for the client that provides a consistent interface for making requests.
    """

    base_url: str
    api_client: Client | None = None
    httpx_client: httpx.Client | None = None

    def __init__(self, base_url: str):
        self.base_url = base_url

    def _get_api_client(self) -> Client:
        if self.api_client is None:
            self.httpx_client = httpx.Client(base_url=self.base_url)
            self.api_client = Client(base_url=self.base_url, raise_on_unexpected_status=True)
            self.api_client.set_httpx_client(self.httpx_client)
        return self.api_client

    async def run_simulation(self) -> EcoliSimulationDTO:
        api_client = self._get_api_client()
        response: Response[EcoliSimulationDTO | HTTPValidationError] = await run_simulation_async(  # type: ignore[assignment]
            client=api_client,
            body=BodyRunEcoliSimulation(request=experiment_request.ExperimentRequest(experiment_id="test")),
        )
        if response.status_code == 200 and isinstance(response.parsed, EcoliSimulationDTO):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")
