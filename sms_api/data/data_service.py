import itertools
import pickle
from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import duckdb  # type: ignore[import-untyped]
import numpy as np
import pandas as pd
from ecoli.library.parquet_emitter import (  # type: ignore[import-untyped]
    create_duckdb_conn,
    dataset_sql,
    ndlist_to_ndarray,
    read_stacked_columns,
)
from ecoli.library.sim_data import LoadSimData  # type: ignore[import-untyped]
from reconstruction.ecoli.simulation_data import SimulationDataEcoli  # type: ignore[import-untyped]
from validation.ecoli.validation_data import ValidationDataEcoli  # type: ignore[import-untyped]

from sms_api.common.storage.file_paths import HPCFilePath
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


class AnalysisType(StrEnum):
    MULTIVARIANT = "multivariant"
    MULTISEED = "multiseed"
    MULTIGENERATION = "multigeneration"
    SINGLE = "single"


@dataclass
class Labels:
    bulk_ids: list[str]
    bulk_ids_biocyc: list[str]
    bulk_names_unique: list[str]
    bulk_common_names: list[str]
    rxn_ids: list[str]
    mrna_cistron_ids: list[str]
    mrna_gene_ids: list[str]
    mrna_cistron_names: list[str]
    monomer_ids: list[str]
    monomer_names: list[str]


