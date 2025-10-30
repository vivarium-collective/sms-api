import itertools
import os
from enum import StrEnum
from typing import Any, LiteralString

import duckdb
import numpy as np
import pandas as pd
from ecoli.library.parquet_emitter import dataset_sql
from ecoli.library.sim_data import LoadSimData

from sms_api.config import Settings

PARTITION_GROUPS = {
    "multiseed": ["experiment_id", "variant"],
    "multigeneration": ["experiment_id", "variant", "lineage_seed"],
    "multidaughter": ["experiment_id", "variant", "lineage_seed", "generation"],
    "single": [
        "experiment_id",
        "variant",
        "lineage_seed",
        "generation",
        "agent_id",
    ],
}

### -- Public -- ###


class ObservableLabelType(StrEnum):
    BIOCYC = "biocyc"  # currently, bulk_sp_plot
    COMMON = "common name"


### -- genes df -- ###


def get_genes_dataframe(
    experiment_id: str,
    env: Settings,
    observable_ids: list[str] | None = None,
    variant: int = 0,
    seed: int = 0,
    generation: int = 0,
    agent_id: str = "0",
    label_type: ObservableLabelType = ObservableLabelType.BIOCYC,
) -> pd.DataFrame:
    # - this chunk is always required, regardless of dataframe - #
    sim_data_path = env.vecoli_simdata_path
    out_dir = env.simulation_outdir
    sim_data = LoadSimData(sim_data_path).sim_data
    variant = 0
    seed = 30
    gen = 22
    agent_id = "0000000000000000000000"
    expid = "sms_multiseed"
    (
        bulk_ids,
        bulk_ids_biocyc,
        bulk_names_unique,
        bulk_common_names,
        rxn_ids,
        cistron_data,
        mrna_cistron_ids,
        mrna_cistron_names,
    ) = get_ids(sim_data_path, sim_data)
    dbf_dict = partitions_dict("single", expid, variant, seed, gen, agent_id)
    db_filter = get_db_filter(dbf_dict)
    history_sql_filtered = get_filtered_query(out_dir, expid, db_filter)
    output_loaded = load_outputs(history_sql_filtered)

    mrna_select = mrna_cistron_names

    mrna_mtx = np.stack(output_loaded["listeners__rna_counts__full_mRNA_cistron_counts"])

    mrna_idxs = [mrna_cistron_names.index(gene_id) for gene_id in mrna_select]

    mrna_trajs = [mrna_mtx[:, mrna_idx] for mrna_idx in mrna_idxs]

    mrna_plot_dict = {key: val for (key, val) in zip(mrna_select, mrna_trajs)}

    mrna_plot_dict["time"] = output_loaded["time"]

    mrna_plot_df = pd.DataFrame(mrna_plot_dict)

    mrna_df_long = mrna_plot_df.melt(
        id_vars=["time"],  # Columns to keep as identifier variables
        var_name="gene names",  # Name for the new column containing original column headers
        value_name="counts",  # Name for the new column containing original column values
    )

    mrna_df = downsample(mrna_df_long)
    return mrna_df[mrna_df["gene names"].isin(observable_ids)] if observable_ids is not None else mrna_df


def get_bulk_dataframe(
    experiment_id: str,
    env: Settings,
    observable_ids: list[str] | None = None,
    variant: int = 0,
    seed: int = 0,
    generation: int = 0,
    agent_id: str = "0",
    label_type: ObservableLabelType = ObservableLabelType.BIOCYC,
    # cache: bool = False
) -> pd.DataFrame:
    df = BulkDataframe(
        expid=experiment_id,
        variant=variant,
        seed=seed,
        gen=generation,
        agent_id=agent_id,
        label_type=label_type,
        out_dir=env.simulation_outdir,
        sim_data_path=env.vecoli_simdata_path,
    )
    # if cache:
    #     import redis
    #     r = redis.Redis(host='localhost', port=6379, db=0)
    # return df[observable_ids] if observable_ids is not None else df
    return df[df["bulk_molecules"].isin(observable_ids)] if observable_ids is not None else df


