"""
Data model relating to SED2 (S.E.D.) specification
"""


from dataclasses import dataclass
from typing import *
from types import NoneType
from abc import abstractmethod, ABC

import requests
from pydantic import Field, create_model

from bsp.data_model.base import BaseModel, BaseClass as _BaseClass


@dataclass
class SimulationModelParameter(_BaseClass):
    """
        Attributes:
            name:`str`
            feature:`str`
            value:`Union[float, int, str]`
            scope:`str`
    """
    name: str
    value: Union[float, int, str]
    feature: str
    scope: str = None


# TODO: what could this specific name be? Are these changes etc, unique to Time Course / '2d' simulation?
@dataclass
class SpeciesChange(_BaseClass):  # <-- this is done like set_species('B', kwarg=) where the inner most keys are the kwargs
    species_name: str
    unit: Union[str, NoneType, SimulationModelParameter] = None
    initial_concentration: Optional[Union[float, SimulationModelParameter]] = None
    initial_particle_number: Optional[Union[float, NoneType, SimulationModelParameter]] = None
    initial_expression: Union[str, NoneType, SimulationModelParameter] = None
    expression: Union[str, NoneType, SimulationModelParameter] = None


@dataclass
class GlobalParameterChange(_BaseClass):  # <-- this is done with set_parameters(PARAM, kwarg=). where the inner most keys are the kwargs
    parameter_name: str
    initial_value: Union[float, NoneType] = None
    initial_expression: Union[str, NoneType] = None
    expression: Union[str, NoneType] = None
    status: Union[str, NoneType] = None
    param_type: Union[str, NoneType] = None  # ie: fixed, assignment, reactions, etc


@dataclass
class ReactionParameter(_BaseClass):
    parameter_name: str
    value: Union[float, int, str]


@dataclass
class ReactionChange(_BaseClass):
    """
        Attributes:
            reaction_name:`str`: name of the reaction you wish to change.
            parameter_changes:`List[ReactionParameter]`: list of parameters you want to change from
                `reaction_name`. Defaults to `[]`, which denotes no parameter changes.

    """
    reaction_name: str
    parameter_changes: List[ReactionParameter] = None
    reaction_scheme: Union[NoneType, str] = None


@dataclass
class TimeCourseModelChanges(_BaseClass):
    species_changes: List[SpeciesChange] = None
    global_parameter_changes: List[GlobalParameterChange] = None
    reaction_changes: List[ReactionChange] = None


@dataclass
class ModelSource(_BaseClass):
    value: str

    @abstractmethod
    def validate_source(self):
        pass


@dataclass
class BiomodelID(ModelSource):
    def __init__(self, value):
        super().__init__(value)
        self.validate_source()

    def validate_source(self):
        if 'BIO' not in self.value:
            raise AttributeError('You must pass a valid biomodel id.')


@dataclass
class ModelFilepath(ModelSource):
    def __init__(self, value):
        super().__init__(value)
        self.validate_source()

    def validate_source(self):
        if '/' not in self.value:
            raise AttributeError('You must pass a valid model path.')


@dataclass
class ModelChange(_BaseClass):
    name: str
    scope: str
    value: Dict


@dataclass
class ModelChanges(_BaseClass):
    species_changes: List[ModelChange] = None
    param_changes: List[ModelChange] = None
    reaction_changes: List[ModelChange] = None


class ModelUnits:
    def __init__(self, **units_config):
        for k, v in units_config:
            self.__setattr__(k, v)


@dataclass
class SedModel(_BaseClass):
    """The data model declaration for process configuration schemas that support SED.

        Attributes:
            model_id: `str`
            model_source: `Union[biosimulators_processes.data_model.ModelFilepath, biosimulators_processes.data_model.BiomodelId]`
            model_language: `str`
            model_name: `str`
            model_changes: `biosimulators_processes.data_model.TimeCourseModelChanges`
    """
    model_source: Union[BiomodelID, ModelFilepath, str]
    model_id: str = None
    model_name: str = None
    model_language: str = Field(default='sbml')
    model_changes: ModelChanges = None
    model_units: ModelUnits = None

    def set_id(self, model_id=None):
        if model_id is None:
            if isinstance(self.model_source, ModelFilepath) \
                    or isinstance(self.model_source, str) and '/' in self.model_source:
                if isinstance(self.model_source, ModelFilepath):
                    source = self.model_source.value
                else:
                    source = self.model_source
                modId = source.split('/')[-1]
            elif isinstance(self.model_source, str):
                modId = self.model_source
            else:
                modId = self.model_source.value
            return f'model_from_{modId}'
        else:
            return model_id

    def set_name(self, name=None):
        if name is None:
            if self.model_id is not None:
                return self.model_id
            else:
                return 'Un-named model'
        else:
            return name

    def set_source(self):
        if isinstance(self.model_source, str):
            if 'BIOMD' in self.model_source.upper():
                self.model_source = BiomodelID(value=self.model_source)
            elif '/' in self.model_source:
                self.model_source = ModelFilepath(value=self.model_source)
            else:
                raise AttributeError('You must pass either a valid model filepath or valid Biomodel id.')

    def get_model_source_info(self, source: str, validator, **kwargs):
        """Currently only support BioModel id."""
        return validator(source, **kwargs)

    def get_biomodel_model_source_info(self, biomodel_id: str) -> Dict:
        """Return information about the BioModel ID passed."""
        return requests.get(
            url=f'https://www.ebi.ac.uk/biomodels/{biomodel_id}',
            headers={'accept': 'application/json'}).json()

    def set_model_source_info(self, **kwargs):
        """Currently only support biomodel id"""
        return self.get_biomodel_model_source_info(**kwargs)


