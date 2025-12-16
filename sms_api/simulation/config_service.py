import json
import logging
import os
import typing

from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings

logger = logging.getLogger(__file__)


DEFAULT_CONFIG_FILENAME = "default.json"
PARCA_LABEL_MAPPING = {
    "cpus": "Number of CPUs",
    "outdir": "Output directory",
    "operons": "Operons",
    "ribosome_fitting": "Ribosome fitting",
    "rnapoly_fitting": "RNAP fitting",
    "remove_rrna_operons": "Remove rRNA operons",
    "remove_rrff": "Remove rrfF",
    "stable_rrna": "Stable rRNA",
    "gene_deletions": "Gene deletions",
    "new_genes": "New gene options",
    "debug_parca": "Debug",
    "load_intermediate": "Load intermediates",
    "save_intermediates": "Save intermediates",
    "intermediates_directory": "",
    "variable_elongation_transcription": "Variable elongation (transcription)",
    "variable_elongation_translation": "Variable elongation (translation)",
}
PARCA_OPTIONS_EXPOSED = [
    "cpus",
    "new_genes",
    "operons",
    "ribosome_fitting",
    "rnapoly_fitting",
    "remove_rrna_operons",
    "remove_rrff",
    "stable_rrna",
    "variable_elongation_transcription",
    "variable_elongation_translation",
]


class SimulationConfigJSON(dict[str, typing.Any]):
    pass


def check_dir(func: typing.Callable[..., HPCFilePath]) -> typing.Callable[..., HPCFilePath]:
    def wrapper(self: "ConfigServiceHpc") -> HPCFilePath:
        dirpath: HPCFilePath = func(self)
        if not dirpath.remote_path.exists():
            logger.info(f"Nothing exists at {dirpath!s}")
        return dirpath

    return wrapper


class ConfigServiceHpc:
    env: Settings

    def __init__(self, env: Settings) -> None:
        self.env = env

    def vecoli_root_dir(self) -> HPCFilePath:
        """Should return ``wd_root``"""
        rootdir = self.env.vecoli_config_dir.parent
        return rootdir

    @check_dir
    def config_dir(self) -> HPCFilePath:
        conf_dir = self.vecoli_root_dir() / "configs"
        return conf_dir

    def default_config(self) -> SimulationConfigJSON:
        fp = self.config_dir() / DEFAULT_CONFIG_FILENAME
        return SimulationConfigJSON(json.loads(fp.remote_path.read_text()))

    @check_dir
    def new_genes_dir(self) -> HPCFilePath:
        genes_dir = self.vecoli_root_dir() / "reconstruction" / "ecoli" / "flat" / "new_gene_data"
        return genes_dir

    @check_dir
    def variants_dir(self) -> HPCFilePath:
        return self.vecoli_root_dir() / "ecoli" / "variants"

    def list_variants(self) -> list[str]:
        variant_files = os.listdir(str(self.variants_dir()))
        variant_files.remove("__init__.py")
        variant_files.remove("__pycache__")
        variant_files = [file.replace(".py", "") for file in variant_files]
        return variant_files
