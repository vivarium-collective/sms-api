import json
import os
import pathlib
import uuid
from collections.abc import Collection
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, override

import numpy
import numpy as np
import orjson
from pydantic import BaseModel, Field


class Base(BaseModel):
    pass


class BiocycComponentData(Base):
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


class BiocycComponent(Base):
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


@dataclass
class _BiocycData:
    obj_id: str
    org_id: str
    data: dict[str, Any]
    request: dict[str, Collection[str]]
    dest_dirpath: pathlib.Path | None = None

    @property
    def filepath(self) -> pathlib.Path:
        dest_fp = self.dest_dirpath or pathlib.Path("assets/biocyc")
        return dest_fp / f"{self.obj_id}.json"

    def to_dict(self) -> dict[str, str | dict[str, Any] | dict[str, str] | pathlib.Path | None]:
        return asdict(self)

    def export(self, fp: pathlib.Path | None = None) -> None:
        try:
            exp = self.to_dict()
            fp = fp or self.filepath
            with open(fp, "w") as f:
                json.dump(exp, f, indent=4)
            print(f"Successfully wrote: {fp}")
        except OSError:
            print(f"Could not write for {self.obj_id}")


class OutputDomain(StrEnum):
    ANALYSIS = "analysis"
    PARQUET = "history"
    STATE = "daughter_states"
    PARAMETERS = "parca"


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


class Configuration(BaseModel):
    @classmethod
    def from_file(cls, fp: pathlib.Path, config_id: str | None = None) -> "Configuration":
        filepath = fp
        with open(filepath) as f:
            conf = json.load(f)
        return cls(**conf)


class AnalysisRequest(BaseModel):
    experiment_id: str
    analysis_name: str = Field(default_factory=lambda: f"analysis_{uuid.uuid4()!s}")
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


class AnalysisConfigOptions(BaseModel):
    # TODO: infer variant data dir, validation datapath from experiment id
    experiment_id: list[str]
    variant_data_dir: list[str] | None = None
    validation_data_path: list[str] | None = None
    outdir: str | None = None
    cpus: int = 3
    single: dict[str, Any] = Field(default_factory=dict)
    multidaughter: dict[str, Any] = Field(default_factory=dict)
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


class AnalysisConfig(Configuration):
    analysis_options: AnalysisConfigOptions
    emitter_arg: dict[str, str] = Field(default={"out_dir": ""})

    @classmethod
    @override
    def from_file(cls, fp: pathlib.Path, config_id: str | None = None) -> "AnalysisConfig":
        filepath = fp
        with open(filepath) as f:
            conf = json.load(f)
        options = AnalysisConfigOptions(**conf["analysis_options"])
        return cls(analysis_options=options, emitter_arg=conf["emitter_arg"])

    @classmethod
    def from_request(cls, request: AnalysisRequest) -> "AnalysisConfig":
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


class ExperimentAnalysisDTO(BaseModel):
    database_id: int
    name: str
    config: AnalysisConfig
    last_updated: str


class AnalysisJob(BaseModel):
    id: int
    status: str = "WAITING"


class UploadConfirmation(BaseModel):
    filename: str
    home: str
    timestamp: str | None = None

    def model_post_init(self, context, /) -> None:
        if self.timestamp is not None:
            raise ValueError("You cannot edit this field!")
        self.timestamp = str(datetime.now())
