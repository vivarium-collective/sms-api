import asyncio
import gzip
import io
import os
import sys
import tarfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

import httpx
from httpx import AsyncClient
from tqdm import tqdm

from sms_api.analysis.models import AnalysisRun, ExperimentAnalysisDTO, OutputFile, TsvOutputFile
from sms_api.common.simulator_defaults import SimulationConfigFilename
from sms_api.simulation.models import HpcRun, ParcaDataset, Simulation, SimulationRun, Simulator, SimulatorVersion


class BaseUrl(StrEnum):
    RKE_PROD = "https://sms.cam.uchc.edu"
    RKE_DEV = "https://sms-dev.cam.uchc.edu"
    LOCAL = "http://localhost:8888"
    RKE_PROD_FORWARDED = "http://localhost:8000"
    RKE_DEV_FORWARDED = "http://localhost:1111"
    STANFORD_FORWARDED = "http://localhost:8080"
    STANFORD_DEV_FORWARDED = "http://localhost:62505"
    LOCAL_8080 = "http://localhost:8080"


DEFAULT_BASE_URL = BaseUrl.LOCAL_8080
DEFAULT_REQUEST_TIMEOUT = 1000

SUPPORTED_CONFIGS = [name.replace(".json", "") for name in SimulationConfigFilename.values()]


@asynccontextmanager
async def async_client(base_url: BaseUrl, timeout: int = 300) -> AsyncIterator[AsyncClient]:
    try:
        async with AsyncClient(base_url=base_url, timeout=timeout) as client:
            yield client
    finally:
        pass


