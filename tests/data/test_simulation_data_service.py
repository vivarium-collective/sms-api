import os

import pandas as pd
import pytest

from sms_api.config import get_settings
from sms_api.data.simulation_data_service import ObservableLabelType, get_bulk_dataframe, get_genes_dataframe


@pytest.mark.skipif(len(get_settings().vecoli_simdata_path) == 0, reason="Sim Data path not provided")
@pytest.mark.asyncio
def test_get_bulk_dataframe() -> None:
    variant = 0
    seed = 9  # 30
    gen = 1  # 22
    agent_id = "0"  # "0000000000000000000000"
    expid = "sms_multigeneration"  # "sms_multiseed"
    home = os.environ["HOME"]
    out_dir = f"{home}/sms/vEcoli/out"
    sim_data_path = f"{home}/sms/vEcoli/kb/simData.cPickle"
    label_type = ObservableLabelType.BIOCYC
    # bulk = BulkDataframe(expid, variant, seed, gen, agent_id, label_type, out_dir, sim_data_path)
    env = get_settings()
    env.simulation_outdir = out_dir
    env.vecoli_simdata_path = sim_data_path
    ids = ["--TRANS-ACENAPHTHENE-12-DIOL", "ACETOLACTSYNI-CPLX", "CPD-3729"]
    df = get_bulk_dataframe(
        experiment_id=expid,
        env=env,
        variant=variant,
        seed=seed,
        generation=gen,
        agent_id=agent_id,
        label_type=label_type,
        observable_ids=ids,
    )
    assert isinstance(df, pd.DataFrame)
    assert all([id in df[["bulk_molecules"]].to_numpy().flatten() for id in ids])
    print(df.head())


@pytest.mark.skipif(len(get_settings().vecoli_simdata_path) == 0, reason="Sim Data path not provided")
@pytest.mark.asyncio
def test_get_genes_dataframe() -> None:
    variant = 0
    seed = 9  # 30
    gen = 1  # 22
    agent_id = "0"  # "0000000000000000000000"
    expid = "sms_multigeneration"  # "sms_multiseed"
    env = get_settings()
    ids = ["alr", "ruvB"]
    df = get_genes_dataframe(
        env=env, variant=variant, experiment_id=expid, seed=seed, generation=gen, agent_id=agent_id
    )
    assert isinstance(df, pd.DataFrame)
    assert all([id in df[["gene names"]].to_numpy().flatten() for id in ids])
    print(df.head())
