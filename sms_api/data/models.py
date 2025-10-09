import json
import os
import pathlib
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Literal

import numpy
import numpy as np
import orjson
from pydantic import BaseModel, ConfigDict, Field

from sms_api.config import get_settings

ENV = get_settings()
MAX_ANALYSIS_CPUS = 3


### -- analyses -- ###


class TsvOutputFileRequest(BaseModel):
    # analysis_id: int
    filename: str
    variant: int = 0
    lineage_seed: int | None = None
    generation: int | None = None
    agent_id: str | None = None


class OutputFileMetadata(BaseModel):
    filename: str
    variant: int = 0
    lineage_seed: int | None = None
    generation: int | None = None
    agent_id: str | None = None
    content: str | None = None

    def model_post_init(self, *args: Any) -> None:
        trim_attributes(self, OutputFileMetadata)


class TsvOutputFile(OutputFileMetadata):
    pass


class OutputFile(BaseModel):
    name: str
    content: str


class AnalysisModuleConfig(BaseModel):
    name: str
    files: list[OutputFileMetadata] | None = None
    model_config = ConfigDict(extra="allow")

    def to_dict(self) -> dict[str, Any]:
        return {self.name: {}}


class PtoolsAnalysisConfig(BaseModel):
    """
    :param name: (str) Analysis module name (One of ["ptools_rxns", "ptools_rna", "ptools_proteins"])
    :param n_tp: (int) Number of timepoints/columns to use in the tsv
    :param files: (list[OutputFileMetadata]) Specification of files requested to be returned
        with the completion of the analysis.
    """

    name: Literal["ptools_rxns", "ptools_rna", "ptools_proteins"]
    n_tp: int = 8
    variant: int = 0
    generation: int | None = None
    lineage_seed: int | None = None
    agent_id: int | None = None
    files: list[OutputFileMetadata] | None = None

    def model_post_init(self, context: Any, /) -> None:
        for attrname in list(PtoolsAnalysisConfig.model_fields.keys()):
            if getattr(self, attrname, None) is None:
                delattr(self, attrname)

    def to_dict(self) -> dict[Literal["ptools_rxns", "ptools_rna", "ptools_proteins"], dict[str, int]]:
        return {self.name: {"n_tp": self.n_tp}}


class AnalysisConfigOptions(BaseModel):
    """Schema for analysis module configs:

    "single": {},
    "multidaughter": {},
    "multigeneration": {
      "replication": {},
      "ribosome_components": {},
      "ribosome_crowding": {},
      "ribosome_production": {},
      "ribosome_usage": {},
      "rna_decay_03_high": {},
      "ptools_rxns": {
        "n_tp": 8
      },
      "ptools_rna": {
        "n_tp": 8
      },
      "ptools_proteins": {
        "n_tp": 8
      }
    },
    "multiseed": {
      "protein_counts_validation": {},
      "ribosome_spacing": {},
      "subgenerational_expression_table":
      "ptools_rxns": {
        "n_tp": 8
      },
      "ptools_rna": {
        "n_tp": 8
      },
      "ptools_proteins": {
        "n_tp": 8
      }
    },
    "multivariant": {
      "average_monomer_counts": {},
      "cell_mass": {},
      "doubling_time_hist": {
        "skip_n_gens": 1
      },
      "doubling_time_line": {}
    },
    "multiexperiment": {}
    """

    experiment_id: list[str]
    variant_data_dir: list[str] | None = None
    validation_data_path: list[str] | None = None
    outdir: str | None = None
    cpus: int = 3
    single: dict[str, Any] = {}
    multidaughter: dict[str, Any] = {}
    multigeneration: dict[str, dict[str, Any]] = {}
    multiseed: dict[str, dict[str, Any]] = {}
    multivariant: dict[str, dict[str, Any]] = {}
    multiexperiment: dict[str, Any] = {}