class SimulationDataService(ABC):
    wd_root: HPCFilePath
    outputs_dir: HPCFilePath
    sim_data: SimulationDataEcoli
    validation_data: ValidationDataEcoli
    labels: Labels
    output_loaded: pd.DataFrame

    def __init__(self, env: Settings):
        """
        NOTE: ``wd_root`` is essentially ~/workspace
        """
        self.wd_root = HPCFilePath(remote_path=Path(env.slurm_base_path.remote_path / "workspace"))
        self.outputs_dir = env.simulation_outdir
        kb_dir = self.wd_root / "parameters" / "registry" / "default"
        self.sim_data = LoadSimData(str(kb_dir / "simData.cPickle")).sim_data
        with open(str(kb_dir / "validationData.cPickle"), "rb") as f:
            self.validation_data = pickle.load(f)  # noqa: S301
        assert isinstance(self.validation_data, ValidationDataEcoli)
        self.labels = self._get_labels()
        self.conn = create_duckdb_conn(str(env.simulation_outdir.remote_path), False, 1)

    @classmethod
    def downsample(cls, df_long: pd.DataFrame) -> pd.DataFrame:
        tp_all = np.unique(df_long["time"]).astype(int)
        ds_ratio = int(np.ceil(np.shape(df_long)[0] / 20000))
        tp_ds = list(itertools.islice(tp_all, 0, max(tp_all), ds_ratio))
        df_ds = df_long[np.isin(df_long["time"], tp_ds)]
        return df_ds

    def get_monomer_counts(
        self, exp_select: str, analysis_type: AnalysisType, partitions_all: dict[str, str | int]
    ) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        history_sql_base, _, _ = self._get_sql_base(exp_select)
        db_filter = self._get_db_filter(analysis_type, partitions_all)
        history_sql_subquery = f"SELECT * FROM ({history_sql_base}) WHERE {db_filter}"
        subquery = read_stacked_columns(history_sql_subquery, ["listeners__monomer_counts"], order_results=False)
        sql_monomer_validation = f"""
                WITH unnested_counts AS (
                    SELECT unnest(listeners__monomer_counts) AS counts,
                        generate_subscripts(listeners__monomer_counts, 1) AS idx,
                        experiment_id, variant, lineage_seed, generation, agent_id
                    FROM ({subquery})
                ),
                avg_counts AS (
                    SELECT avg(counts) AS avgCounts,
                        experiment_id, variant, lineage_seed,
                        generation, agent_id, idx
                    FROM unnested_counts
                    GROUP BY experiment_id, variant, lineage_seed,
                        generation, agent_id, idx
                )
                SELECT list(avgCounts ORDER BY idx) AS avgCounts
                FROM avg_counts
                GROUP BY experiment_id, variant, lineage_seed, generation, agent_id
                """
        monomer_counts = self.conn.sql(sql_monomer_validation).pl()
        return ndlist_to_ndarray(monomer_counts["avgCounts"])

    def get_monomers_df(
        self, output_loaded: pd.DataFrame, monomer_label_type: str, monomer_select_plot: list[str]
    ) -> pd.DataFrame:
        def get_monomer_traj(
            monomer_label_type: str, monomer_input: str, monomer_mtx: np.ndarray[tuple[Any, ...], np.dtype[Any]]
        ):
            if monomer_label_type == "common name":
                monomer_name = monomer_input
            if monomer_label_type == "BioCyc ID":
                monomer_name = self.labels.monomer_names[self.labels.monomer_ids.index(monomer_input)]
            monomer_idx = self.labels.monomer_names.index(monomer_name)
            monomer_traj = monomer_mtx[:, monomer_idx]
            return monomer_traj

        monomer_mtx = np.stack(output_loaded["listeners__monomer_counts"])
        monomer_trajs = [
            get_monomer_traj(monomer_label_type, monomer_id, monomer_mtx) for monomer_id in monomer_select_plot
        ]
        monomer_plot_dict = {key: val for (key, val) in zip(monomer_select_plot, monomer_trajs)}
        monomer_plot_dict["time"] = output_loaded["time"]
        monomer_plot_df = pd.DataFrame(monomer_plot_dict)
        monomer_df_long = monomer_plot_df.melt(
            id_vars=["time"],
            var_name="protein names",
            value_name="counts",
        )
        return SimulationDataService.downsample(monomer_df_long)

    def get_rxns_df(self, output_loaded: pd.DataFrame, select_rxns: list[str]) -> pd.DataFrame:
        rxns_mtx = np.stack(output_loaded["listeners__fba_results__base_reaction_fluxes"].values)
        rxns_idxs = [self.labels.rxn_ids.index(rxn) for rxn in select_rxns]
        rxn_trajs = [rxns_mtx[:, rxn_idx] for rxn_idx in rxns_idxs]
        plot_rxns_dict = {key: val for (key, val) in zip(select_rxns, rxn_trajs)}
        plot_rxns_dict["time"] = output_loaded["time"]
        plot_rxns_df = pd.DataFrame(plot_rxns_dict)
        rxns_df_long = plot_rxns_df.melt(
            id_vars=["time"],  # Columns to keep as identifier variables
            var_name="reaction_id",  # Name for the new column containing original column headers
            value_name="flux",  # Name for the new column containing original column values
        )
        return SimulationDataService.downsample(rxns_df_long)

    def get_mrna_df(
        self, output_loaded: pd.DataFrame, rna_label_type: str, mrna_select_plot: list[str]
    ) -> pd.DataFrame:
        def get_mrna_traj(rna_label_type: str, mrna_input, mrna_mtx):
            mrna_cistron_names = self.labels.mrna_cistron_names
            if rna_label_type == "gene name":
                mrna_name = mrna_input
            elif rna_label_type == "BioCyc ID":
                mrna_name = mrna_cistron_names[self.labels.mrna_gene_ids.index(mrna_input)]
            mrna_idx = mrna_cistron_names.index(mrna_name)
            mrna_traj = mrna_mtx[:, mrna_idx]
            return mrna_traj

        mrna_mtx = np.stack(output_loaded["listeners__rna_counts__full_mRNA_cistron_counts"])
        mrna_trajs = [get_mrna_traj(rna_label_type, mrna_id, mrna_mtx) for mrna_id in mrna_select_plot]
        # mrna_trajs = [mrna_mtx[:, mrna_idx] for mrna_idx in mrna_idxs]
        mrna_plot_dict = {key: val for (key, val) in zip(mrna_select_plot, mrna_trajs)}
        mrna_plot_dict["time"] = output_loaded["time"]
        mrna_plot_df = pd.DataFrame(mrna_plot_dict)
        mrna_df_long = mrna_plot_df.melt(
            id_vars=["time"],  # Columns to keep as identifier variables
            var_name="Genes",  # Name for the new column containing original column headers
            value_name="counts",  # Name for the new column containing original column values
        )
        return SimulationDataService.downsample(mrna_df_long)

    def get_bulk_df(self, output_loaded: pd.DataFrame, molecule_id_type: str, bulk_sp_plot: list[str]) -> pd.DataFrame:
        sp_trajs: list[np.ndarray[tuple[Any, ...], np.dtype[Any]]] = self._get_sp_trajs(
            output_loaded, molecule_id_type, bulk_sp_plot
        )
        plot_dict = {key: val for (key, val) in zip(bulk_sp_plot, sp_trajs)}
        plot_dict["time"] = output_loaded["time"]  # type: ignore[assignment]

        plot_df = pd.DataFrame(plot_dict)
        df_long = plot_df.melt(
            id_vars=["time"],  # Columns to keep as identifier variables
            var_name="Compounds",  # Name for the new column containing original column headers
            value_name="counts",  # Name for the new column containing original column values
        )
        return SimulationDataService.downsample(df_long)

    def get_outputs(
        self, analysis_type: AnalysisType, partitions_all: dict[str, str | int], exp_select: str
    ) -> pd.DataFrame:
        # dbf_dict = self.partitions_dict(analysis_type, partitions_all)
        # db_filter = self.get_db_filter(dbf_dict)
        db_filter = self._get_db_filter(analysis_type, partitions_all)
        pq_columns = [
            "bulk",
            "listeners__fba_results__base_reaction_fluxes",
            "listeners__rna_counts__full_mRNA_cistron_counts",
            "listeners__monomer_counts",
        ]

        history_sql_base, _, _ = self._get_sql_base(exp_select)
        history_sql_filtered = (
            f"SELECT {','.join(pq_columns)},time FROM ({history_sql_base}) WHERE {db_filter} ORDER BY time"
        )
        outputs_df: pd.DataFrame = duckdb.sql(history_sql_filtered).df()
        return outputs_df.groupby("time", as_index=False).sum()

    def _get_sql_base(self, exp_select: str) -> tuple[str, str, str]:
        history, conf, success = dataset_sql(str(self.outputs_dir.remote_path), experiment_ids=[exp_select])
        return history, conf, success

    def _get_db_filter(self, analysis_type: AnalysisType, partitions_all: dict[str, str | int]) -> str:
        def partitions_dict(analysis_type: AnalysisType, partitions_all: dict[str, str | int]) -> dict[str, Any]:
            partitions_req = PARTITION_GROUPS[analysis_type]
            partitions_dict = {}
            for partition in partitions_req:
                partitions_dict[partition] = partitions_all[partition]
            partitions_dict["experiment_id"] = f"'{partitions_dict['experiment_id']}'"
            return partitions_dict

        def db_filter(partitions_dict: dict[str, Any]) -> str:
            db_filter_list = []
            for key, value in partitions_dict.items():
                db_filter_list.append(str(key) + "=" + str(value))
            db_filter = " AND ".join(db_filter_list)
            return db_filter

        dbf_dict = partitions_dict(analysis_type, partitions_all)
        return db_filter(dbf_dict)

    def _get_sp_trajs(
        self, output_loaded: pd.DataFrame, molecule_id_type: str, bulk_sp_plot: list[str]
    ) -> list[np.ndarray[tuple[Any, ...], np.dtype[Any]]]:
        def get_bulk_sp_traj(
            molecule_id_type: str, sp_input: str, bulk_mtx: np.ndarray[tuple[Any, ...], np.dtype[Any]]
        ) -> Any:
            if molecule_id_type == "Common name":
                sp_name = self.labels.bulk_names_unique[self.labels.bulk_common_names.index(sp_input)]
            elif molecule_id_type == "BioCyc ID":
                sp_name = sp_input
            sp_idxs = [index for index, item in enumerate(self.labels.bulk_ids_biocyc) if item == sp_name]
            bulk_sp_traj = np.sum(bulk_mtx[:, sp_idxs], 1)
            return bulk_sp_traj

        bulk_mtx = np.stack(output_loaded["bulk"].values)
        sp_trajs = [get_bulk_sp_traj(molecule_id_type, bulk_id, bulk_mtx) for bulk_id in bulk_sp_plot]
        return sp_trajs

    def get_common_names(self, names: list[str], sim_data: SimulationDataEcoli | None = None) -> list[str]:
        if sim_data is None:
            sim_data = self.sim_data
        bulk_names = names
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

    def _get_labels(self) -> Labels:
        def get_common_names(bulk_names: list[str], sim_data: SimulationDataEcoli) -> list[str]:
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

        def get_bulk_ids() -> list[str]:
            bulk_ids: list[str] = self.sim_data.internal_state.bulk_molecules.bulk_data["id"].tolist()
            return bulk_ids

        def get_rxn_ids() -> list[str]:
            rxn_ids: list[str] = self.sim_data.process.metabolism.base_reaction_ids
            return rxn_ids

        sim_data = self.sim_data
        bulk_ids = get_bulk_ids()
        bulk_ids_biocyc = [bulk_id[:-3] for bulk_id in bulk_ids]
        bulk_names_unique = list(np.unique(bulk_ids_biocyc))
        bulk_common_names = get_common_names(bulk_names_unique, sim_data)
        rxn_ids = get_rxn_ids()
        cistron_data = sim_data.process.transcription.cistron_data
        mrna_cistron_ids = cistron_data["id"][cistron_data["is_mRNA"]].tolist()
        mrna_gene_ids = [cistron_id.strip("_RNA") for cistron_id in mrna_cistron_ids]
        mrna_cistron_names = [sim_data.common_names.get_common_name(cistron_id) for cistron_id in mrna_cistron_ids]
        monomer_ids = sim_data.process.translation.monomer_data["id"].tolist()
        monomer_ids = [id[:-3] for id in monomer_ids]
        monomer_names = get_common_names(monomer_ids, sim_data)
        return Labels(
            bulk_ids=bulk_ids,
            bulk_common_names=bulk_common_names,
            bulk_ids_biocyc=bulk_ids_biocyc,
            bulk_names_unique=bulk_names_unique,
            rxn_ids=rxn_ids,
            mrna_cistron_ids=mrna_cistron_ids,
            mrna_gene_ids=mrna_gene_ids,
            mrna_cistron_names=mrna_cistron_names,
            monomer_ids=monomer_ids,
            monomer_names=monomer_names,
        )