class E2EDataService:
    base_url: BaseUrl
    client: httpx.Client

    def __init__(self, base_url: BaseUrl, timeout: int = 300) -> None:
        self.base_url = base_url
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    # -- Simulator --

    def get_simulator(self) -> SimulatorVersion:
        latest = self.submit_get_latest_simulator()
        uploaded = self.submit_upload_simulator(simulator=latest)
        status = "pending"
        try:
            while status not in ["completed", "failed"]:
                status = self.submit_get_simulator_build_status(simulator=uploaded)
                time.sleep(1.0)
        except Exception as e:
            raise httpx.HTTPError("Could not set up the simulator. Try again.") from e
        return uploaded

    def get_simulator_status(self, simulator_id: int) -> str:
        return self.submit_get_simulator_status(simulator_id=simulator_id)

    # -- Simulation --

    def run_workflow(
        self,
        params: httpx.QueryParams | None = None,
        experiment_id: str | None = None,
        simulator_id: int | None = None,
        config_filename: str | None = None,
        num_generations: int | None = None,
        num_seeds: int | None = None,
        description: str | None = None,
        run_parameter_calculator: bool | None = None,
        observables: list[str] | None = None,
    ) -> Simulation:
        simulation = self.submit_run_workflow(
            params=params,
            config_filename=config_filename,
            experiment_id=experiment_id,
            simulator_id=simulator_id,
            num_generations=num_generations,
            num_seeds=num_seeds,
            description=description,
            run_parameter_calculator=run_parameter_calculator,
            observables=observables,
        )
        return simulation

    def get_workflow(self, simulation_id: int) -> Simulation:
        return self.submit_get_workflow(simulation_id=simulation_id)

    def show_workflows(self) -> list[Simulation]:
        return self.submit_list_workflows()

    def show_simulators(self) -> list[SimulatorVersion]:
        return self.submit_list_simulators()

    def get_workflow_log(self, simulation_id: int, truncate: bool = True) -> str:
        return self.submit_get_workflow_log(simulation_id=simulation_id, truncate=truncate)

    def get_workflow_status(self, simulation_id: int) -> SimulationRun:
        return self.submit_get_workflow_status(simulation_id=simulation_id)

    def cancel_workflow(self, simulation_id: int) -> SimulationRun:
        return self.submit_cancel_workflow(simulation_id=simulation_id)

    def get_output_data_sync(self, simulation_id: int, dest: Path) -> Path:
        """Download simulation outputs synchronously (no async event loop required)."""
        simulation = self.submit_get_workflow(simulation_id=simulation_id)
        experiment_id = simulation.experiment_id
        output_path = dest / f"{experiment_id}.tar.gz"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.client.stream("POST", f"/api/v1/simulations/{simulation_id}/data") as response:
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}")
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        with tarfile.open(output_path, "r:gz") as tar:
            tar.extractall(output_path.parent)  # noqa: S202
        # .stem on .tar.gz gives "foo.tar", so strip both suffixes
        return output_path.parent / experiment_id

    async def get_output_data(self, simulation_id: int, dest: Path | None = None, timeout: int = 300) -> Path:
        if dest is None:
            dest = Path(os.getcwd()).absolute()
        archive_path = await self.submit_stream_output_data(
            simulation_id=simulation_id, output_dirpath=dest, timeout=timeout
        )
        if not isinstance(archive_path, Path):
            raise TypeError()
        with tarfile.open(archive_path, "r:gz") as tar:
            # Extract to parent dir - the tar already contains the experiment_id directory
            tar.extractall(archive_path.parent)  # noqa: S202
        # Return the extracted directory (archive stem is the experiment_id)
        extracted_dir = archive_path.parent / archive_path.stem
        return extracted_dir

    # -- Parca --

    def get_parca_datasets(self) -> list[ParcaDataset]:
        return self.submit_get_parca_datasets()

    def get_parca_status(self, parca_id: int) -> HpcRun:
        return self.submit_get_parca_status(parca_id=parca_id)

    # -- Analysis --

    def get_analysis(self, analysis_id: int) -> ExperimentAnalysisDTO:
        return self.submit_get_analysis(analysis_id=analysis_id)

    def get_analysis_status(self, analysis_id: int) -> AnalysisRun:
        return self.submit_get_analysis_status(analysis_id=analysis_id)

    def get_analysis_log(self, analysis_id: int) -> str:
        return self.submit_get_analysis_log(analysis_id=analysis_id)

    def get_analysis_plots(self, analysis_id: int) -> list[OutputFile]:
        return self.submit_get_analysis_plots(analysis_id=analysis_id)

    # -- Low-level HTTP methods: Simulator --

    def submit_get_latest_simulator(self, repo_url: str | None = None, branch: str | None = None) -> Simulator:
        try:
            from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO

            latest_response = self.client.get(
                url="/core/v1/simulator/latest",
                params={"git_branch": branch or DEFAULT_BRANCH, "git_repo_url": repo_url or DEFAULT_REPO},
            )
            return Simulator(**latest_response.json())
        except Exception as e:
            raise httpx.HTTPError(
                f"Could not get the latest simulator from the repo {repo_url} on branch {branch}"
            ) from e

    def submit_upload_simulator(self, simulator: Simulator, force: bool = False) -> SimulatorVersion:
        try:
            params = {"force": "true"} if force else {}
            uploaded_response = self.client.post(
                url="/core/v1/simulator/upload", json=simulator.model_dump(), params=params
            )
            return SimulatorVersion(**uploaded_response.json())
        except Exception as e:
            raise httpx.HTTPError(f"Could not build the simulator: {simulator.model_dump()}") from e

    def submit_list_simulators(self) -> list[SimulatorVersion]:
        try:
            simulators = self.client.get(url="/core/v1/simulator/versions")
            if simulators.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return [SimulatorVersion(**sim) for sim in simulators.json()["versions"]]
        except Exception as e:
            raise httpx.HTTPError("Could not load simulators") from e

    def submit_get_simulator_build_status(self, simulator: SimulatorVersion) -> str:
        try:
            status_update_response = self.client.get(
                url="/core/v1/simulator/status", params={"simulator_id": simulator.database_id}
            )
            if status_update_response.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return status_update_response.json().get("status", "")  # type: ignore[no-any-return]
        except Exception as e:
            raise httpx.HTTPError(f"Could not fetch build status for simulator: {simulator.model_dump()}") from e

    def submit_get_simulator_build_status_full(self, simulator_id: int) -> HpcRun:
        try:
            response = self.client.get(url="/core/v1/simulator/status", params={"simulator_id": simulator_id})
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return HpcRun(**response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not fetch build status for simulator {simulator_id}") from e

    def submit_get_simulator_status(self, simulator_id: int) -> str:
        try:
            status_update_response = self.client.get(
                url="/core/v1/simulator/status", params={"simulator_id": simulator_id}
            )
            if status_update_response.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return status_update_response.json().get("status", "")  # type: ignore[no-any-return]
        except Exception as e:
            raise httpx.HTTPError(f"Could not fetch build status for simulator with id: {simulator_id}") from e

    # -- Low-level HTTP methods: Simulation --

    def submit_run_workflow(
        self,
        params: httpx.QueryParams | None = None,
        experiment_id: str | None = None,
        simulator_id: int | None = None,
        config_filename: str | None = None,
        num_generations: int | None = None,
        num_seeds: int | None = None,
        description: str | None = None,
        run_parameter_calculator: bool | None = None,
        observables: list[str] | None = None,
    ) -> Simulation:
        if params is not None:
            query_params = params
        else:
            # Build query items — httpx needs repeated keys for list params
            items: list[tuple[str, str | int | float | bool | None]] = [
                (k, str(v))
                for k, v in {
                    "simulator_id": simulator_id,
                    "simulation_config_filename": config_filename,
                    "num_generations": num_generations,
                    "num_seeds": num_seeds,
                    "description": description,
                    "experiment_id": experiment_id,
                    "run_parca": run_parameter_calculator,
                }.items()
                if v is not None
            ]
            if observables:
                items.extend(("observables", obs) for obs in observables)
            query_params = httpx.QueryParams(items)
        try:
            simulation_response = self.client.post(
                url="/api/v1/simulations",
                params=query_params,
            )
            if simulation_response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {simulation_response.status_code}: {simulation_response.text}")  # noqa: TRY301
            return Simulation(**simulation_response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not submit a new simulation workflow with params {query_params}: {e}") from e

    def submit_get_workflow_status(self, simulation_id: int) -> SimulationRun:
        try:
            status_update_response = self.client.get(url=f"/api/v1/simulations/{simulation_id}/status")
            if status_update_response.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return SimulationRun(**status_update_response.json())
        except Exception as e:
            raise httpx.HTTPError(f"Could not load status for simulation {simulation_id}") from e

    def submit_cancel_workflow(self, simulation_id: int) -> SimulationRun:
        try:
            response = self.client.delete(url=f"/api/v1/simulations/{simulation_id}/cancel")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return SimulationRun(**response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not cancel simulation {simulation_id}") from e

    def submit_get_output_data(self, simulation_id: int) -> list[TsvOutputFile]:
        try:
            data_response = self.client.post(url=f"/api/v1/simulations/{simulation_id}/data")
            if data_response.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return [TsvOutputFile(**output) for output in data_response.json()]
        except Exception as e:
            raise httpx.HTTPError("Could not load simulation data") from e

    def submit_get_workflow(self, simulation_id: int) -> Simulation:
        try:
            simulation = self.client.get(url=f"/api/v1/simulations/{simulation_id}")
            if simulation.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return Simulation(**simulation.json())
        except Exception as e:
            raise httpx.HTTPError("Could not load simulation data") from e

    def submit_list_workflows(self) -> list[Simulation]:
        try:
            simulations = self.client.get(url="/api/v1/simulations")
            if simulations.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return [Simulation(**sim) for sim in simulations.json()]
        except Exception as e:
            raise httpx.HTTPError("Could not load simulation data") from e

    def submit_get_workflow_log(self, simulation_id: int, truncate: bool = True) -> str:
        try:
            structured_log = self.client.get(
                url=f"/api/v1/simulations/{simulation_id}/log",
                params={"truncate": str(truncate).lower()},
            )
            if structured_log.status_code != 200:
                raise httpx.HTTPError("Error!")  # noqa: TRY301
            return structured_log.text
        except Exception as e:
            raise httpx.HTTPError("Could not load simulation log") from e

    # -- Low-level HTTP methods: Parca --

    def submit_get_parca_datasets(self) -> list[ParcaDataset]:
        try:
            response = self.client.get(url="/core/v1/simulation/parca/versions")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return [ParcaDataset(**ds) for ds in response.json()]
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError("Could not load parca datasets") from e

    def submit_get_parca_status(self, parca_id: int) -> HpcRun:
        try:
            response = self.client.get(url="/core/v1/simulation/parca/status", params={"parca_id": parca_id})
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return HpcRun(**response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not load parca status for id {parca_id}") from e

    # -- Low-level HTTP methods: Analysis --

    def submit_get_analysis(self, analysis_id: int) -> ExperimentAnalysisDTO:
        try:
            response = self.client.get(url=f"/api/v1/analyses/{analysis_id}")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return ExperimentAnalysisDTO(**response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not load analysis {analysis_id}") from e

    def submit_get_analysis_status(self, analysis_id: int) -> AnalysisRun:
        try:
            response = self.client.get(url=f"/api/v1/analyses/{analysis_id}/status")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return AnalysisRun(**response.json())
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not load analysis status for id {analysis_id}") from e

    def submit_get_analysis_log(self, analysis_id: int) -> str:
        try:
            response = self.client.get(url=f"/api/v1/analyses/{analysis_id}/log")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return response.text
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not load analysis log for id {analysis_id}") from e

    def submit_get_analysis_plots(self, analysis_id: int) -> list[OutputFile]:
        try:
            response = self.client.get(url=f"/api/v1/analyses/{analysis_id}/plots")
            if response.status_code != 200:
                raise httpx.HTTPError(f"Server returned {response.status_code}: {response.text}")  # noqa: TRY301
            return [OutputFile(**p) for p in response.json()]
        except httpx.HTTPError:
            raise
        except Exception as e:
            raise httpx.HTTPError(f"Could not load analysis plots for id {analysis_id}") from e

    # -- Streaming output download --

    async def submit_stream_output_data(  # noqa: C901
        self, simulation_id: int, show_progress: bool = True, output_dirpath: Path | None = None, timeout: int = 300
    ) -> set[str] | Path:
        """
        Download simulation output data as a streamable tar.gz archive.

        Args:
            simulation_id: The ID of the simulation to download data for.
            show_progress: If True, display a tqdm progress bar during download.
            output_dirpath: If provided, stream directly to a file
            found at: <OUTPUT_PATH>/<EXPERIMENT_ID>.tar.gz (memory-efficient
                for large archives). If None, keep in memory and return file basenames.

        Returns:
            If output_path is None: Set of archived file basenames.
            If output_path is provided: Path to the downloaded file.
        """
        async with async_client(base_url=self.base_url, timeout=timeout) as client:
            spinner_task = None
            if show_progress:
                # Start spinner while waiting for server to prepare data
                spinner_task = asyncio.create_task(
                    self._show_spinner(f"Waiting for server to gather simulation {simulation_id} files from HPC")
                )

            try:
                # Use stream=True to test actual streaming behavior
                async with client.stream("POST", f"/api/v1/simulations/{simulation_id}/data") as response:
                    # Stop spinner once we get a response
                    if spinner_task:
                        spinner_task.cancel()
                        try:  # noqa: SIM105
                            await spinner_task
                        except asyncio.CancelledError:
                            pass
                        # Clear the spinner line
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        sys.stdout.flush()

                    if response.status_code != 200:
                        body = await response.aread()
                        raise httpx.HTTPError(message=body.decode(errors="replace"))  # noqa: TRY301

                    # Validate headers
                    if response.headers["content-type"] != "application/gzip":
                        raise httpx.HTTPError(  # noqa: TRY301
                            f"Unexpected MIME type for archive. Expected: {'application/gzip'}; "
                            f"Got: {response.headers['content-type']}"
                        )

                    if "attachment" not in response.headers.get("content-disposition", ""):
                        raise httpx.HTTPError(  # noqa: TRY301
                            f"Unexpected content-disposition header. Expected: {'attachment'}; "
                            f"Got: {response.headers.get('content-disposition', '')}"
                        )

                    # Get total size if available for progress bar
                    total_size = response.headers.get("content-length")
                    total_bytes = int(total_size) if total_size else None

                    if output_dirpath is not None:
                        # Stream directly to disk (memory-efficient for large files)
                        simulation = self.submit_get_workflow(simulation_id=simulation_id)
                        experiment_id = simulation.experiment_id
                        output_path = output_dirpath / f"{experiment_id}.tar.gz"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            if show_progress:
                                with tqdm(
                                    total=total_bytes,
                                    unit="B",
                                    unit_scale=True,
                                    unit_divisor=1024,
                                    desc=f"Downloading to {output_path.name}",
                                    dynamic_ncols=True,
                                ) as pbar:
                                    async for chunk in response.aiter_bytes():
                                        f.write(chunk)
                                        pbar.update(len(chunk))
                            else:
                                async for chunk in response.aiter_bytes():
                                    f.write(chunk)
                        return output_path
                    else:
                        # Collect in memory (original behavior)
                        chunks = []
                        if show_progress:
                            with tqdm(
                                total=total_bytes,
                                unit="B",
                                unit_scale=True,
                                unit_divisor=1024,
                                desc="Downloading",
                                dynamic_ncols=True,
                            ) as pbar:
                                async for chunk in response.aiter_bytes():
                                    chunks.append(chunk)
                                    pbar.update(len(chunk))
                        else:
                            async for chunk in response.aiter_bytes():
                                chunks.append(chunk)

                        # Verify we actually got data
                        if len(chunks) < 1:
                            raise httpx.HTTPError("No data was streamed.")  # noqa: TRY301
                        content = b"".join(chunks)

            except Exception:
                if spinner_task and not spinner_task.done():
                    spinner_task.cancel()
                raise

        # If we got here, output_path was None - process in-memory content
        # Validate it's valid gzip
        decompressed = gzip.decompress(content)

        # Validate it's a valid tar archive with expected structure
        tar_buffer = io.BytesIO(decompressed)
        with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
            archived_names = set(tar.getnames())
            # Extract basenames from archived files for comparison
            archived_basenames = {Path(name).name for name in archived_names}

        return archived_basenames

    @staticmethod
    async def _show_spinner(message: str) -> None:
        """Display a spinner animation while waiting."""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        idx = 0
        while True:
            sys.stdout.write(f"\r{spinner_chars[idx]} {message}...")
            sys.stdout.flush()
            idx = (idx + 1) % len(spinner_chars)
            await asyncio.sleep(0.1)


def get_data_service(base_url: BaseUrl | str | None = None, timeout: int | None = None) -> E2EDataService:
    return E2EDataService(
        base_url=BaseUrl(base_url) if base_url else DEFAULT_BASE_URL, timeout=timeout or DEFAULT_REQUEST_TIMEOUT
    )