class AnalysisConfig(BaseModel):
    analysis_options: AnalysisConfigOptions
    emitter_arg: dict[str, str] = Field(default={"out_dir": ""})

    @classmethod
    def from_file(cls, fp: pathlib.Path, config_id: str | None = None) -> "AnalysisConfig":
        filepath = fp
        with open(filepath) as f:
            conf = json.load(f)
        options = AnalysisConfigOptions(**conf["analysis_options"])
        return cls(analysis_options=options, emitter_arg=conf["emitter_arg"])

    @classmethod
    def from_request(cls, request: "ExperimentAnalysisRequest", analysis_name: str) -> "AnalysisConfig":
        output_dir = pathlib.Path(f"/home/FCAM/svc_vivarium/workspace/api_outputs/{request.experiment_id}")

        options = AnalysisConfigOptions(
            experiment_id=[request.experiment_id],
            variant_data_dir=[str(output_dir / "variant_sim_data")],
            validation_data_path=[str(output_dir / "parca/kb/validationData.cPickle")],
            outdir=str(output_dir.parent / analysis_name),
            single=dict_options(request.single),
            multidaughter=dict_options(request.multidaughter),
            multigeneration=dict_options(request.multigeneration),
            multiexperiment=dict_options(request.multiexperiment),
            multivariant=dict_options(request.multivariant),
            multiseed=dict_options(request.multiseed),
        )
        emitter_arg = {"out_dir": str(output_dir.parent)}
        return cls(analysis_options=options, emitter_arg=emitter_arg)


class ExperimentAnalysisRequest(BaseModel):
    experiment_id: str
    # analysis_name: str = Field(default=f"analysis_{unique_id()!s}")
    single: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None
    multidaughter: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None
    multigeneration: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None
    multiseed: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None
    multivariant: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None
    multiexperiment: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None = None

    def to_config(self, analysis_name: str) -> AnalysisConfig:
        experiment_outdir = f"{ENV.simulation_outdir}/{self.experiment_id}"
        options = AnalysisConfigOptions(
            experiment_id=[self.experiment_id],
            variant_data_dir=[f"{experiment_outdir}/variant_sim_data"],
            validation_data_path=[f"{experiment_outdir}/parca/kb/validationData.cPickle"],
            outdir=f"{ENV.simulation_outdir}/{analysis_name}",
            cpus=MAX_ANALYSIS_CPUS,
            single=dict_options(self.single),
            multidaughter=dict_options(self.multidaughter),
            multigeneration=dict_options(self.multigeneration),
            multiexperiment=dict_options(self.multiexperiment),
            multivariant=dict_options(self.multivariant),
            multiseed=dict_options(self.multiseed),
        )
        emitter_arg = {"out_dir": ENV.simulation_outdir}
        return AnalysisConfig(analysis_options=options, emitter_arg=emitter_arg)


class ExperimentAnalysisDTO(BaseModel):
    """Example schema:
    {
        "database_id": 1,
        "name": "ptools_analysis-sms_multigeneration_0-67ed3dbe116f78d9_1759364318634",
        "config": {
          "analysis_options": {
            "experiment_id": [
              "sms_multigeneration_0-67ed3dbe116f78d9_1759364318634"
            ],
            "variant_data_dir": [
              "/home/FCAM/svc_vivarium/workspace/api_outputs/sms_multigeneration_0-67ed3dbe116f78d9_1759364318634/variant_sim_data"
            ],
            "validation_data_path": [
              "/home/FCAM/svc_vivarium/workspace/api_outputs/sms_multigeneration_0-67ed3dbe116f78d9_1759364318634/parca/kb/validationData.cPickle"
            ],
            "outdir":
                "/home/FCAM/svc_vivarium/workspace/api_outputs/ptools_analysis-sms_multigeneration_0-67ed3dbe116f78d9_1759364318634",
            "cpus": 3,
            "single": {},
            "multidaughter": {},
            "multigeneration": {
              "ptools_rxns": {
                "n_tp": 8,
                "files": [
                  {
                     "filename": "ptools_rxns_multigen.txt",
                     "variant": 0,
                     "lineage_seed": 0
                  }
                ]
              },
              "ptools_rna": {
                "n_tp": 8,
                "files": [
                  {
                     "filename": "ptools_rna_multigen.txt",
                     "variant": 0,
                     "lineage_seed": 0
                  }
                ]
              },
              "ptools_proteins": {
                "n_tp": 8,
                "files": [
                  {
                     "filename": "ptools_proteins_multigen.txt",
                     "variant": 0,
                     "lineage_seed": 0
                  }
                ]
              }
            },
            "multiseed": {},
            "multivariant": {},
            "multiexperiment": {}
          },
          "emitter_arg": {
            "out_dir": "/home/FCAM/svc_vivarium/workspace/api_outputs"
          }
        },
        "last_updated": "2025-10-02 00:50:39.764349",
        "job_name": "sms-079c43c-ptools_analysis-sms_multigeneration_0-67ed3dbe116f78d9_1759364318634-e5qu7p",
        "job_id": 812320
      }
    """

    database_id: int
    name: str
    config: AnalysisConfig
    last_updated: str
    job_name: str | None = None
    job_id: int | None = None