def BulkDataframe(
    expid: str,
    variant: int,
    seed: int,
    gen: int,
    agent_id: str,
    label_type: ObservableLabelType,
    out_dir: str,
    sim_data_path: str,
) -> pd.DataFrame:
    sim_data = LoadSimData(sim_data_path).sim_data
    dbf_dict = partitions_dict("single", expid, variant, seed, gen, agent_id)
    db_filter = get_db_filter(dbf_dict)
    history_sql_filtered = get_filtered_query(out_dir, expid, db_filter)
    outputs_loaded = load_outputs(history_sql_filtered)
    (
        bulk_ids,
        bulk_ids_biocyc,
        bulk_names_unique,
        bulk_common_names,
        rxn_ids,
        cistron_data,
        mrna_cistron_ids,
        mrna_cistron_names,
    ) = get_ids(sim_data_path, sim_data)
    bulk_mtx = get_bulk_mtx(outputs_loaded)
    sp_trajs = get_sp_trajs(
        bulk_mtx,
        bulk_names_unique,
        MoleculeIdType.BULK if label_type == label_type.BIOCYC else MoleculeIdType.COMMON,
        bulk_names_unique,
        bulk_common_names,
        bulk_ids_biocyc,
    )
    plot_df = get_plot_df(outputs_loaded, bulk_names_unique, sp_trajs)
    return _get_bulk_df(plot_df)


### -- internal -- ###


def _get_bulk_df(plot_df: pd.DataFrame):
    df_long = plot_df.melt(
        id_vars=["time"],  # Columns to keep as identifier variables
        var_name="bulk_molecules",  # Name for the new column containing original column headers
        value_name="counts",  # Name for the new column containing original column values
    )
    # df_long = plot_df.unpivot(
    #     index=["time"],  # Columns to keep as identifier variables
    #     variable_name="bulk_molecules",  # Name for the new column containing original column headers
    #     value_name="counts",  # Name for the new column containing original column values
    # )
    return downsample(df_long)


def get_genes_df(output_loaded: dict[str, Any], mrna_cistron_names, mrna_ids):
    mrna_mtx = np.stack(output_loaded["listeners__rna_counts__full_mRNA_cistron_counts"])

    mrna_idxs = [mrna_cistron_names.index(gene_id) for gene_id in mrna_ids]

    mrna_trajs = [mrna_mtx[:, mrna_idx] for mrna_idx in mrna_idxs]

    mrna_plot_dict = {key: val for (key, val) in zip(mrna_ids, mrna_trajs)}

    mrna_plot_dict["time"] = output_loaded["time"]

    mrna_plot_df = pd.DataFrame(mrna_plot_dict)

    mrna_df_long = mrna_plot_df.melt(
        id_vars=["time"],  # Columns to keep as identifier variables
        var_name="gene names",  # Name for the new column containing original column headers
        value_name="counts",  # Name for the new column containing original column values
    )
    return downsample(mrna_df_long)


def get_reactions_df(output_loaded: dict[str, Any], rxn_ids, select_rxns):
    rxns_mtx = np.stack(output_loaded["listeners__fba_results__base_reaction_fluxes"].values)

    rxns_idxs = [rxn_ids.index(rxn) for rxn in select_rxns]

    rxn_trajs = [rxns_mtx[:, rxn_idx] for rxn_idx in rxns_idxs]

    plot_rxns_dict = {key: val for (key, val) in zip(select_rxns, rxn_trajs)}

    plot_rxns_dict["time"] = output_loaded["time"]

    plot_rxns_df = pd.DataFrame(plot_rxns_dict)

    rxns_df_long = plot_rxns_df.melt(
        id_vars=["time"],  # Columns to keep as identifier variables
        var_name="reaction_id",  # Name for the new column containing original column headers
        value_name="flux",  # Name for the new column containing original column values
    )

    return downsample(rxns_df_long)


def get_sim_data(sim_data_path):
    return LoadSimData(sim_data_path).sim_data


