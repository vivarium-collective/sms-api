import os
from pathlib import Path

import pytest

from sms_api.config import get_settings
from sms_api.data.data_service import AnalysisType, SimulationDataServiceFS

ENV = get_settings()
DATA_PATH_EXISTS = os.path.exists(Path(str(ENV.hpc_parca_base_path)) / "default" / "kb")


@pytest.mark.skipif(not DATA_PATH_EXISTS, reason="Simulation data path not available")
def test_get_outputs() -> None:
    # TODO: make this a fixture mock
    service = SimulationDataServiceFS()
    expid = "sms_multigeneration"
    outdir = service.env.simulation_outdir.__str__()
    partitions = {
        "experiment_id": "sms_multigeneration",
        "variant": "0",
        "lineage_seed": "5",
        "generation": "1",
        "agent_id": "0",
    }
    df = service.get_outputs(
        analysis_type=AnalysisType.MULTISEED, exp_select=expid, partitions_all=partitions, simulation_outdir=outdir
    )
    assert "bulk" in list(df.columns)
