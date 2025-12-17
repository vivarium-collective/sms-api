import json
import logging
import random
import subprocess
import tempfile
import textwrap
import uuid
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from sms_api.analysis.models import (
    AnalysisConfig,
    AnalysisDomain,
    AnalysisModuleConfig,
    PtoolsAnalysisConfig,
    TsvOutputFile,
)
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import timestamp
from sms_api.config import Settings
from sms_api.simulation.database_service import DatabaseService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AnalysisServiceLocal:
    env: Settings
    db_service: DatabaseService

    def __init__(self, env: Settings, db_service: DatabaseService) -> None:
        self.env = env
        self.db_service = db_service

    async def run_analysis(
        self,
        expid: str,
        analysis_name: str,
        analysis_config: AnalysisConfig,
        requested: dict[str, list[AnalysisModuleConfig | PtoolsAnalysisConfig]],
    ) -> Sequence[TsvOutputFile]:
        # exec analysis
        ret = self.execute_analysis(expid=expid, name=analysis_name, config=analysis_config)

        # store in db
        job_id = random.randint(1111, 221111)
        job_name = analysis_name + f"-{str(uuid.uuid4())[:4]}"
        record = await self.insert_analysis(
            analysis_name=analysis_name, job_id=job_id, config=analysis_config, job_name=job_name
        )

        # get available
        analysis_dir = Path(analysis_config.analysis_options.outdir)
        available = self.get_available_output_paths(analysis_dirpath=analysis_dir)

        # download available
        return self.download_available(
            available_paths=available, requested=requested, analysis_cache=analysis_dir, logger=logger
        )

    def execute_analysis(self, expid: str, name: str, config: AnalysisConfig) -> int:
        env = self.env
        workspace_dir = env.vecoli_config_dir.parent.parent
        simulation_outdir = workspace_dir / ".results_cache"
        exp_outdir = simulation_outdir / expid  # env.simulation_outdir / args.expid
        variant_data_dir = exp_outdir / "variant_sim_data"
        validation_data_path = exp_outdir / "parca" / "kb" / "validationData.cPickle"
        config_name = "API_TEST"
        analysis_outdir = Path(env.cache_dir) / name
        tmpdir = tempfile.TemporaryDirectory()
        conf_path = str(Path(tmpdir.name) / "tmp.json")
        with open(conf_path, "w") as f:
            json.dump(config.model_dump(), f, indent=3)
        # (env.vecoli_config_dir / config_name)!s
        cmd = textwrap.dedent(f""" \
            rm -rf {analysis_outdir!s};
            mkdir -p {analysis_outdir!s};

            cd {env.vecoli_config_dir.parent!s};
            uv run --env-file .env runscripts/analysis.py \\
                --config {conf_path} \\
                --variant_data_dir {variant_data_dir!s} \\
                --validation_data_path {validation_data_path!s} \\
                --outdir {analysis_outdir!s} \\
                --experiment_id {expid}
        """)

        ret = self._execute_command(cmd)
        # config = self._get_config(analysis_outdir=analysis_outdir, simulation_outdir=simulation_outdir)
        tmpdir.cleanup()
        return ret

    def _get_config(self, analysis_outdir: Path, simulation_outdir: Path) -> AnalysisConfig:
        with open(str(analysis_outdir / "metadata.json")) as f:
            analysis_options = json.load(f)
        config = {"emitter_arg": {"out_dir": str(simulation_outdir)}, "analysis_options": analysis_options}
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "_.json"
            with open(str(fp), "w") as f:
                json.dump(config, f, indent=3)
            return AnalysisConfig.from_file(fp=fp)

    async def insert_analysis(self, analysis_name: str, config: AnalysisConfig, job_name: str, job_id: int):
        # insert new analysis
        return await self.db_service.insert_analysis(
            name=analysis_name,
            config=config,
            last_updated=timestamp(),
            job_name=job_name,
            job_id=job_id,
        )

    @classmethod
    def get_available_output_paths(cls, analysis_dirpath: Path) -> list[Path]:
        """This should search locally, so env.analysis_outdir should be {REPO_ROOT}/.results_cache/{analysis_name}"""
        return [p for p in analysis_dirpath.rglob("*") if p.is_file()]

    @classmethod
    def download_available(
        cls,
        available_paths: list[Path],
        requested: dict[str, list[AnalysisModuleConfig | PtoolsAnalysisConfig]],
        analysis_cache: Path,
        logger: logging.Logger,
    ) -> list[TsvOutputFile]:
        results: list[TsvOutputFile] = []
        if len(available_paths):
            # download requested available to cache and generate dto outputs
            for domain, configs in requested.items():
                for config in configs:
                    requested_filename = f"{config.name}_{AnalysisDomain[domain.upper()]}.txt"
                    relevant_files = cls._find_relevant_files(requested_filename, available_paths)
                    for remote_path in relevant_files:
                        # TODO: better save to cache
                        local = analysis_cache / requested_filename
                        verification = cls._verify_result(local, 5)
                        if not verification:
                            logger.info("WARNING: resulting num cols/tps do not match requested.")
                        file_content = local.read_text()
                        output = TsvOutputFile(filename=requested_filename, content=file_content)
                        results.append(output)
        return results

    @classmethod
    def _find_relevant_files(cls, requested_filename: str, available_paths: list[Path]) -> list[HPCFilePath]:
        return [fp for fp in filter(lambda fpath: requested_filename in str(fpath), available_paths)]

    @classmethod
    def _verify_result(cls, local_result_path: Path, expected_n_tp: int) -> bool:
        tsv_data = pd.read_csv(local_result_path, sep="\t")
        actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
        return len(actual_cols) == expected_n_tp

    @classmethod
    def _execute_command(cls, cmd: str) -> int:
        process = subprocess.Popen(
            cmd,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if process.stdout:
            for line in process.stdout:
                logger.info(line.rstrip())
        return process.wait()
