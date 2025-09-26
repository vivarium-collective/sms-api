import asyncio
import io
from pathlib import Path

import httpx
import polars

from sms_api.api.client import Client
from sms_api.api.client.api.analyses.fetch_experiment_analysis import (
    asyncio_detailed as fetch_experiment_analysis_async,
)
from sms_api.api.client.api.analyses.get_analysis_status import asyncio_detailed as get_analysis_status_async
from sms_api.api.client.api.analyses.get_analysis_tsv import asyncio_detailed as get_analysis_tsv_async
from sms_api.api.client.api.analyses.run_experiment_analysis import asyncio_detailed as run_analysis_async
from sms_api.api.client.api.simulations.run_ecoli_simulation import asyncio_detailed as run_simulation_async
from sms_api.api.client.models import (
    BodyRunEcoliSimulation,
    EcoliSimulationDTO,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    ExperimentRequest,
    HTTPValidationError,
    OutputFile,
    SimulationRun,
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

    async def run_simulation(self, request: ExperimentRequest) -> EcoliSimulationDTO:
        api_client = self._get_api_client()
        response: Response[EcoliSimulationDTO | HTTPValidationError] = await run_simulation_async(
            client=api_client, body=BodyRunEcoliSimulation(request=request)
        )
        if response.status_code == 200 and isinstance(response.parsed, EcoliSimulationDTO):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    async def run_analysis(self, request: ExperimentAnalysisRequest) -> ExperimentAnalysisDTO:
        api_client = self._get_api_client()
        response: Response[ExperimentAnalysisDTO | HTTPValidationError] = await run_analysis_async(
            client=api_client, body=request
        )
        if response.status_code == 200 and isinstance(response.parsed, ExperimentAnalysisDTO):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    async def get_analysis(self, database_id: int) -> ExperimentAnalysisDTO:
        api_client = self._get_api_client()
        response: Response[ExperimentAnalysisDTO | HTTPValidationError] = await fetch_experiment_analysis_async(
            client=api_client, id=database_id
        )
        if response.status_code == 200 and isinstance(response.parsed, ExperimentAnalysisDTO):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    async def get_analysis_status(self, analysis: ExperimentAnalysisDTO) -> SimulationRun:
        api_client = self._get_api_client()
        response: Response[SimulationRun | HTTPValidationError] = await get_analysis_status_async(
            client=api_client, id=analysis.database_id
        )
        if response.status_code == 200 and isinstance(response.parsed, SimulationRun):
            return response.parsed
        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")

    async def get_tsv_outputs(self, analysis: ExperimentAnalysisDTO, outfile: Path | None = None) -> list[OutputFile]:
        api_client = self._get_api_client()
        response: Response[list[OutputFile] | HTTPValidationError] = await get_analysis_tsv_async(
            client=api_client, id=analysis.database_id
        )
        if response.status_code == 200 and isinstance(response.parsed, list):
            outputs = response.parsed
            if outfile is not None:
                lines = ["".join(output.content).split("\n") for output in outputs]
                if outfile is not None:
                    with open(outfile, "w") as f:
                        for item in lines:
                            f.write(f"{item}\n")

            return outputs

        else:
            raise TypeError(f"Unexpected response status: {response.status_code}, content: {type(response.content)}")


def format_tsv_string(output: OutputFile) -> str:
    """
    Convert a raw string containing escaped \\t and \\n into a proper TSV text.
    """
    raw_string = output.content
    return raw_string.encode("utf-8").decode("unicode_escape")


def tsv_string_to_polars_df(output: OutputFile) -> polars.DataFrame:
    """
    Parse a TSV-formatted string into a Polars DataFrame.
    """
    formatted = format_tsv_string(output)
    return polars.read_csv(io.StringIO(formatted), separator="\t")


async def test_client_get_tsv_outputs() -> None:
    base_url = "https://sms.cam.uchc.edu"
    dbid = 1
    client = ClientWrapper(base_url=base_url)
    analysis = await client.get_analysis(database_id=dbid)
    outputs: list[OutputFile] = await client.get_tsv_outputs(analysis=analysis)
    output_i = outputs[0]
    df = tsv_string_to_polars_df(output_i)
    print(df)


if __name__ == "__main__":
    asyncio.run(test_client_get_tsv_outputs())