# TODO: Provide this model if 'CopasiProcess', etc is selected by the user in prompt.

@dataclass
class TimeCourseModel(SedModel):
    """The data model declaration for process configuration schemas that support SED.

        Attributes:
            model_id: `str`
            model_source: `Union[biosimulators_processes.data_model.ModelFilepath, biosimulators_processes.data_model.BiomodelId]`
            model_language: `str` defaults to sbml
            model_name: `str`
            model_changes: `biosimulators_processes.data_model.TimeCourseModelChanges`
    """
    model_language: str = 'sbml',
    model_changes: TimeCourseModelChanges = None,
    model_units: ModelUnits = None

    def __init__(self,
                 model_source: Union[BiomodelID, ModelFilepath, str],
                 model_changes=model_changes,
                 model_id=None,
                 model_name=None):
        """Class which inherits SedModel."""
        super().__init__(model_source, model_id, model_name, model_changes)
        # TODO: extract functionality for algorithms related to UTC sims
        self.model_id = self.set_id(model_id)
        self.model_name = self.set_name(model_name)
        source_id = self.model_source.value \
            if isinstance(self.model_source, BiomodelID) or isinstance(self.model_source, ModelFilepath) \
            else self.model_source
        if 'BIOMD' in source_id:
            self.source_info = self.get_biomodel_model_source_info(source_id)


class SteadyStateModel(SedModel):
    def __init__(self,
                 model_source: Union[BiomodelID, ModelFilepath, str],
                 model_id=None,
                 model_name=None,
                 model_language: str = None,
                 model_changes: ModelChanges = None,
                 model_units: ModelUnits = None):
        """Class which inherits SedModel. # TODO: expand this."""
        super().__init__(model_source, model_id, model_name, model_language, model_changes, model_units)
        self.model_id = self.set_id(model_id)
        self.model_name = self.set_name(model_name)


class SpatialModel(SedModel):
    def __init__(self,
                 model_source: Union[BiomodelID, ModelFilepath, str],
                 model_id=None,
                 model_name=None,
                 model_language: str = None,
                 model_changes: ModelChanges = None,
                 model_units: ModelUnits = None):
        """Class which inherits SedModel. # TODO: expand this."""
        super().__init__(model_source, model_id, model_name, model_language, model_changes, model_units)
        self.model_id = self.set_id(model_id)
        self.model_name = self.set_name(model_name)


@dataclass
class TimeCourseProcess(_BaseClass):
    """Used as config for BioBuilder API"""
    model: SedModel
    method: str = 'lsoda'
    model_language: str = 'sbml'


@dataclass
class ExperimentMetadata(_BaseClass):
    def __init__(self):
        raise NotImplementedError('Please do not use this class yet. Thanks!')


@dataclass
class SimulationResult(_BaseClass):
    value: Dict[str, Any]

    def serialize(self):
        pass


@dataclass
class Experiment:
    """Consider this a 'simulation run'."""
    simulation_model: Union[TimeCourseModel, Dict[str, Any]]  # where the theory/hypothesis lies. you're stating your biological case here.
    duration: Union[int, float]  # one level above theory model. you're sure of your case and want to not tell but show it.
    results: Dict[str, Union[NoneType, SimulationResult]] = None  # consider async
    name: str = None
    metadata: ExperimentMetadata = None

    def get_results(self, source: Any):
        return source.get('results', {})

    def set_results(self):
        source = None
        results = self.get_results(source)
        self.results = results


def dynamic_process_config(name: str = None, config: Dict = None, **kwargs):
    config = config or {}
    config.update(kwargs)
    dynamic_config_types = {}
    for param_name, param_val in config.items():
        dynamic_config_types[param_name] = (type(param_val), ...)

    model_name = 'ProcessConfig'
    if name is not None:
        proc_name = name.replace(name[0], name[0].upper())
        dynamic_name = proc_name + model_name
    else:
        dynamic_name = model_name

    DynamicProcessConfig = create_model(__model_name=dynamic_name, **dynamic_config_types)

    return DynamicProcessConfig(**config)


class Port(_BaseClass):
    value: Dict