class JobStatus(StrEnum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRun(BaseModel):
    id: int
    status: JobStatus


### -- biocyc -- ###


class BiocycComponentData(BaseModel):
    id: str
    orgid: str
    frameid: str
    detail: str
    parent: dict[str, dict[str, str]] = Field(default_factory=dict)


class BiocycCompound(BiocycComponentData):
    cml: dict[str, Any]
    cls: str | None = None
    # common_name: dict


class BiocycReaction(BiocycComponentData):
    ec_number: dict[str, Any]
    right: list[dict[str, Any]]
    enzymatic_reaction: dict[str, Any]
    left: list[dict[str, Any]]


class BiocycComponent(BaseModel):
    id: str  # loadedjson['obj_id']
    pgdb: dict[str, Any]  # ['data']['ptools-xml']['metadata']['PGDB']
    data: BiocycCompound | BiocycReaction  # ['data']['ptools-xml']['Compound'] FOR EXAMPLE


@dataclass
class BiocycData:
    obj_id: str
    org_id: str
    data: dict[str, Any]
    request: dict[str, Any]
    dest_dirpath: pathlib.Path | None = None

    @property
    def filepath(self) -> pathlib.Path:
        dest_fp = self.dest_dirpath or pathlib.Path("assets/biocyc")
        return dest_fp / f"{self.obj_id}.json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dto(self) -> BiocycComponent:
        data = self
        ptools_data = data.data["ptools-xml"]
        pgdb = ptools_data["metadata"]["PGDB"]
        data_key = next(
            iter([key for key in ptools_data if not key.startswith("@") and not key.startswith("metadata")])
        )
        raw_component = ptools_data[data_key]
        comp_data = {}
        for k, v in raw_component.items():
            if "common" in k or "subclass" in k or "synonym" in k:
                continue
            if "class" in k:
                k = "cls"
            if k.startswith("@"):
                k = k.replace("@", "").replace("-", "_")
            comp_data[k.lower()] = v
        data_type = BiocycCompound if "Compound" in data_key else BiocycReaction
        return BiocycComponent(id=data.obj_id, pgdb=pgdb, data=data_type(**comp_data))

    def export(self, fp: pathlib.Path | None = None) -> None:
        try:
            exp = self.to_dict()
            fp = fp or self.filepath
            with open(fp, "w") as f:
                json.dump(exp, f, indent=4)
            print(f"Successfully wrote: {fp}")
        except OSError:
            print(f"Could not write for {self.obj_id}")


@dataclass
class Credentials:
    username: str | None = None
    password: str | None = None
    config: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, str | None]:
        d = asdict(self)
        d.pop("config", None)
        return d


@dataclass
class BiocycCredentials(Credentials):
    def to_dict(self) -> dict[str, str | None]:
        return {"email": self.username, "password": self.password}

    @classmethod
    def from_env(cls, env_fp: pathlib.Path, config: dict[str, Any] | None = None) -> "BiocycCredentials":
        import dotenv

        dotenv.load_dotenv(env_fp)
        print("loading", env_fp)
        return cls(username=os.getenv("BIOCYC_EMAIL"), password=os.getenv("BIOCYC_PASSWORD"), config=config)


class SerializedArray:
    __slots__ = ("_value", "shape")

    def __init__(self, arr: numpy.ndarray) -> None:
        self._value = self.serialize(arr)

    def serialize(self, arr: numpy.ndarray) -> bytes:
        self.shape = arr.shape
        return orjson.dumps(numpy.ravel(arr, order="C").tolist())

    def deserialize(self) -> numpy.ndarray:
        arr: np.ndarray = np.array(orjson.loads(self._value))
        return arr.reshape(self.shape)

    @property
    def value(self) -> numpy.ndarray:
        return self.deserialize()

    @value.setter
    def value(self, value: np.ndarray) -> None:
        self._value = self.serialize(value)


def trim_attributes(instance: BaseModel, cls: type[BaseModel]) -> None:
    for attrname in list(cls.model_fields.keys()):
        if "analysis_type" not in attrname:
            attr = getattr(instance, attrname, None)
            if attr is None or attr == ["string"]:
                delattr(instance, attrname)
            if isinstance(attr, (list, dict)) and not len(attr):
                delattr(instance, attrname)


def dict_options(items: list[AnalysisModuleConfig | PtoolsAnalysisConfig] | None) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if items is not None:
        for item in items:
            options.update(item.to_dict())  # type: ignore[arg-type]
    return options
