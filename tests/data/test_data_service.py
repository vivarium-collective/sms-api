from sms_api.data.data_service import AnalysisType, SimulationDataServiceFS


def test_get_outputs():
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