def get_bulk_ids(sim_data_path):
    sim_data = LoadSimData(sim_data_path).sim_data
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"].tolist()
    return bulk_ids


def get_rxn_ids(sim_data_path):
    sim_data = LoadSimData(sim_data_path).sim_data
    rxn_ids = sim_data.process.metabolism.base_reaction_ids
    return rxn_ids


def get_ids(sim_data_path, sim_data):
    bulk_ids = get_bulk_ids(sim_data_path)
    bulk_ids_biocyc = [bulk_id[:-3] for bulk_id in bulk_ids]
    bulk_names_unique = list(np.unique(bulk_ids_biocyc))
    bulk_common_names = get_common_names(bulk_names_unique, sim_data)
    rxn_ids = get_rxn_ids(sim_data_path)
    cistron_data = sim_data.process.transcription.cistron_data
    mrna_cistron_ids = cistron_data["id"][cistron_data["is_mRNA"]].tolist()
    mrna_cistron_names = [sim_data.common_names.get_common_name(cistron_id) for cistron_id in mrna_cistron_ids]
    return (
        bulk_ids,
        bulk_ids_biocyc,
        bulk_names_unique,
        bulk_common_names,
        rxn_ids,
        cistron_data,
        mrna_cistron_ids,
        mrna_cistron_names,
    )


def get_common_names(bulk_names, sim_data):
    bulk_common_names = [sim_data.common_names.get_common_name(name) for name in bulk_names]

    duplicates = []

    for item in bulk_common_names:
        if bulk_common_names.count(item) > 1 and item not in duplicates:
            duplicates.append(item)

    for dup in duplicates:
        sp_idxs = [index for index, item in enumerate(bulk_common_names) if item == dup]

        for sp_idx in sp_idxs:
            bulk_rename = str(bulk_common_names[sp_idx]) + f"[{bulk_names[sp_idx]}]"
            bulk_common_names[sp_idx] = bulk_rename

    return bulk_common_names


def load_outputs(sql: str) -> pd.DataFrame:
    outputs_df = duckdb.sql(sql).df()
    outputs_df = outputs_df.groupby("time", as_index=False).sum()

    return outputs_df


def downsample(df_long):
    tp_all = np.unique(df_long["time"]).astype(int)
    ds_ratio = int(np.ceil(np.shape(df_long)[0] / 20000))
    tp_ds = list(itertools.islice(tp_all, 0, max(tp_all), ds_ratio))
    df_ds = df_long[np.isin(df_long["time"], tp_ds)]

    return df_ds


def get_filtered_query(output_dir, experiment_id, db_filter):
    pq_columns = [
        "bulk",
        "listeners__fba_results__base_reaction_fluxes",
        "listeners__rna_counts__full_mRNA_cistron_counts",
    ]

    history_sql_base, _, _ = dataset_sql(output_dir, experiment_ids=[experiment_id])
    return f"SELECT {','.join(pq_columns)},time FROM ({history_sql_base}) WHERE {db_filter} ORDER BY time"


class MoleculeIdType(StrEnum):
    COMMON = "common name"
    BULK = "bulk id"


def get_bulk_sp_traj(
    sp_input, bulk_mtx, molecule_id_type: MoleculeIdType, bulk_names_unique, bulk_common_names, bulk_ids_biocyc
):
    if molecule_id_type == "common name":
        sp_name = bulk_names_unique[bulk_common_names.index(sp_input)]

    elif molecule_id_type.value == "bulk id":
        sp_name = sp_input

    sp_idxs = [index for index, item in enumerate(bulk_ids_biocyc) if item == sp_name]

    bulk_sp_traj = np.sum(bulk_mtx[:, sp_idxs], 1)

    return bulk_sp_traj


def get_sp_trajs(
    bulk_mtx, bulk_sp_plot, molecule_id_type: MoleculeIdType, bulk_names_unique, bulk_common_names, bulk_ids_biocyc
):
    return [
        get_bulk_sp_traj(bulk_id, bulk_mtx, molecule_id_type, bulk_names_unique, bulk_common_names, bulk_ids_biocyc)
        for bulk_id in bulk_sp_plot
    ]


