import json
import os
import pathlib
from dataclasses import asdict, dataclass
from typing import Any

import numpy
import numpy as np
import orjson
from pydantic import BaseModel, Field

from sms_api.common.utils import unique_id
from sms_api.config import get_settings

ENV = get_settings()
MAX_ANALYSIS_CPUS = 3


### -- analyses -- ###


class OutputFile(BaseModel):
    name: str
    content: str


class AnalysisConfigOptions(BaseModel):
    # TODO: infer variant data dir, validation datapath from experiment id
    experiment_id: list[str]
    variant_data_dir: list[str] | None = None
    validation_data_path: list[str] | None = None
    outdir: str | None = None
    cpus: int = 3
    single: dict[str, Any] = {}
    multidaughter: dict[str, Any] = {}
    multigeneration: dict[str, dict[str, Any]] = {
        "replication": {},
        "ribosome_components": {},
        "ribosome_crowding": {},
        "ribosome_production": {},
        "ribosome_usage": {},
        "rna_decay_03_high": {},
    }
    multiseed: dict[str, dict[str, Any]] = {
        "protein_counts_validation": {},
        "ribosome_spacing": {},
        "subgenerational_expression_table": {},
    }
    multivariant: dict[str, dict[str, Any]] = {
        "average_monomer_counts": {},
        "cell_mass": {},
        "doubling_time_hist": {"skip_n_gens": 1},
        "doubling_time_line": {},
    }
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
    def from_request(cls, request: "ExperimentAnalysisRequest") -> "AnalysisConfig":
        output_dir = pathlib.Path(f"/home/FCAM/svc_vivarium/workspace/api_outputs/{request.experiment_id}")
        options = AnalysisConfigOptions(
            experiment_id=[request.experiment_id],
            variant_data_dir=[str(output_dir / "variant_sim_data")],
            validation_data_path=[str(output_dir / "parca/kb/validationData.cPickle")],
            outdir=str(output_dir.parent / request.analysis_name),
            single=request.single,
            multidaughter=request.multidaughter,
            multigeneration=request.multigeneration,
            multiexperiment=request.multiexperiment,
            multivariant=request.multivariant,
            multiseed=request.multiseed,
        )
        emitter_arg = {"out_dir": str(output_dir.parent)}
        return cls(analysis_options=options, emitter_arg=emitter_arg)


class ExperimentAnalysisRequest(BaseModel):
    experiment_id: str
    analysis_name: str = Field(default=f"analysis_{unique_id()!s}")
    single: dict[str, Any] = {}
    multidaughter: dict[str, Any] = {}
    multigeneration: dict[str, dict[str, Any]] = {
        "replication": {},
        "ribosome_components": {},
        "ribosome_crowding": {},
        "ribosome_production": {},
        "ribosome_usage": {},
        "rna_decay_03_high": {},
    }
    multiseed: dict[str, dict[str, Any]] = {
        "protein_counts_validation": {},
        "ribosome_spacing": {},
        "subgenerational_expression_table": {},
    }
    multivariant: dict[str, dict[str, Any]] = {
        "average_monomer_counts": {},
        "cell_mass": {},
        "doubling_time_hist": {"skip_n_gens": 1},
        "doubling_time_line": {},
    }
    multiexperiment: dict[str, Any] = {}

    def to_config(self) -> AnalysisConfig:
        experiment_outdir = f"{ENV.simulation_outdir}/{self.experiment_id}"
        options = AnalysisConfigOptions(
            experiment_id=[self.experiment_id],
            variant_data_dir=[f"{experiment_outdir}/variant_sim_data"],
            validation_data_path=[f"{experiment_outdir}/parca/kb/validationData.cPickle"],
            outdir=f"{ENV.simulation_outdir}/{self.analysis_name}",
            cpus=MAX_ANALYSIS_CPUS,
            single=self.single,
            multidaughter=self.multidaughter,
            multigeneration=self.multigeneration,
            multiexperiment=self.multiexperiment,
            multivariant=self.multivariant,
            multiseed=self.multiseed,
        )
        emitter_arg = {"out_dir": ENV.simulation_outdir}
        return AnalysisConfig(analysis_options=options, emitter_arg=emitter_arg)


class ExperimentAnalysisDTO(BaseModel):
    database_id: int
    name: str
    config: AnalysisConfig
    last_updated: str
    job_name: str | None = None
    job_id: int | None = None


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
