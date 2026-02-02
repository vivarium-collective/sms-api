import os
import marimo as mo
import pytest

from sms_api.config import get_settings
from sms_api.data.data_service import AnalysisType, SimulationDataServiceFS

ENV = get_settings()


# Check if local data path exists (returns False if path prefixes not configured)
def _check_data_path_exists() -> bool:
    try:
        local_path = ENV.hpc_parca_base_path.local_path() / "default" / "kb"
        return os.path.exists(local_path)
    except ValueError:
        # path_local_prefix/path_remote_prefix not configured
        return False


DATA_PATH_EXISTS = _check_data_path_exists()


@pytest.mark.skipif(not DATA_PATH_EXISTS, reason="Simulation data path not available")
def test_get_outputs() -> None:
    # TODO: make this a fixture mock
    service = SimulationDataServiceFS()
    expid = "sms_multigeneration"
    outdir = str(service.env.simulation_outdir.local_path())
    partitions = {
        "experiment_id": "sms_multigeneration",
        "variant": "0",
        "lineage_seed": "5",
        "generation": "1",
        "agent_id": "0",
    }
    df = service.get_plot_df_bulk(
        analysis_type=AnalysisType.MULTISEED,
        partitions_all=partitions,
        bulk_ids_selected=["WATER","ATP"],
        datapoints_cap=2000,
        molecule_id_ui=mo.ui.radio(options=["Common name", "BioCyc ID"], value="BioCyc ID")
    )
    assert "bulk_counts" in list(df.columns)