def get_bulk_mtx(output_loaded):
    return np.stack(output_loaded["bulk"].values)


def get_plot_df(output_loaded, bulk_sp_plot, sp_trajs):
    plot_dict = {key: val for (key, val) in zip(bulk_sp_plot, sp_trajs)}

    plot_dict["time"] = output_loaded["time"]

    return pd.DataFrame(plot_dict)
    # return pl.DataFrame(plot_dict)


def get_output_loaded(history_sql_filtered):
    return load_outputs(history_sql_filtered)


def get_variants(exp_id, outdir):
    try:
        vars_ls = os.listdir(
            os.path.join(
                outdir,
                exp_id,
                "history",
                f"experiment_id={exp_id}",
            )
        )

        variant_folders = [folder for folder in vars_ls if not folder.startswith(".")]

        variants = [var.split("variant=")[1] for var in variant_folders]

    except (FileNotFoundError, TypeError):
        variants = ["N/A"]

    return variants


def get_seeds(exp_id, var_id, outdir):
    try:
        seeds_ls = os.listdir(
            os.path.join(
                outdir,
                exp_id,
                "history",
                f"experiment_id={exp_id}",
                f"variant={var_id}",
            )
        )
        seed_folders = [folder for folder in seeds_ls if not folder.startswith(".")]

        seeds = [seed.split("lineage_seed=")[1] for seed in seed_folders]
    except (FileNotFoundError, TypeError):
        seeds = ["N/A"]

    return seeds


def get_gens(exp_id, var_id, seed_id, outdir):
    try:
        gens_ls = os.listdir(
            os.path.join(
                outdir,
                exp_id,
                "history",
                f"experiment_id={exp_id}",
                f"variant={var_id}",
                f"lineage_seed={seed_id}",
            )
        )

        gen_folders = [folder for folder in gens_ls if not folder.startswith(".")]

        gens = [gen.split("generation=")[1] for gen in gen_folders]
    except (FileNotFoundError, TypeError):
        gens = ["N/A"]

    return gens


def get_agents(exp_id, var_id, seed_id, gen_id, outdir):
    try:
        agents_ls = os.listdir(
            os.path.join(
                outdir,
                exp_id,
                "history",
                f"experiment_id={exp_id}",
                f"variant={var_id}",
                f"lineage_seed={seed_id}",
                f"generation={gen_id}",
            )
        )

        agent_folders = [folder for folder in agents_ls if not folder.startswith(".")]
        agents = [agent.split("agent_id=")[1] for agent in agent_folders]
    except (FileNotFoundError, TypeError):
        agents = ["N/A"]

    return agents


SelectedPartition = dict[str, int | str]


def partitions_dict(analysis_type, exp_select, variant_select, seed_select, gen_select, agent_select) -> dict[str, Any]:
    partitions_req = PARTITION_GROUPS[analysis_type]
    partitions_all = read_partitions(exp_select, variant_select, seed_select, gen_select, agent_select)

    partitions_dict = {}
    for partition in partitions_req:
        partitions_dict[partition] = partitions_all[partition]
    partitions_dict["experiment_id"] = f"'{partitions_dict['experiment_id']}'"
    return partitions_dict


def get_db_filter(partitions_dict) -> LiteralString:
    db_filter_list = []
    for key, value in partitions_dict.items():
        db_filter_list.append(str(key) + "=" + str(value))
    db_filter = " AND ".join(db_filter_list)

    return db_filter


def read_partitions(
    exp_select: str, variant_select: int, seed_select: int, gen_select: int, agent_select: str
) -> SelectedPartition:
    partitions_selected = {
        "experiment_id": exp_select,
        "variant": variant_select,
        "lineage_seed": seed_select,
        "generation": gen_select,
        "agent_id": agent_select,
    }
    return partitions_selected
