from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
    from ..models.experiment_request_analysis_options import ExperimentRequestAnalysisOptions
    from ..models.experiment_request_topology import ExperimentRequestTopology
    from ..models.experiment_request_spatial_environment_config import ExperimentRequestSpatialEnvironmentConfig
    from ..models.experiment_request_flow import ExperimentRequestFlow
    from ..models.experiment_request_process_configs import ExperimentRequestProcessConfigs
    from ..models.experiment_request_metadata import ExperimentRequestMetadata
    from ..models.experiment_request_swap_processes import ExperimentRequestSwapProcesses
    from ..models.experiment_request_variants import ExperimentRequestVariants
    from ..models.experiment_request_initial_state import ExperimentRequestInitialState


T = TypeVar("T", bound="ExperimentRequest")


@_attrs_define
class ExperimentRequest:
    """Used by the /simulation endpoint.

    Attributes:
        experiment_id (str):
        simulation_name (Union[Unset, str]):  Default: 'sim_smsapi-e0197b80deadab35_1759239346615'.
        metadata (Union[Unset, ExperimentRequestMetadata]):
        run_parca (Union[Unset, bool]):  Default: True.
        generations (Union[Unset, int]):  Default: 1.
        n_init_sims (Union[None, Unset, int]):
        max_duration (Union[Unset, float]):  Default: 10800.0.
        initial_global_time (Union[Unset, float]):  Default: 0.0.
        time_step (Union[Unset, float]):  Default: 1.0.
        single_daughters (Union[Unset, bool]):  Default: True.
        variants (Union[Unset, ExperimentRequestVariants]):
        analysis_options (Union[Unset, ExperimentRequestAnalysisOptions]):
        gcloud (Union[None, Unset, str]):
        agent_id (Union[None, Unset, str]):
        parallel (Union[None, Unset, bool]):
        divide (Union[None, Unset, bool]):
        d_period (Union[None, Unset, bool]):
        division_threshold (Union[None, Unset, bool]):
        division_variable (Union[Unset, list[str]]):
        chromosome_path (Union[None, Unset, list[str]]):
        spatial_environment (Union[None, Unset, bool]):
        fixed_media (Union[None, Unset, str]):
        condition (Union[None, Unset, str]):
        add_processes (Union[Unset, list[str]]):
        exclude_processes (Union[Unset, list[str]]):
        profile (Union[None, Unset, bool]):
        processes (Union[Unset, list[str]]):
        process_configs (Union[Unset, ExperimentRequestProcessConfigs]):
        topology (Union[Unset, ExperimentRequestTopology]):
        engine_process_reports (Union[Unset, list[list[str]]]):
        emit_paths (Union[Unset, list[str]]):
        emit_topology (Union[None, Unset, bool]):
        emit_processes (Union[None, Unset, bool]):
        emit_config (Union[None, Unset, bool]):
        emit_unique (Union[None, Unset, bool]):
        log_updates (Union[None, Unset, bool]):
        description (Union[None, Unset, str]):
        seed (Union[None, Unset, int]):
        mar_regulon (Union[None, Unset, bool]):
        amp_lysis (Union[None, Unset, bool]):
        initial_state_file (Union[None, Unset, str]):
        skip_baseline (Union[None, Unset, bool]):
        lineage_seed (Union[None, Unset, int]):
        fail_at_max_duration (Union[None, Unset, bool]):
        inherit_from (Union[Unset, list[str]]):
        spatial_environment_config (Union[Unset, ExperimentRequestSpatialEnvironmentConfig]):
        swap_processes (Union[Unset, ExperimentRequestSwapProcesses]):
        flow (Union[Unset, ExperimentRequestFlow]):
        initial_state_overrides (Union[Unset, list[str]]):
        initial_state (Union[Unset, ExperimentRequestInitialState]):
    """

    experiment_id: str
    simulation_name: Union[Unset, str] = "sim_smsapi-e0197b80deadab35_1759239346615"
    metadata: Union[Unset, "ExperimentRequestMetadata"] = UNSET
    run_parca: Union[Unset, bool] = True
    generations: Union[Unset, int] = 1
    n_init_sims: Union[None, Unset, int] = UNSET
    max_duration: Union[Unset, float] = 10800.0
    initial_global_time: Union[Unset, float] = 0.0
    time_step: Union[Unset, float] = 1.0
    single_daughters: Union[Unset, bool] = True
    variants: Union[Unset, "ExperimentRequestVariants"] = UNSET
    analysis_options: Union[Unset, "ExperimentRequestAnalysisOptions"] = UNSET
    gcloud: Union[None, Unset, str] = UNSET
    agent_id: Union[None, Unset, str] = UNSET
    parallel: Union[None, Unset, bool] = UNSET
    divide: Union[None, Unset, bool] = UNSET
    d_period: Union[None, Unset, bool] = UNSET
    division_threshold: Union[None, Unset, bool] = UNSET
    division_variable: Union[Unset, list[str]] = UNSET
    chromosome_path: Union[None, Unset, list[str]] = UNSET
    spatial_environment: Union[None, Unset, bool] = UNSET
    fixed_media: Union[None, Unset, str] = UNSET
    condition: Union[None, Unset, str] = UNSET
    add_processes: Union[Unset, list[str]] = UNSET
    exclude_processes: Union[Unset, list[str]] = UNSET
    profile: Union[None, Unset, bool] = UNSET
    processes: Union[Unset, list[str]] = UNSET
    process_configs: Union[Unset, "ExperimentRequestProcessConfigs"] = UNSET
    topology: Union[Unset, "ExperimentRequestTopology"] = UNSET
    engine_process_reports: Union[Unset, list[list[str]]] = UNSET
    emit_paths: Union[Unset, list[str]] = UNSET
    emit_topology: Union[None, Unset, bool] = UNSET
    emit_processes: Union[None, Unset, bool] = UNSET
    emit_config: Union[None, Unset, bool] = UNSET
    emit_unique: Union[None, Unset, bool] = UNSET
    log_updates: Union[None, Unset, bool] = UNSET
    description: Union[None, Unset, str] = UNSET
    seed: Union[None, Unset, int] = UNSET
    mar_regulon: Union[None, Unset, bool] = UNSET
    amp_lysis: Union[None, Unset, bool] = UNSET
    initial_state_file: Union[None, Unset, str] = UNSET
    skip_baseline: Union[None, Unset, bool] = UNSET
    lineage_seed: Union[None, Unset, int] = UNSET
    fail_at_max_duration: Union[None, Unset, bool] = UNSET
    inherit_from: Union[Unset, list[str]] = UNSET
    spatial_environment_config: Union[Unset, "ExperimentRequestSpatialEnvironmentConfig"] = UNSET
    swap_processes: Union[Unset, "ExperimentRequestSwapProcesses"] = UNSET
    flow: Union[Unset, "ExperimentRequestFlow"] = UNSET
    initial_state_overrides: Union[Unset, list[str]] = UNSET
    initial_state: Union[Unset, "ExperimentRequestInitialState"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.experiment_request_analysis_options import ExperimentRequestAnalysisOptions
        from ..models.experiment_request_topology import ExperimentRequestTopology
        from ..models.experiment_request_spatial_environment_config import ExperimentRequestSpatialEnvironmentConfig
        from ..models.experiment_request_flow import ExperimentRequestFlow
        from ..models.experiment_request_process_configs import ExperimentRequestProcessConfigs
        from ..models.experiment_request_metadata import ExperimentRequestMetadata
        from ..models.experiment_request_swap_processes import ExperimentRequestSwapProcesses
        from ..models.experiment_request_variants import ExperimentRequestVariants
        from ..models.experiment_request_initial_state import ExperimentRequestInitialState

        experiment_id = self.experiment_id

        simulation_name = self.simulation_name

        metadata: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()

        run_parca = self.run_parca

        generations = self.generations

        n_init_sims: Union[None, Unset, int]
        if isinstance(self.n_init_sims, Unset):
            n_init_sims = UNSET
        else:
            n_init_sims = self.n_init_sims

        max_duration = self.max_duration

        initial_global_time = self.initial_global_time

        time_step = self.time_step

        single_daughters = self.single_daughters

        variants: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.variants, Unset):
            variants = self.variants.to_dict()

        analysis_options: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.analysis_options, Unset):
            analysis_options = self.analysis_options.to_dict()

        gcloud: Union[None, Unset, str]
        if isinstance(self.gcloud, Unset):
            gcloud = UNSET
        else:
            gcloud = self.gcloud

        agent_id: Union[None, Unset, str]
        if isinstance(self.agent_id, Unset):
            agent_id = UNSET
        else:
            agent_id = self.agent_id

        parallel: Union[None, Unset, bool]
        if isinstance(self.parallel, Unset):
            parallel = UNSET
        else:
            parallel = self.parallel

        divide: Union[None, Unset, bool]
        if isinstance(self.divide, Unset):
            divide = UNSET
        else:
            divide = self.divide

        d_period: Union[None, Unset, bool]
        if isinstance(self.d_period, Unset):
            d_period = UNSET
        else:
            d_period = self.d_period

        division_threshold: Union[None, Unset, bool]
        if isinstance(self.division_threshold, Unset):
            division_threshold = UNSET
        else:
            division_threshold = self.division_threshold

        division_variable: Union[Unset, list[str]] = UNSET
        if not isinstance(self.division_variable, Unset):
            division_variable = self.division_variable

        chromosome_path: Union[None, Unset, list[str]]
        if isinstance(self.chromosome_path, Unset):
            chromosome_path = UNSET
        elif isinstance(self.chromosome_path, list):
            chromosome_path = self.chromosome_path

        else:
            chromosome_path = self.chromosome_path

        spatial_environment: Union[None, Unset, bool]
        if isinstance(self.spatial_environment, Unset):
            spatial_environment = UNSET
        else:
            spatial_environment = self.spatial_environment

        fixed_media: Union[None, Unset, str]
        if isinstance(self.fixed_media, Unset):
            fixed_media = UNSET
        else:
            fixed_media = self.fixed_media

        condition: Union[None, Unset, str]
        if isinstance(self.condition, Unset):
            condition = UNSET
        else:
            condition = self.condition

        add_processes: Union[Unset, list[str]] = UNSET
        if not isinstance(self.add_processes, Unset):
            add_processes = self.add_processes

        exclude_processes: Union[Unset, list[str]] = UNSET
        if not isinstance(self.exclude_processes, Unset):
            exclude_processes = self.exclude_processes

        profile: Union[None, Unset, bool]
        if isinstance(self.profile, Unset):
            profile = UNSET
        else:
            profile = self.profile

        processes: Union[Unset, list[str]] = UNSET
        if not isinstance(self.processes, Unset):
            processes = self.processes

        process_configs: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.process_configs, Unset):
            process_configs = self.process_configs.to_dict()

        topology: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.topology, Unset):
            topology = self.topology.to_dict()

        engine_process_reports: Union[Unset, list[list[str]]] = UNSET
        if not isinstance(self.engine_process_reports, Unset):
            engine_process_reports = []
            for engine_process_reports_item_data in self.engine_process_reports:
                engine_process_reports_item = engine_process_reports_item_data

                engine_process_reports.append(engine_process_reports_item)

        emit_paths: Union[Unset, list[str]] = UNSET
        if not isinstance(self.emit_paths, Unset):
            emit_paths = self.emit_paths

        emit_topology: Union[None, Unset, bool]
        if isinstance(self.emit_topology, Unset):
            emit_topology = UNSET
        else:
            emit_topology = self.emit_topology

        emit_processes: Union[None, Unset, bool]
        if isinstance(self.emit_processes, Unset):
            emit_processes = UNSET
        else:
            emit_processes = self.emit_processes

        emit_config: Union[None, Unset, bool]
        if isinstance(self.emit_config, Unset):
            emit_config = UNSET
        else:
            emit_config = self.emit_config

        emit_unique: Union[None, Unset, bool]
        if isinstance(self.emit_unique, Unset):
            emit_unique = UNSET
        else:
            emit_unique = self.emit_unique

        log_updates: Union[None, Unset, bool]
        if isinstance(self.log_updates, Unset):
            log_updates = UNSET
        else:
            log_updates = self.log_updates

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        seed: Union[None, Unset, int]
        if isinstance(self.seed, Unset):
            seed = UNSET
        else:
            seed = self.seed

        mar_regulon: Union[None, Unset, bool]
        if isinstance(self.mar_regulon, Unset):
            mar_regulon = UNSET
        else:
            mar_regulon = self.mar_regulon

        amp_lysis: Union[None, Unset, bool]
        if isinstance(self.amp_lysis, Unset):
            amp_lysis = UNSET
        else:
            amp_lysis = self.amp_lysis

        initial_state_file: Union[None, Unset, str]
        if isinstance(self.initial_state_file, Unset):
            initial_state_file = UNSET
        else:
            initial_state_file = self.initial_state_file

        skip_baseline: Union[None, Unset, bool]
        if isinstance(self.skip_baseline, Unset):
            skip_baseline = UNSET
        else:
            skip_baseline = self.skip_baseline

        lineage_seed: Union[None, Unset, int]
        if isinstance(self.lineage_seed, Unset):
            lineage_seed = UNSET
        else:
            lineage_seed = self.lineage_seed

        fail_at_max_duration: Union[None, Unset, bool]
        if isinstance(self.fail_at_max_duration, Unset):
            fail_at_max_duration = UNSET
        else:
            fail_at_max_duration = self.fail_at_max_duration

        inherit_from: Union[Unset, list[str]] = UNSET
        if not isinstance(self.inherit_from, Unset):
            inherit_from = self.inherit_from

        spatial_environment_config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.spatial_environment_config, Unset):
            spatial_environment_config = self.spatial_environment_config.to_dict()

        swap_processes: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.swap_processes, Unset):
            swap_processes = self.swap_processes.to_dict()

        flow: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.flow, Unset):
            flow = self.flow.to_dict()

        initial_state_overrides: Union[Unset, list[str]] = UNSET
        if not isinstance(self.initial_state_overrides, Unset):
            initial_state_overrides = self.initial_state_overrides

        initial_state: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.initial_state, Unset):
            initial_state = self.initial_state.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "experiment_id": experiment_id,
        })
        if simulation_name is not UNSET:
            field_dict["simulation_name"] = simulation_name
        if metadata is not UNSET:
            field_dict["metadata"] = metadata
        if run_parca is not UNSET:
            field_dict["run_parca"] = run_parca
        if generations is not UNSET:
            field_dict["generations"] = generations
        if n_init_sims is not UNSET:
            field_dict["n_init_sims"] = n_init_sims
        if max_duration is not UNSET:
            field_dict["max_duration"] = max_duration
        if initial_global_time is not UNSET:
            field_dict["initial_global_time"] = initial_global_time
        if time_step is not UNSET:
            field_dict["time_step"] = time_step
        if single_daughters is not UNSET:
            field_dict["single_daughters"] = single_daughters
        if variants is not UNSET:
            field_dict["variants"] = variants
        if analysis_options is not UNSET:
            field_dict["analysis_options"] = analysis_options
        if gcloud is not UNSET:
            field_dict["gcloud"] = gcloud
        if agent_id is not UNSET:
            field_dict["agent_id"] = agent_id
        if parallel is not UNSET:
            field_dict["parallel"] = parallel
        if divide is not UNSET:
            field_dict["divide"] = divide
        if d_period is not UNSET:
            field_dict["d_period"] = d_period
        if division_threshold is not UNSET:
            field_dict["division_threshold"] = division_threshold
        if division_variable is not UNSET:
            field_dict["division_variable"] = division_variable
        if chromosome_path is not UNSET:
            field_dict["chromosome_path"] = chromosome_path
        if spatial_environment is not UNSET:
            field_dict["spatial_environment"] = spatial_environment
        if fixed_media is not UNSET:
            field_dict["fixed_media"] = fixed_media
        if condition is not UNSET:
            field_dict["condition"] = condition
        if add_processes is not UNSET:
            field_dict["add_processes"] = add_processes
        if exclude_processes is not UNSET:
            field_dict["exclude_processes"] = exclude_processes
        if profile is not UNSET:
            field_dict["profile"] = profile
        if processes is not UNSET:
            field_dict["processes"] = processes
        if process_configs is not UNSET:
            field_dict["process_configs"] = process_configs
        if topology is not UNSET:
            field_dict["topology"] = topology
        if engine_process_reports is not UNSET:
            field_dict["engine_process_reports"] = engine_process_reports
        if emit_paths is not UNSET:
            field_dict["emit_paths"] = emit_paths
        if emit_topology is not UNSET:
            field_dict["emit_topology"] = emit_topology
        if emit_processes is not UNSET:
            field_dict["emit_processes"] = emit_processes
        if emit_config is not UNSET:
            field_dict["emit_config"] = emit_config
        if emit_unique is not UNSET:
            field_dict["emit_unique"] = emit_unique
        if log_updates is not UNSET:
            field_dict["log_updates"] = log_updates
        if description is not UNSET:
            field_dict["description"] = description
        if seed is not UNSET:
            field_dict["seed"] = seed
        if mar_regulon is not UNSET:
            field_dict["mar_regulon"] = mar_regulon
        if amp_lysis is not UNSET:
            field_dict["amp_lysis"] = amp_lysis
        if initial_state_file is not UNSET:
            field_dict["initial_state_file"] = initial_state_file
        if skip_baseline is not UNSET:
            field_dict["skip_baseline"] = skip_baseline
        if lineage_seed is not UNSET:
            field_dict["lineage_seed"] = lineage_seed
        if fail_at_max_duration is not UNSET:
            field_dict["fail_at_max_duration"] = fail_at_max_duration
        if inherit_from is not UNSET:
            field_dict["inherit_from"] = inherit_from
        if spatial_environment_config is not UNSET:
            field_dict["spatial_environment_config"] = spatial_environment_config
        if swap_processes is not UNSET:
            field_dict["swap_processes"] = swap_processes
        if flow is not UNSET:
            field_dict["flow"] = flow
        if initial_state_overrides is not UNSET:
            field_dict["initial_state_overrides"] = initial_state_overrides
        if initial_state is not UNSET:
            field_dict["initial_state"] = initial_state

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.experiment_request_analysis_options import ExperimentRequestAnalysisOptions
        from ..models.experiment_request_topology import ExperimentRequestTopology
        from ..models.experiment_request_spatial_environment_config import ExperimentRequestSpatialEnvironmentConfig
        from ..models.experiment_request_flow import ExperimentRequestFlow
        from ..models.experiment_request_process_configs import ExperimentRequestProcessConfigs
        from ..models.experiment_request_metadata import ExperimentRequestMetadata
        from ..models.experiment_request_swap_processes import ExperimentRequestSwapProcesses
        from ..models.experiment_request_variants import ExperimentRequestVariants
        from ..models.experiment_request_initial_state import ExperimentRequestInitialState

        d = dict(src_dict)
        experiment_id = d.pop("experiment_id")

        simulation_name = d.pop("simulation_name", UNSET)

        _metadata = d.pop("metadata", UNSET)
        metadata: Union[Unset, ExperimentRequestMetadata]
        if isinstance(_metadata, Unset):
            metadata = UNSET
        else:
            metadata = ExperimentRequestMetadata.from_dict(_metadata)

        run_parca = d.pop("run_parca", UNSET)

        generations = d.pop("generations", UNSET)

        def _parse_n_init_sims(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        n_init_sims = _parse_n_init_sims(d.pop("n_init_sims", UNSET))

        max_duration = d.pop("max_duration", UNSET)

        initial_global_time = d.pop("initial_global_time", UNSET)

        time_step = d.pop("time_step", UNSET)

        single_daughters = d.pop("single_daughters", UNSET)

        _variants = d.pop("variants", UNSET)
        variants: Union[Unset, ExperimentRequestVariants]
        if isinstance(_variants, Unset):
            variants = UNSET
        else:
            variants = ExperimentRequestVariants.from_dict(_variants)

        _analysis_options = d.pop("analysis_options", UNSET)
        analysis_options: Union[Unset, ExperimentRequestAnalysisOptions]
        if isinstance(_analysis_options, Unset):
            analysis_options = UNSET
        else:
            analysis_options = ExperimentRequestAnalysisOptions.from_dict(_analysis_options)

        def _parse_gcloud(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        gcloud = _parse_gcloud(d.pop("gcloud", UNSET))

        def _parse_agent_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        agent_id = _parse_agent_id(d.pop("agent_id", UNSET))

        def _parse_parallel(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        parallel = _parse_parallel(d.pop("parallel", UNSET))

        def _parse_divide(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        divide = _parse_divide(d.pop("divide", UNSET))

        def _parse_d_period(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        d_period = _parse_d_period(d.pop("d_period", UNSET))

        def _parse_division_threshold(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        division_threshold = _parse_division_threshold(d.pop("division_threshold", UNSET))

        division_variable = cast(list[str], d.pop("division_variable", UNSET))

        def _parse_chromosome_path(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                chromosome_path_type_0 = cast(list[str], data)

                return chromosome_path_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        chromosome_path = _parse_chromosome_path(d.pop("chromosome_path", UNSET))

        def _parse_spatial_environment(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        spatial_environment = _parse_spatial_environment(d.pop("spatial_environment", UNSET))

        def _parse_fixed_media(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        fixed_media = _parse_fixed_media(d.pop("fixed_media", UNSET))

        def _parse_condition(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        condition = _parse_condition(d.pop("condition", UNSET))

        add_processes = cast(list[str], d.pop("add_processes", UNSET))

        exclude_processes = cast(list[str], d.pop("exclude_processes", UNSET))

        def _parse_profile(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        profile = _parse_profile(d.pop("profile", UNSET))

        processes = cast(list[str], d.pop("processes", UNSET))

        _process_configs = d.pop("process_configs", UNSET)
        process_configs: Union[Unset, ExperimentRequestProcessConfigs]
        if isinstance(_process_configs, Unset):
            process_configs = UNSET
        else:
            process_configs = ExperimentRequestProcessConfigs.from_dict(_process_configs)

        _topology = d.pop("topology", UNSET)
        topology: Union[Unset, ExperimentRequestTopology]
        if isinstance(_topology, Unset):
            topology = UNSET
        else:
            topology = ExperimentRequestTopology.from_dict(_topology)

        engine_process_reports = []
        _engine_process_reports = d.pop("engine_process_reports", UNSET)
        for engine_process_reports_item_data in _engine_process_reports or []:
            engine_process_reports_item = cast(list[str], engine_process_reports_item_data)

            engine_process_reports.append(engine_process_reports_item)

        emit_paths = cast(list[str], d.pop("emit_paths", UNSET))

        def _parse_emit_topology(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        emit_topology = _parse_emit_topology(d.pop("emit_topology", UNSET))

        def _parse_emit_processes(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        emit_processes = _parse_emit_processes(d.pop("emit_processes", UNSET))

        def _parse_emit_config(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        emit_config = _parse_emit_config(d.pop("emit_config", UNSET))

        def _parse_emit_unique(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        emit_unique = _parse_emit_unique(d.pop("emit_unique", UNSET))

        def _parse_log_updates(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        log_updates = _parse_log_updates(d.pop("log_updates", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_seed(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        seed = _parse_seed(d.pop("seed", UNSET))

        def _parse_mar_regulon(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        mar_regulon = _parse_mar_regulon(d.pop("mar_regulon", UNSET))

        def _parse_amp_lysis(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        amp_lysis = _parse_amp_lysis(d.pop("amp_lysis", UNSET))

        def _parse_initial_state_file(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        initial_state_file = _parse_initial_state_file(d.pop("initial_state_file", UNSET))

        def _parse_skip_baseline(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        skip_baseline = _parse_skip_baseline(d.pop("skip_baseline", UNSET))

        def _parse_lineage_seed(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        lineage_seed = _parse_lineage_seed(d.pop("lineage_seed", UNSET))

        def _parse_fail_at_max_duration(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        fail_at_max_duration = _parse_fail_at_max_duration(d.pop("fail_at_max_duration", UNSET))

        inherit_from = cast(list[str], d.pop("inherit_from", UNSET))

        _spatial_environment_config = d.pop("spatial_environment_config", UNSET)
        spatial_environment_config: Union[Unset, ExperimentRequestSpatialEnvironmentConfig]
        if isinstance(_spatial_environment_config, Unset):
            spatial_environment_config = UNSET
        else:
            spatial_environment_config = ExperimentRequestSpatialEnvironmentConfig.from_dict(
                _spatial_environment_config
            )

        _swap_processes = d.pop("swap_processes", UNSET)
        swap_processes: Union[Unset, ExperimentRequestSwapProcesses]
        if isinstance(_swap_processes, Unset):
            swap_processes = UNSET
        else:
            swap_processes = ExperimentRequestSwapProcesses.from_dict(_swap_processes)

        _flow = d.pop("flow", UNSET)
        flow: Union[Unset, ExperimentRequestFlow]
        if isinstance(_flow, Unset):
            flow = UNSET
        else:
            flow = ExperimentRequestFlow.from_dict(_flow)

        initial_state_overrides = cast(list[str], d.pop("initial_state_overrides", UNSET))

        _initial_state = d.pop("initial_state", UNSET)
        initial_state: Union[Unset, ExperimentRequestInitialState]
        if isinstance(_initial_state, Unset):
            initial_state = UNSET
        else:
            initial_state = ExperimentRequestInitialState.from_dict(_initial_state)

        experiment_request = cls(
            experiment_id=experiment_id,
            simulation_name=simulation_name,
            metadata=metadata,
            run_parca=run_parca,
            generations=generations,
            n_init_sims=n_init_sims,
            max_duration=max_duration,
            initial_global_time=initial_global_time,
            time_step=time_step,
            single_daughters=single_daughters,
            variants=variants,
            analysis_options=analysis_options,
            gcloud=gcloud,
            agent_id=agent_id,
            parallel=parallel,
            divide=divide,
            d_period=d_period,
            division_threshold=division_threshold,
            division_variable=division_variable,
            chromosome_path=chromosome_path,
            spatial_environment=spatial_environment,
            fixed_media=fixed_media,
            condition=condition,
            add_processes=add_processes,
            exclude_processes=exclude_processes,
            profile=profile,
            processes=processes,
            process_configs=process_configs,
            topology=topology,
            engine_process_reports=engine_process_reports,
            emit_paths=emit_paths,
            emit_topology=emit_topology,
            emit_processes=emit_processes,
            emit_config=emit_config,
            emit_unique=emit_unique,
            log_updates=log_updates,
            description=description,
            seed=seed,
            mar_regulon=mar_regulon,
            amp_lysis=amp_lysis,
            initial_state_file=initial_state_file,
            skip_baseline=skip_baseline,
            lineage_seed=lineage_seed,
            fail_at_max_duration=fail_at_max_duration,
            inherit_from=inherit_from,
            spatial_environment_config=spatial_environment_config,
            swap_processes=swap_processes,
            flow=flow,
            initial_state_overrides=initial_state_overrides,
            initial_state=initial_state,
        )

        experiment_request.additional_properties = d
        return experiment_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
