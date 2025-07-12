import httpx

from sms_api.api.client import Client
from sms_api.api.client.api.simulations.get_parca_versions import sync_detailed as get_parca_versions_sync
from sms_api.api.client.api.simulations.run_simulation import sync_detailed as run_simulation_sync
from sms_api.api.client.api.simulators.get_core_simulator_version import sync_detailed as get_simulators_sync
from sms_api.api.client.models import (
    EcoliExperiment,
    EcoliSimulationRequest,
    HTTPValidationError,
    ParcaDataset,
    RegisteredSimulators,
)
from sms_api.api.client.types import Response


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

    def run_simulation(self, ecoli_simulation_request: EcoliSimulationRequest) -> EcoliExperiment:
        api_client = self._get_api_client()
        response: Response[EcoliExperiment | HTTPValidationError] = run_simulation_sync(
            client=api_client, body=ecoli_simulation_request
        )
        if response.status_code == 200 and isinstance(response.parsed, EcoliExperiment):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    def get_simulators(self) -> RegisteredSimulators:
        api_client = self._get_api_client()
        response: Response[RegisteredSimulators] = get_simulators_sync(client=api_client)
        if response.status_code == 200:
            return response.parsed or RegisteredSimulators(versions=[])
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    def get_parcas(self) -> list[ParcaDataset]:
        api_client = self._get_api_client()
        response: Response[list[ParcaDataset]] = get_parca_versions_sync(client=api_client)
        if response.status_code == 200:
            return response.parsed or []
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")
