"""
======================
Polypeptide Elongation
======================

This process models the polymerization of amino acids into polypeptides
by ribosomes using an mRNA transcript as a template. Elongation terminates
once a ribosome has reached the end of an mRNA transcript. Polymerization
occurs across all ribosomes simultaneously and resources are allocated to
maximize the progress of all ribosomes within the limits of the maximum ribosome
elongation rate, available amino acids and GTP, and the length of the transcript.
"""

import abc
import warnings
from typing import Any, Callable, Optional, Tuple

from numba import njit
import numpy as np
import numpy.typing as npt
from scipy.integrate import solve_ivp
from unum import Unum

# wcEcoli imports TODO: somehow resolve this: is it okay to use PyPI?
from sms_api.notebook.wholecell.utils.polymerize import buildSequences, polymerize, computeMassIncrease
from sms_api.notebook.wholecell.utils.random import stochasticRound
from sms_api.notebook.wholecell.utils import units

# vivarium imports
from vivarium.core.composition import simulate_process
from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units as vivunits
from vivarium.plots.simulation_output import plot_variables
from vivarium.core.process import Step, Process
from vivarium.library.dict_utils import deep_merge

# vivarium-ecoli imports
from sms_api.notebook.schema import (
    listener_schema,
    numpy_schema,
    counts,
    attrs,
    bulk_name_to_idx,
)
from sms_api.notebook.registries import topology_registry


class Requester(Step):
    """Requester Step

    Accepts a PartitionedProcess as an input, and runs in coordination with an
    Evolver that uses the same PartitionedProcess.
    """

    defaults = {"process": None}

    def __init__(self, parameters=None):
        assert isinstance(parameters["process"], PartitionedProcess)
        if parameters["process"].parallel:
            raise RuntimeError("PartitionedProcess objects cannot be parallelized.")
        parameters["name"] = f"{parameters['process'].name}_requester"
        super().__init__(parameters)

    def update_condition(self, timestep, states):
        """
        Implements variable timestepping for partitioned processes

        Vivarium cycles through all :py:class:~vivarium.core.process.Step`
        instances every time a :py:class:`~vivarium.core.process.Process`
        instance updates the simulation state. When that happens, Vivarium
        will only call the :py:meth:`~.Requester.next_update` method of this
        Requester if ``update_condition`` returns True.

        Each process has access to a process-specific ``next_update_time``
        store and the ``global_time`` store. If the next update time is
        less than or equal to the global time, the process runs. If the
        next update time is ever earlier than the global time, this usually
        indicates that the global clock process is running with too large
        a timestep, preventing accurate timekeeping.
        """
        if states["next_update_time"] <= states["global_time"]:
            if states["next_update_time"] < states["global_time"]:
                warnings.warn(
                    f"{self.name} updated at t="
                    f"{states['global_time']} instead of t="
                    f"{states['next_update_time']}. Decrease the "
                    "timestep of the global_clock process for more "
                    "accurate timekeeping."
                )
            return True
        return False

    def ports_schema(self):
        process = self.parameters.get("process")
        ports = process.get_schema()
        ports["request"] = {
            "bulk": {
                "_updater": "set",
                "_divider": "null",
                "_emit": False,
            }
        }
        ports["process"] = {
            "_default": tuple(),
            "_updater": "set",
            "_divider": "null",
            "_emit": False,
        }
        ports["global_time"] = {"_default": 0.0}
        ports["timestep"] = {"_default": process.parameters["timestep"]}
        ports["next_update_time"] = {
            "_default": process.parameters["timestep"],
            "_updater": "set",
            "_divider": "set",
        }
        self.cached_bulk_ports = list(ports["request"].keys())
        return ports

    def next_update(self, timestep, states):
        process = states["process"][0]
        request = process.calculate_request(states["timestep"], states)
        process.request_set = True

        request["request"] = {}
        # Send bulk requests through request port
        for bulk_port in self.cached_bulk_ports:
            bulk_request = request.pop(bulk_port, None)
            if bulk_request is not None:
                request["request"][bulk_port] = bulk_request

        # Ensure listeners are updated if present
        listeners = request.pop("listeners", None)
        if listeners is not None:
            request["listeners"] = listeners

        # Update shared process instance
        request["process"] = (process,)
        return request


class Evolver(Step):
    """Evolver Step

    Accepts a PartitionedProcess as an input, and runs in coordination with an
    Requester that uses the same PartitionedProcess.
    """

    defaults = {"process": None}

    def __init__(self, parameters=None):
        assert isinstance(parameters["process"], PartitionedProcess)
        parameters["name"] = f"{parameters['process'].name}_evolver"
        super().__init__(parameters)

    def update_condition(self, timestep, states):
        """
        See :py:meth:`~.Requester.update_condition`.
        """
        if states["next_update_time"] <= states["global_time"]:
            if states["next_update_time"] < states["global_time"]:
                warnings.warn(
                    f"{self.name} updated at t="
                    f"{states['global_time']} instead of t="
                    f"{states['next_update_time']}. Decrease the "
                    "timestep for the global clock process for more "
                    "accurate timekeeping."
                )
            return True
        return False

    def ports_schema(self):
        process = self.parameters.get("process")
        ports = process.get_schema()
        ports["allocate"] = {
            "bulk": {
                "_updater": "set",
                "_divider": "null",
                "_emit": False,
            }
        }
        ports["process"] = {
            "_default": tuple(),
            "_updater": "set",
            "_divider": "null",
            "_emit": False,
        }
        ports["global_time"] = {"_default": 0.0}
        ports["timestep"] = {"_default": process.parameters["timestep"]}
        ports["next_update_time"] = {
            "_default": process.parameters["timestep"],
            "_updater": "set",
            "_divider": "set",
        }
        return ports

    def next_update(self, timestep, states):
        allocations = states.pop("allocate")
        states = deep_merge(states, allocations)
        process = states["process"][0]

        # If the Requester has not run yet, skip the Evolver's update to
        # let the Requester run in the next time step. This problem
        # often arises after division because after the step divider
        # runs, Vivarium wants to run the Evolvers instead of re-running
        # the Requesters. Skipping the Evolvers in this case means our
        # timesteps are slightly off. However, the alternative is to run
        # self.process.calculate_request and discard the result before
        # running the Evolver this timestep, which means we skip the
        # Allocator. Skipping the Allocator can cause the simulation to
        # crash, so having a slightly off timestep is preferable.
        if not process.request_set:
            return {}

        update = process.evolve_state(states["timestep"], states)
        update["process"] = (process,)
        update["next_update_time"] = states["global_time"] + states["timestep"]
        return update


class PartitionedProcess(Process):
    """Partitioned Process Base Class

    This is the base class for all processes whose updates can be partitioned.
    """

    def __init__(self, parameters=None):
        super().__init__(parameters)

        # set partition mode
        self.evolve_only = self.parameters.get("evolve_only", False)
        self.request_only = self.parameters.get("request_only", False)
        self.request_set = False

        # register topology
        assert self.name
        assert self.topology
        topology_registry.register(self.name, self.topology)

    @abc.abstractmethod
    def ports_schema(self):
        return {}

    @abc.abstractmethod
    def calculate_request(self, timestep, states):
        return {}

    @abc.abstractmethod
    def evolve_state(self, timestep, states):
        return {}

    def next_update(self, timestep, states):
        if self.request_only:
            return self.calculate_request(timestep, states)
        if self.evolve_only:
            return self.evolve_state(timestep, states)

        requests = self.calculate_request(timestep, states)
        bulk_requests = requests.pop("bulk", [])
        if bulk_requests:
            bulk_copy = states["bulk"].copy()
            for bulk_idx, request in bulk_requests:
                bulk_copy[bulk_idx] = request
            states["bulk"] = bulk_copy
        states = deep_merge(states, requests)
        update = self.evolve_state(timestep, states)
        if "listeners" in requests:
            update["listeners"] = deep_merge(update["listeners"], requests["listeners"])
        return update


MICROMOLAR_UNITS = units.umol / units.L
"""Units used for all concentrations."""
REMOVED_FROM_CHARGING = {"L-SELENOCYSTEINE[c]"}
"""Amino acids to remove from charging when running with
``steady_state_trna_charging``"""


# Register default topology for this process, associating it with process name
NAME = "ecoli-polypeptide-elongation"
TOPOLOGY = {
    "environment": ("environment",),
    "boundary": ("boundary",),
    "listeners": ("listeners",),
    "active_ribosome": ("unique", "active_ribosome"),
    "bulk": ("bulk",),
    "polypeptide_elongation": ("process_state", "polypeptide_elongation"),
    # Non-partitioned counts
    "bulk_total": ("bulk",),
    "timestep": ("timestep",),
}
topology_registry.register(NAME, TOPOLOGY)

DEFAULT_AA_NAMES = [
    "L-ALPHA-ALANINE[c]",
    "ARG[c]",
    "ASN[c]",
    "L-ASPARTATE[c]",
    "CYS[c]",
    "GLT[c]",
    "GLN[c]",
    "GLY[c]",
    "HIS[c]",
    "ILE[c]",
    "LEU[c]",
    "LYS[c]",
    "MET[c]",
    "PHE[c]",
    "PRO[c]",
    "SER[c]",
    "THR[c]",
    "TRP[c]",
    "TYR[c]",
    "L-SELENOCYSTEINE[c]",
    "VAL[c]",
]


class PolypeptideElongation(PartitionedProcess):
    """Polypeptide Elongation PartitionedProcess

    defaults:
        proteinIds: array length n of protein names
    """

    name = NAME
    topology = TOPOLOGY
    defaults = {
        "time_step": 1,
        "n_avogadro": 6.02214076e23 / units.mol,
        "proteinIds": np.array([]),
        "proteinLengths": np.array([]),
        "proteinSequences": np.array([[]]),
        "aaWeightsIncorporated": np.array([]),
        "endWeight": np.array([2.99146113e-08]),
        "variable_elongation": False,
        "make_elongation_rates": (lambda random, rate, timestep, variable: np.array([])),
        "next_aa_pad": 1,
        "ribosomeElongationRate": 17.388824902723737,
        "translation_aa_supply": {"minimal": np.array([])},
        "import_threshold": 1e-05,
        "aa_from_trna": np.zeros(21),
        "gtpPerElongation": 4.2,
        "aa_supply_in_charging": False,
        "mechanistic_translation_supply": False,
        "mechanistic_aa_transport": False,
        "ppgpp_regulation": False,
        "disable_ppgpp_elongation_inhibition": False,
        "trna_charging": False,
        "translation_supply": False,
        "mechanistic_supply": False,
        "ribosome30S": "ribosome30S",
        "ribosome50S": "ribosome50S",
        "amino_acids": DEFAULT_AA_NAMES,
        "aa_exchange_names": DEFAULT_AA_NAMES,
        "basal_elongation_rate": 22.0,
        "ribosomeElongationRateDict": {"minimal": 17.388824902723737 * units.aa / units.s},
        "uncharged_trna_names": np.array([]),
        "aaNames": DEFAULT_AA_NAMES,
        "aa_enzymes": [],
        "proton": "PROTON",
        "water": "H2O",
        "cellDensity": 1100 * units.g / units.L,
        "elongation_max": 22 * units.aa / units.s,
        "aa_from_synthetase": np.array([[]]),
        "charging_stoich_matrix": np.array([[]]),
        "charged_trna_names": [],
        "charging_molecule_names": [],
        "synthetase_names": [],
        "ppgpp_reaction_names": [],
        "ppgpp_reaction_metabolites": [],
        "ppgpp_reaction_stoich": np.array([[]]),
        "ppgpp_synthesis_reaction": "GDPPYPHOSKIN-RXN",
        "ppgpp_degradation_reaction": "PPGPPSYN-RXN",
        "aa_importers": [],
        "amino_acid_export": None,
        "synthesis_index": 0,
        "aa_exporters": [],
        "get_pathway_enzyme_counts_per_aa": None,
        "import_constraint_threshold": 0,
        "unit_conversion": 0,
        "elong_rate_by_ppgpp": 0,
        "amino_acid_import": None,
        "degradation_index": 1,
        "amino_acid_synthesis": None,
        "rela": "RELA",
        "spot": "SPOT",
        "ppgpp": "ppGpp",
        "kS": 100.0,
        "KMtf": 1.0,
        "KMaa": 100.0,
        "krta": 1.0,
        "krtf": 500.0,
        "KD_RelA": 0.26,
        "k_RelA": 75.0,
        "k_SpoT_syn": 2.6,
        "k_SpoT_deg": 0.23,
        "KI_SpoT": 20.0,
        "aa_supply_scaling": lambda aa_conc, aa_in_media: 0,
        "seed": 0,
        "emit_unique": False,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        # Simulation options
        self.aa_supply_in_charging = self.parameters["aa_supply_in_charging"]
        self.mechanistic_translation_supply = self.parameters["mechanistic_translation_supply"]
        self.mechanistic_aa_transport = self.parameters["mechanistic_aa_transport"]
        self.ppgpp_regulation = self.parameters["ppgpp_regulation"]
        self.disable_ppgpp_elongation_inhibition = self.parameters["disable_ppgpp_elongation_inhibition"]
        self.variable_elongation = self.parameters["variable_elongation"]
        self.variable_polymerize = self.ppgpp_regulation or self.variable_elongation
        translation_supply = self.parameters["translation_supply"]
        trna_charging = self.parameters["trna_charging"]

        # Load parameters
        self.n_avogadro = self.parameters["n_avogadro"]
        self.proteinIds = self.parameters["proteinIds"]
        self.protein_lengths = self.parameters["proteinLengths"]
        self.proteinSequences = self.parameters["proteinSequences"]
        self.aaWeightsIncorporated = self.parameters["aaWeightsIncorporated"]
        self.endWeight = self.parameters["endWeight"]
        self.make_elongation_rates = self.parameters["make_elongation_rates"]
        self.next_aa_pad = self.parameters["next_aa_pad"]

        self.ribosome30S = self.parameters["ribosome30S"]
        self.ribosome50S = self.parameters["ribosome50S"]
        self.amino_acids = self.parameters["amino_acids"]
        self.aa_exchange_names = self.parameters["aa_exchange_names"]
        self.aa_environment_names = [aa[:-3] for aa in self.aa_exchange_names]
        self.aa_enzymes = self.parameters["aa_enzymes"]

        self.ribosomeElongationRate = self.parameters["ribosomeElongationRate"]

        # Amino acid supply calculations
        self.translation_aa_supply = self.parameters["translation_aa_supply"]
        self.import_threshold = self.parameters["import_threshold"]

        # Used for figure in publication
        self.trpAIndex = np.where(self.proteinIds == "TRYPSYN-APROTEIN[c]")[0][0]

        self.elngRateFactor = 1.0

        # Data structures for charging
        self.aa_from_trna = self.parameters["aa_from_trna"]

        # Set modeling method
        # TODO: Test that these models all work properly
        if trna_charging:
            self.elongation_model = SteadyStateElongationModel(self.parameters, self)
        elif translation_supply:
            self.elongation_model = TranslationSupplyElongationModel(self.parameters, self)
        else:
            self.elongation_model = BaseElongationModel(self.parameters, self)

        # Growth associated maintenance energy requirements for elongations
        self.gtpPerElongation = self.parameters["gtpPerElongation"]
        # Need to account for ATP hydrolysis for charging that has been
        # removed from measured GAM (ATP -> AMP is 2 hydrolysis reactions)
        # if charging reactions are not explicitly modeled
        if not trna_charging:
            self.gtpPerElongation += 2

        # basic molecule names
        self.proton = self.parameters["proton"]
        self.water = self.parameters["water"]
        self.rela = self.parameters["rela"]
        self.spot = self.parameters["spot"]
        self.ppgpp = self.parameters["ppgpp"]
        self.aa_importers = self.parameters["aa_importers"]
        self.aa_exporters = self.parameters["aa_exporters"]
        # Numpy index for bulk molecule
        self.proton_idx = None

        # Names of molecules associated with tRNA charging
        self.ppgpp_reaction_metabolites = self.parameters["ppgpp_reaction_metabolites"]
        self.uncharged_trna_names = self.parameters["uncharged_trna_names"]
        self.charged_trna_names = self.parameters["charged_trna_names"]
        self.charging_molecule_names = self.parameters["charging_molecule_names"]
        self.synthetase_names = self.parameters["synthetase_names"]

        self.seed = self.parameters["seed"]
        self.random_state = np.random.RandomState(seed=self.seed)

        self.zero_aa_exchange_rates = MICROMOLAR_UNITS / units.s * np.zeros(len(self.amino_acids))

    def ports_schema(self):
        return {
            "environment": {
                "media_id": {"_default": "", "_updater": "set"},
                "exchange": {"*": {"_default": 0}},
            },
            "boundary": {"external": {aa: {"_default": 0} for aa in sorted(self.aa_environment_names)}},
            "listeners": {
                "mass": listener_schema({"cell_mass": 0.0, "dry_mass": 0.0}),
                "growth_limits": listener_schema({
                    "fraction_trna_charged": (
                        [0.0] * len(self.uncharged_trna_names),
                        self.uncharged_trna_names,
                    ),
                    "aa_allocated": ([0] * len(self.amino_acids), self.amino_acids),
                    "aa_pool_size": ([0] * len(self.amino_acids), self.amino_acids),
                    "aa_request_size": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "active_ribosome_allocated": 0,
                    "net_charged": (
                        [0] * len(self.uncharged_trna_names),
                        self.uncharged_trna_names,
                    ),
                    "aas_used": ([0] * len(self.amino_acids), self.amino_acids),
                    "aa_count_diff": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    # Below only if trna_charging enbaled
                    "original_aa_supply": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_in_media": (
                        [False] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "synthetase_conc": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "uncharged_trna_conc": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "charged_trna_conc": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_conc": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "ribosome_conc": 0.0,
                    "fraction_aa_to_elongate": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_supply": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "aa_synthesis": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_import": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "aa_export": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "aa_importers": (
                        [0] * len(self.aa_importers),
                        self.aa_importers,
                    ),
                    "aa_exporters": (
                        [0] * len(self.aa_exporters),
                        self.aa_exporters,
                    ),
                    "aa_supply_enzymes_fwd": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_supply_enzymes_rev": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_supply_aa_conc": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_supply_fraction_fwd": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_supply_fraction_rev": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "ppgpp_conc": 0.0,
                    "rela_conc": 0.0,
                    "spot_conc": 0.0,
                    "rela_syn": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "spot_syn": 0.0,
                    "spot_deg": 0.0,
                    "spot_deg_inhibited": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "trna_charged": ([0] * len(self.amino_acids), self.amino_acids),
                }),
                "ribosome_data": listener_schema({
                    "translation_supply": (
                        [0.0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "effective_elongation_rate": 0.0,
                    "aa_count_in_sequence": (
                        [0] * len(self.amino_acids),
                        self.amino_acids,
                    ),
                    "aa_counts": ([0.0] * len(self.amino_acids), self.amino_acids),
                    "actual_elongations": 0,
                    "actual_elongation_hist": [0] * 22,
                    "elongations_non_terminating_hist": [0] * 22,
                    "did_terminate": 0,
                    "termination_loss": 0,
                    "num_trpA_terminated": 0,
                    "process_elongation_rate": 0.0,
                }),
            },
            "bulk": numpy_schema("bulk"),
            "bulk_total": numpy_schema("bulk"),
            "active_ribosome": numpy_schema("active_ribosome", emit=self.parameters["emit_unique"]),
            "polypeptide_elongation": {
                "aa_count_diff": {
                    "_default": [0.0] * len(self.amino_acids),
                    "_emit": True,
                    "_updater": "set",
                    "_divider": "empty_dict",
                },
                "gtp_to_hydrolyze": {
                    "_default": 0.0,
                    "_emit": True,
                    "_updater": "set",
                    "_divider": "zero",
                },
                "aa_exchange_rates": {
                    "_default": self.zero_aa_exchange_rates.copy(),
                    "_emit": True,
                    "_updater": "set",
                    "_divider": "set",
                },
            },
            "timestep": {"_default": self.parameters["time_step"]},
        }

    def calculate_request(self, timestep, states):
        """
        Set ribosome elongation rate based on simulation medium environment and elongation rate factor
        which is used to create single-cell variability in growth rate
        The maximum number of amino acids that can be elongated in a single timestep is set to 22
        intentionally as the minimum number of padding values on the protein sequence matrix is set to 22.
        If timesteps longer than 1.0s are used, this feature will lead to errors in the effective ribosome
        elongation rate.
        """

        if self.proton_idx is None:
            bulk_ids = states["bulk"]["id"]
            self.proton_idx = bulk_name_to_idx(self.proton, bulk_ids)
            self.water_idx = bulk_name_to_idx(self.water, bulk_ids)
            self.rela_idx = bulk_name_to_idx(self.rela, bulk_ids)
            self.spot_idx = bulk_name_to_idx(self.spot, bulk_ids)
            self.ppgpp_idx = bulk_name_to_idx(self.ppgpp, bulk_ids)
            self.monomer_idx = bulk_name_to_idx(self.proteinIds, bulk_ids)
            self.amino_acid_idx = bulk_name_to_idx(self.amino_acids, bulk_ids)
            self.aa_enzyme_idx = bulk_name_to_idx(self.aa_enzymes, bulk_ids)
            self.ppgpp_rxn_metabolites_idx = bulk_name_to_idx(self.ppgpp_reaction_metabolites, bulk_ids)
            self.uncharged_trna_idx = bulk_name_to_idx(self.uncharged_trna_names, bulk_ids)
            self.charged_trna_idx = bulk_name_to_idx(self.charged_trna_names, bulk_ids)
            self.charging_molecule_idx = bulk_name_to_idx(self.charging_molecule_names, bulk_ids)
            self.synthetase_idx = bulk_name_to_idx(self.synthetase_names, bulk_ids)
            self.ribosome30S_idx = bulk_name_to_idx(self.ribosome30S, bulk_ids)
            self.ribosome50S_idx = bulk_name_to_idx(self.ribosome50S, bulk_ids)
            self.aa_importer_idx = bulk_name_to_idx(self.aa_importers, bulk_ids)
            self.aa_exporter_idx = bulk_name_to_idx(self.aa_exporters, bulk_ids)

        # MODEL SPECIFIC: get ribosome elongation rate
        self.ribosomeElongationRate = self.elongation_model.elongation_rate(states)

        # If there are no active ribosomes, return immediately
        if states["active_ribosome"]["_entryState"].sum() == 0:
            return {"listeners": {"ribosome_data": {}, "growth_limits": {}}}

        # Build sequences to request appropriate amount of amino acids to
        # polymerize for next timestep
        (
            proteinIndexes,
            peptideLengths,
        ) = attrs(states["active_ribosome"], ["protein_index", "peptide_length"])

        self.elongation_rates = self.make_elongation_rates(
            self.random_state,
            self.ribosomeElongationRate,
            states["timestep"],
            self.variable_elongation,
        )

        sequences = buildSequences(self.proteinSequences, proteinIndexes, peptideLengths, self.elongation_rates)

        sequenceHasAA = sequences != polymerize.PAD_VALUE
        aasInSequences = np.bincount(sequences[sequenceHasAA], minlength=21)

        # Calculate AA supply for expected doubling of protein
        dryMass = states["listeners"]["mass"]["dry_mass"] * units.fg
        current_media_id = states["environment"]["media_id"]
        translation_supply_rate = self.translation_aa_supply[current_media_id] * self.elngRateFactor
        mol_aas_supplied = translation_supply_rate * dryMass * states["timestep"] * units.s
        self.aa_supply = units.strip_empty_units(mol_aas_supplied * self.n_avogadro)

        # MODEL SPECIFIC: Calculate AA request
        fraction_charged, aa_counts_for_translation, requests = self.elongation_model.request(states, aasInSequences)

        # Write to listeners
        listeners = requests.setdefault("listeners", {})
        ribosome_data_listener = listeners.setdefault("ribosome_data", {})
        ribosome_data_listener["translation_supply"] = translation_supply_rate.asNumber()
        growth_limits_listener = requests["listeners"].setdefault("growth_limits", {})
        growth_limits_listener["fraction_trna_charged"] = np.dot(fraction_charged, self.aa_from_trna)
        growth_limits_listener["aa_pool_size"] = counts(states["bulk_total"], self.amino_acid_idx)
        growth_limits_listener["aa_request_size"] = aa_counts_for_translation
        # Simulations without mechanistic translation supply need this to be
        # manually zeroed after division
        proc_data = requests.setdefault("polypeptide_elongation", {})
        proc_data.setdefault("aa_exchange_rates", np.zeros(len(self.amino_acids)))

        return requests

    def evolve_state(self, timestep, states):
        """
        Set ribosome elongation rate based on simulation medium environment and elongation rate factor
        which is used to create single-cell variability in growth rate
        The maximum number of amino acids that can be elongated in a single timestep is set to 22
        intentionally as the minimum number of padding values on the protein sequence matrix is set to 22.
        If timesteps longer than 1.0s are used, this feature will lead to errors in the effective ribosome
        elongation rate.
        """

        update = {
            "listeners": {"ribosome_data": {}, "growth_limits": {}},
            "polypeptide_elongation": {},
            "active_ribosome": {},
            "bulk": [],
        }

        # Begin wcEcoli evolveState()
        # Set values for metabolism in case of early return
        update["polypeptide_elongation"]["gtp_to_hydrolyze"] = 0
        update["polypeptide_elongation"]["aa_count_diff"] = np.zeros(len(self.amino_acids), dtype=np.float64)

        # Get number of active ribosomes
        n_active_ribosomes = states["active_ribosome"]["_entryState"].sum()
        update["listeners"]["growth_limits"]["active_ribosome_allocated"] = n_active_ribosomes
        update["listeners"]["growth_limits"]["aa_allocated"] = counts(states["bulk"], self.amino_acid_idx)

        # If there are no active ribosomes, return immediately
        if n_active_ribosomes == 0:
            return update

        # Polypeptide elongation requires counts to be updated in real-time
        # so make a writeable copy of bulk counts to do so
        states["bulk"] = counts(states["bulk"], range(len(states["bulk"])))

        # Build amino acids sequences for each ribosome to polymerize
        protein_indexes, peptide_lengths, positions_on_mRNA = attrs(
            states["active_ribosome"],
            ["protein_index", "peptide_length", "pos_on_mRNA"],
        )

        all_sequences = buildSequences(
            self.proteinSequences,
            protein_indexes,
            peptide_lengths,
            self.elongation_rates + self.next_aa_pad,
        )
        sequences = all_sequences[:, : -self.next_aa_pad].copy()

        if sequences.size == 0:
            return update

        # Calculate elongation resource capacity
        aaCountInSequence = np.bincount(sequences[(sequences != polymerize.PAD_VALUE)])
        total_aa_counts = counts(states["bulk"], self.amino_acid_idx)
        charged_trna_counts = counts(states["bulk"], self.charged_trna_idx)

        # MODEL SPECIFIC: Get amino acid counts
        aa_counts_for_translation = self.elongation_model.final_amino_acids(total_aa_counts, charged_trna_counts)

        # Using polymerization algorithm elongate each ribosome up to the limits
        # of amino acids, sequence, and GTP
        result = polymerize(
            sequences,
            aa_counts_for_translation,
            10000000,  # Set to a large number, the limit is now taken care of in metabolism
            self.random_state,
            self.elongation_rates[protein_indexes],
            variable_elongation=self.variable_polymerize,
        )

        sequence_elongations = result.sequenceElongation
        aas_used = result.monomerUsages
        nElongations = result.nReactions

        next_amino_acid = all_sequences[np.arange(len(sequence_elongations)), sequence_elongations]
        next_amino_acid_count = np.bincount(next_amino_acid[next_amino_acid != polymerize.PAD_VALUE], minlength=21)

        # Update masses of ribosomes attached to polymerizing polypeptides
        added_protein_mass = computeMassIncrease(sequences, sequence_elongations, self.aaWeightsIncorporated)

        updated_lengths = peptide_lengths + sequence_elongations
        updated_positions_on_mRNA = positions_on_mRNA + 3 * sequence_elongations

        didInitialize = (sequence_elongations > 0) & (peptide_lengths == 0)

        added_protein_mass[didInitialize] += self.endWeight

        # Write current average elongation to listener
        currElongRate = (sequence_elongations.sum() / n_active_ribosomes) / states["timestep"]

        # Ribosomes that reach the end of their sequences are terminated and
        # dissociated into 30S and 50S subunits. The polypeptide that they are
        # polymerizing is converted into a protein in BulkMolecules
        terminalLengths = self.protein_lengths[protein_indexes]

        didTerminate = updated_lengths == terminalLengths

        terminatedProteins = np.bincount(protein_indexes[didTerminate], minlength=self.proteinSequences.shape[0])

        (protein_mass,) = attrs(states["active_ribosome"], ["massDiff_protein"])
        update["active_ribosome"].update({
            "delete": np.where(didTerminate)[0],
            "set": {
                "massDiff_protein": protein_mass + added_protein_mass,
                "peptide_length": updated_lengths,
                "pos_on_mRNA": updated_positions_on_mRNA,
            },
        })

        update["bulk"].append((self.monomer_idx, terminatedProteins))
        states["bulk"][self.monomer_idx] += terminatedProteins

        nTerminated = didTerminate.sum()
        nInitialized = didInitialize.sum()

        update["bulk"].append((self.ribosome30S_idx, nTerminated))
        update["bulk"].append((self.ribosome50S_idx, nTerminated))
        states["bulk"][self.ribosome30S_idx] += nTerminated
        states["bulk"][self.ribosome50S_idx] += nTerminated

        # MODEL SPECIFIC: evolve
        net_charged, aa_count_diff, evolve_update = self.elongation_model.evolve(
            states,
            total_aa_counts,
            aas_used,
            next_amino_acid_count,
            nElongations,
            nInitialized,
        )

        evolve_bulk_update = evolve_update.pop("bulk")
        update = deep_merge(update, evolve_update)
        update["bulk"].extend(evolve_bulk_update)

        update["polypeptide_elongation"]["aa_count_diff"] = aa_count_diff
        # GTP hydrolysis is carried out in Metabolism process for growth
        # associated maintenance. This is passed to metabolism.
        update["polypeptide_elongation"]["gtp_to_hydrolyze"] = self.gtpPerElongation * nElongations

        # Write data to listeners
        update["listeners"]["growth_limits"]["net_charged"] = net_charged
        update["listeners"]["growth_limits"]["aas_used"] = aas_used
        update["listeners"]["growth_limits"]["aa_count_diff"] = aa_count_diff

        ribosome_data_listener = update["listeners"].setdefault("ribosome_data", {})
        ribosome_data_listener["effective_elongation_rate"] = currElongRate
        ribosome_data_listener["aa_count_in_sequence"] = aaCountInSequence
        ribosome_data_listener["aa_counts"] = aa_counts_for_translation
        ribosome_data_listener["actual_elongations"] = sequence_elongations.sum()
        ribosome_data_listener["actual_elongation_hist"] = np.histogram(sequence_elongations, bins=np.arange(0, 23))[0]
        ribosome_data_listener["elongations_non_terminating_hist"] = np.histogram(
            sequence_elongations[~didTerminate], bins=np.arange(0, 23)
        )[0]
        ribosome_data_listener["did_terminate"] = didTerminate.sum()
        ribosome_data_listener["termination_loss"] = (terminalLengths - peptide_lengths)[didTerminate].sum()
        ribosome_data_listener["num_trpA_terminated"] = terminatedProteins[self.trpAIndex]
        ribosome_data_listener["process_elongation_rate"] = self.ribosomeElongationRate / states["timestep"]

        return update


class BaseElongationModel(object):
    """
    Base Model: Request amino acids according to upcoming sequence, assuming
    max ribosome elongation.
    """

    def __init__(self, parameters, process):
        self.parameters = parameters
        self.process = process
        self.basal_elongation_rate = self.parameters["basal_elongation_rate"]
        self.ribosomeElongationRateDict = self.parameters["ribosomeElongationRateDict"]

    def elongation_rate(self, states):
        """
        Sets ribosome elongation rate accordint to the media; returns
        max value of 22 amino acids/second.
        """
        current_media_id = states["environment"]["media_id"]
        rate = self.process.elngRateFactor * self.ribosomeElongationRateDict[current_media_id].asNumber(
            units.aa / units.s
        )
        return np.min([self.basal_elongation_rate, rate])

    def amino_acid_counts(self, aasInSequences):
        return aasInSequences

    def request(
        self, states: dict, aasInSequences: npt.NDArray[np.int64]
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], dict]:
        aa_counts_for_translation = self.amino_acid_counts(aasInSequences)

        requests = {"bulk": [(self.process.amino_acid_idx, aa_counts_for_translation)]}

        # Not modeling charging so set fraction charged to 0 for all tRNA
        fraction_charged = np.zeros(len(self.process.amino_acid_idx))

        return fraction_charged, aa_counts_for_translation.astype(float), requests

    def final_amino_acids(self, total_aa_counts, charged_trna_counts):
        return total_aa_counts

    def evolve(
        self,
        states,
        total_aa_counts,
        aas_used,
        next_amino_acid_count,
        nElongations,
        nInitialized,
    ):
        # Update counts of amino acids and water to reflect polymerization
        # reactions
        net_charged = np.zeros(len(self.parameters["uncharged_trna_names"]), dtype=np.int64)
        return (
            net_charged,
            np.zeros(len(self.process.amino_acids), dtype=np.float64),
            {
                "bulk": [
                    (self.process.amino_acid_idx, -aas_used),
                    (self.process.water_idx, nElongations - nInitialized),
                ]
            },
        )


class TranslationSupplyElongationModel(BaseElongationModel):
    """
    Translation Supply Model: Requests minimum of 1) upcoming amino acid
    sequence assuming max ribosome elongation (ie. Base Model) and 2)
    estimation based on doubling the proteome in one cell cycle (does not
    use ribosome elongation, computed in Parca).
    """

    def __init__(self, parameters, process):
        super().__init__(parameters, process)

    def elongation_rate(self, states):
        """
        Sets ribosome elongation rate accordint to the media; returns
        max value of 22 amino acids/second.
        """
        return self.basal_elongation_rate

    def amino_acid_counts(self, aasInSequences):
        # Check if this is required. It is a better request but there may be
        # fewer elongations.
        return np.fmin(self.process.aa_supply, aasInSequences)


class SteadyStateElongationModel(TranslationSupplyElongationModel):
    """
    Steady State Charging Model: Requests amino acids based on the
    Michaelis-Menten competitive inhibition model.
    """

    def __init__(self, parameters, process):
        super().__init__(parameters, process)

        # Cell parameters
        self.cellDensity = self.parameters["cellDensity"]

        # Names of molecules associated with tRNA charging
        self.charged_trna_names = self.parameters["charged_trna_names"]
        self.charging_molecule_names = self.parameters["charging_molecule_names"]
        self.synthetase_names = self.parameters["synthetase_names"]

        # Data structures for charging
        self.aa_from_synthetase = self.parameters["aa_from_synthetase"]
        self.charging_stoich_matrix = self.parameters["charging_stoich_matrix"]
        self.charging_molecules_not_aa = np.array([
            mol not in set(self.parameters["amino_acids"]) for mol in self.charging_molecule_names
        ])

        # ppGpp synthesis
        self.ppgpp_reaction_metabolites = self.parameters["ppgpp_reaction_metabolites"]
        self.elong_rate_by_ppgpp = self.parameters["elong_rate_by_ppgpp"]

        # Parameters for tRNA charging, ribosome elongation and ppGpp reactions
        self.charging_params = {
            "kS": self.parameters["kS"],
            "KMaa": self.parameters["KMaa"],
            "KMtf": self.parameters["KMtf"],
            "krta": self.parameters["krta"],
            "krtf": self.parameters["krtf"],
            "max_elong_rate": float(self.parameters["elongation_max"].asNumber(units.aa / units.s)),
            "charging_mask": np.array([aa not in REMOVED_FROM_CHARGING for aa in self.parameters["amino_acids"]]),
            "unit_conversion": self.parameters["unit_conversion"],
        }
        self.ppgpp_params = {
            "KD_RelA": self.parameters["KD_RelA"],
            "k_RelA": self.parameters["k_RelA"],
            "k_SpoT_syn": self.parameters["k_SpoT_syn"],
            "k_SpoT_deg": self.parameters["k_SpoT_deg"],
            "KI_SpoT": self.parameters["KI_SpoT"],
            "ppgpp_reaction_stoich": self.parameters["ppgpp_reaction_stoich"],
            "synthesis_index": self.parameters["synthesis_index"],
            "degradation_index": self.parameters["degradation_index"],
        }

        # Amino acid supply calculations
        self.aa_supply_scaling = self.parameters["aa_supply_scaling"]

        self.amino_acid_synthesis = self.parameters["amino_acid_synthesis"]
        self.amino_acid_import = self.parameters["amino_acid_import"]
        self.amino_acid_export = self.parameters["amino_acid_export"]
        self.get_pathway_enzyme_counts_per_aa = self.parameters["get_pathway_enzyme_counts_per_aa"]

        # Comparing two values with units is faster than converting units
        # and comparing magnitudes
        self.import_constraint_threshold = self.parameters["import_constraint_threshold"] * vivunits.mM

    def elongation_rate(self, states):
        if self.process.ppgpp_regulation and not self.process.disable_ppgpp_elongation_inhibition:
            cell_mass = states["listeners"]["mass"]["cell_mass"] * units.fg
            cell_volume = cell_mass / self.cellDensity
            counts_to_molar = 1 / (self.process.n_avogadro * cell_volume)
            ppgpp_count = counts(states["bulk"], self.process.ppgpp_idx)
            ppgpp_conc = ppgpp_count * counts_to_molar
            rate = self.elong_rate_by_ppgpp(ppgpp_conc, self.basal_elongation_rate).asNumber(units.aa / units.s)
        else:
            rate = super().elongation_rate(states)
        return rate

    def request(
        self, states: dict, aasInSequences: npt.NDArray[np.int64]
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], dict]:
        # Conversion from counts to molarity
        cell_mass = states["listeners"]["mass"]["cell_mass"] * units.fg
        dry_mass = states["listeners"]["mass"]["dry_mass"] * units.fg
        cell_volume = cell_mass / self.cellDensity
        self.counts_to_molar = 1 / (self.process.n_avogadro * cell_volume)

        # ppGpp related concentrations
        ppgpp_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.ppgpp_idx)
        rela_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.rela_idx)
        spot_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.spot_idx)

        # Get counts and convert synthetase and tRNA to a per AA basis
        synthetase_counts = np.dot(
            self.aa_from_synthetase,
            counts(states["bulk_total"], self.process.synthetase_idx),
        )
        aa_counts = counts(states["bulk_total"], self.process.amino_acid_idx)
        uncharged_trna_array = counts(states["bulk_total"], self.process.uncharged_trna_idx)
        charged_trna_array = counts(states["bulk_total"], self.process.charged_trna_idx)
        uncharged_trna_counts = np.dot(self.process.aa_from_trna, uncharged_trna_array)
        charged_trna_counts = np.dot(self.process.aa_from_trna, charged_trna_array)
        ribosome_counts = states["active_ribosome"]["_entryState"].sum()

        # Get concentration
        f = aasInSequences / aasInSequences.sum()
        synthetase_conc = self.counts_to_molar * synthetase_counts
        aa_conc = self.counts_to_molar * aa_counts
        uncharged_trna_conc = self.counts_to_molar * uncharged_trna_counts
        charged_trna_conc = self.counts_to_molar * charged_trna_counts
        ribosome_conc = self.counts_to_molar * ribosome_counts

        # Calculate amino acid supply
        aa_in_media = np.array([
            states["boundary"]["external"][aa] > self.import_constraint_threshold
            for aa in self.process.aa_environment_names
        ])
        fwd_enzyme_counts, rev_enzyme_counts = self.get_pathway_enzyme_counts_per_aa(
            counts(states["bulk_total"], self.process.aa_enzyme_idx)
        )
        importer_counts = counts(states["bulk_total"], self.process.aa_importer_idx)
        exporter_counts = counts(states["bulk_total"], self.process.aa_exporter_idx)
        synthesis, fwd_saturation, rev_saturation = self.amino_acid_synthesis(
            fwd_enzyme_counts, rev_enzyme_counts, aa_conc
        )
        import_rates = self.amino_acid_import(
            aa_in_media,
            dry_mass,
            aa_conc,
            importer_counts,
            self.process.mechanistic_aa_transport,
        )
        export_rates = self.amino_acid_export(exporter_counts, aa_conc, self.process.mechanistic_aa_transport)
        exchange_rates = import_rates - export_rates

        supply_function = get_charging_supply_function(
            self.process.aa_supply_in_charging,
            self.process.mechanistic_translation_supply,
            self.process.mechanistic_aa_transport,
            self.amino_acid_synthesis,
            self.amino_acid_import,
            self.amino_acid_export,
            self.aa_supply_scaling,
            self.counts_to_molar,
            self.process.aa_supply,
            fwd_enzyme_counts,
            rev_enzyme_counts,
            dry_mass,
            importer_counts,
            exporter_counts,
            aa_in_media,
        )

        # Calculate steady state tRNA levels and resulting elongation rate
        self.charging_params["max_elong_rate"] = self.elongation_rate(states)
        (
            fraction_charged,
            v_rib,
            synthesis_in_charging,
            import_in_charging,
            export_in_charging,
        ) = calculate_trna_charging(
            synthetase_conc,
            uncharged_trna_conc,
            charged_trna_conc,
            aa_conc,
            ribosome_conc,
            f,
            self.charging_params,
            supply=supply_function,
            limit_v_rib=True,
            time_limit=states["timestep"],
        )

        # Use the supply calculated from each sub timestep while solving the charging steady state
        if self.process.aa_supply_in_charging:
            conversion = 1 / self.counts_to_molar.asNumber(MICROMOLAR_UNITS) / states["timestep"]
            synthesis = conversion * synthesis_in_charging
            import_rates = conversion * import_in_charging
            export_rates = conversion * export_in_charging
            self.process.aa_supply = synthesis + import_rates - export_rates
        # Use the supply calculated from the starting amino acid concentrations only
        elif self.process.mechanistic_translation_supply:
            # Set supply based on mechanistic synthesis and supply
            self.process.aa_supply = states["timestep"] * (synthesis + exchange_rates)
        else:
            # Adjust aa_supply higher if amino acid concentrations are low
            # Improves stability of charging and mimics amino acid synthesis
            # inhibition and export
            self.process.aa_supply *= self.aa_supply_scaling(aa_conc, aa_in_media)

        aa_counts_for_translation = v_rib * f * states["timestep"] / self.counts_to_molar.asNumber(MICROMOLAR_UNITS)

        total_trna = charged_trna_array + uncharged_trna_array
        final_charged_trna = stochasticRound(
            self.process.random_state,
            np.dot(fraction_charged, self.process.aa_from_trna * total_trna),
        )

        # Request charged tRNA that will become uncharged
        charged_trna_request = charged_trna_array - final_charged_trna
        charged_trna_request[charged_trna_request < 0] = 0
        uncharged_trna_request = final_charged_trna - charged_trna_array
        uncharged_trna_request[uncharged_trna_request < 0] = 0
        self.uncharged_trna_to_charge = uncharged_trna_request

        self.aa_counts_for_translation = np.array(aa_counts_for_translation)

        fraction_trna_per_aa = total_trna / np.dot(
            np.dot(self.process.aa_from_trna, total_trna), self.process.aa_from_trna
        )
        total_charging_reactions = stochasticRound(
            self.process.random_state,
            np.dot(aa_counts_for_translation, self.process.aa_from_trna) * fraction_trna_per_aa
            + uncharged_trna_request,
        )

        # Only request molecules that will be consumed in the charging reactions
        aa_from_uncharging = -self.charging_stoich_matrix @ charged_trna_request
        aa_from_uncharging[self.charging_molecules_not_aa] = 0
        requested_molecules = -np.dot(self.charging_stoich_matrix, total_charging_reactions) - aa_from_uncharging
        requested_molecules[requested_molecules < 0] = 0
        self.uncharged_trna_to_charge = uncharged_trna_request

        # ppGpp reactions based on charged tRNA
        bulk_request = [
            (
                self.process.charging_molecule_idx,
                requested_molecules.astype(int),
            ),
            (self.process.charged_trna_idx, charged_trna_request.astype(int)),
            # Request water for transfer of AA from tRNA for initial polypeptide.
            # This is severe overestimate assuming the worst case that every
            # elongation is initializing a polypeptide. This excess of water
            # shouldn't matter though.
            (self.process.water_idx, int(aa_counts_for_translation.sum())),
        ]
        if self.process.ppgpp_regulation:
            total_trna_conc = self.counts_to_molar * (uncharged_trna_counts + charged_trna_counts)
            updated_charged_trna_conc = total_trna_conc * fraction_charged
            updated_uncharged_trna_conc = total_trna_conc - updated_charged_trna_conc
            delta_metabolites, *_ = ppgpp_metabolite_changes(
                updated_uncharged_trna_conc,
                updated_charged_trna_conc,
                ribosome_conc,
                f,
                rela_conc,
                spot_conc,
                ppgpp_conc,
                self.counts_to_molar,
                v_rib,
                self.charging_params,
                self.ppgpp_params,
                states["timestep"],
                request=True,
                random_state=self.process.random_state,
            )

            request_ppgpp_metabolites = -delta_metabolites.astype(int)
            ppgpp_request = counts(states["bulk"], self.process.ppgpp_idx)
            bulk_request.append((self.process.ppgpp_idx, ppgpp_request))
            bulk_request.append((
                self.process.ppgpp_rxn_metabolites_idx,
                request_ppgpp_metabolites,
            ))

        return (
            fraction_charged,
            aa_counts_for_translation,
            {
                "bulk": bulk_request,
                "listeners": {
                    "growth_limits": {
                        "original_aa_supply": self.process.aa_supply,
                        "aa_in_media": aa_in_media,
                        "synthetase_conc": synthetase_conc.asNumber(MICROMOLAR_UNITS),
                        "uncharged_trna_conc": uncharged_trna_conc.asNumber(MICROMOLAR_UNITS),
                        "charged_trna_conc": charged_trna_conc.asNumber(MICROMOLAR_UNITS),
                        "aa_conc": aa_conc.asNumber(MICROMOLAR_UNITS),
                        "ribosome_conc": ribosome_conc.asNumber(MICROMOLAR_UNITS),
                        "fraction_aa_to_elongate": f,
                        "aa_supply": self.process.aa_supply,
                        "aa_synthesis": synthesis * states["timestep"],
                        "aa_import": import_rates * states["timestep"],
                        "aa_export": export_rates * states["timestep"],
                        "aa_supply_enzymes_fwd": fwd_enzyme_counts,
                        "aa_supply_enzymes_rev": rev_enzyme_counts,
                        "aa_importers": importer_counts,
                        "aa_exporters": exporter_counts,
                        "aa_supply_aa_conc": aa_conc.asNumber(units.mmol / units.L),
                        "aa_supply_fraction_fwd": fwd_saturation,
                        "aa_supply_fraction_rev": rev_saturation,
                        "ppgpp_conc": ppgpp_conc.asNumber(MICROMOLAR_UNITS),
                        "rela_conc": rela_conc.asNumber(MICROMOLAR_UNITS),
                        "spot_conc": spot_conc.asNumber(MICROMOLAR_UNITS),
                    }
                },
                "polypeptide_elongation": {
                    "aa_exchange_rates": self.counts_to_molar / units.s * (import_rates - export_rates)
                },
            },
        )

    def final_amino_acids(self, total_aa_counts, charged_trna_counts):
        charged_counts_to_uncharge = self.process.aa_from_trna @ charged_trna_counts
        return np.fmin(total_aa_counts + charged_counts_to_uncharge, self.aa_counts_for_translation)

    def evolve(
        self,
        states,
        total_aa_counts,
        aas_used,
        next_amino_acid_count,
        nElongations,
        nInitialized,
    ):
        update = {
            "bulk": [],
            "listeners": {"growth_limits": {}},
        }

        # Get tRNA counts
        uncharged_trna = counts(states["bulk"], self.process.uncharged_trna_idx)
        charged_trna = counts(states["bulk"], self.process.charged_trna_idx)
        total_trna = uncharged_trna + charged_trna

        # Adjust molecules for number of charging reactions that occurred
        ## Determine limitations for charging and uncharging reactions
        charged_and_elongated_per_aa = np.fmax(0, (aas_used - self.process.aa_from_trna @ charged_trna))
        aa_for_charging = total_aa_counts - charged_and_elongated_per_aa
        n_aa_charged = np.fmin(
            aa_for_charging,
            np.dot(
                self.process.aa_from_trna,
                np.fmin(self.uncharged_trna_to_charge, uncharged_trna),
            ),
        )
        n_uncharged_per_aa = aas_used - charged_and_elongated_per_aa

        ## Calculate changes in tRNA based on limitations
        n_trna_charged = self.distribution_from_aa(n_aa_charged, uncharged_trna, True)
        n_trna_uncharged = self.distribution_from_aa(n_uncharged_per_aa, charged_trna, True)

        ## Determine reactions that are charged and elongated in same time step without changing
        ## charged or uncharged counts
        charged_and_elongated = self.distribution_from_aa(charged_and_elongated_per_aa, total_trna)

        ## Determine total number of reactions that occur
        total_uncharging_reactions = charged_and_elongated + n_trna_uncharged
        total_charging_reactions = charged_and_elongated + n_trna_charged
        net_charged = total_charging_reactions - total_uncharging_reactions
        charging_mol_delta = np.dot(self.charging_stoich_matrix, total_charging_reactions).astype(int)
        update["bulk"].append((self.process.charging_molecule_idx, charging_mol_delta))
        states["bulk"][self.process.charging_molecule_idx] += charging_mol_delta

        ## Account for uncharging of tRNA during elongation
        update["bulk"].append((self.process.charged_trna_idx, -total_uncharging_reactions))
        update["bulk"].append((self.process.uncharged_trna_idx, total_uncharging_reactions))
        states["bulk"][self.process.charged_trna_idx] += -total_uncharging_reactions
        states["bulk"][self.process.uncharged_trna_idx] += total_uncharging_reactions

        # Update proton counts to reflect polymerization reactions and transfer of AA from tRNA
        # Peptide bond formation releases a water but transferring AA from tRNA consumes a OH-
        # Net production of H+ for each elongation, consume extra water for each initialization
        # since a peptide bond doesn't form
        update["bulk"].append((self.process.proton_idx, nElongations))
        update["bulk"].append((self.process.water_idx, -nInitialized))
        states["bulk"][self.process.proton_idx] += nElongations
        states["bulk"][self.process.water_idx] += -nInitialized

        # Create or degrade ppGpp
        # This should come after all countInc/countDec calls since it shares some molecules with
        # other views and those counts should be updated to get the proper limits on ppGpp reactions
        if self.process.ppgpp_regulation:
            v_rib = (nElongations * self.counts_to_molar).asNumber(MICROMOLAR_UNITS) / states["timestep"]
            ribosome_conc = self.counts_to_molar * states["active_ribosome"]["_entryState"].sum()
            updated_uncharged_trna_counts = counts(states["bulk_total"], self.process.uncharged_trna_idx) - net_charged
            updated_charged_trna_counts = counts(states["bulk_total"], self.process.charged_trna_idx) + net_charged
            uncharged_trna_conc = self.counts_to_molar * np.dot(
                self.process.aa_from_trna, updated_uncharged_trna_counts
            )
            charged_trna_conc = self.counts_to_molar * np.dot(self.process.aa_from_trna, updated_charged_trna_counts)
            ppgpp_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.ppgpp_idx)
            rela_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.rela_idx)
            spot_conc = self.counts_to_molar * counts(states["bulk_total"], self.process.spot_idx)

            # Need to include the next amino acid the ribosome sees for certain
            # cases where elongation does not occur, otherwise f will be NaN
            aa_at_ribosome = aas_used + next_amino_acid_count
            f = aa_at_ribosome / aa_at_ribosome.sum()
            limits = counts(states["bulk"], self.process.ppgpp_rxn_metabolites_idx)
            (
                delta_metabolites,
                ppgpp_syn,
                ppgpp_deg,
                rela_syn,
                spot_syn,
                spot_deg,
                spot_deg_inhibited,
            ) = ppgpp_metabolite_changes(
                uncharged_trna_conc,
                charged_trna_conc,
                ribosome_conc,
                f,
                rela_conc,
                spot_conc,
                ppgpp_conc,
                self.counts_to_molar,
                v_rib,
                self.charging_params,
                self.ppgpp_params,
                states["timestep"],
                random_state=self.process.random_state,
                limits=limits,
            )

            update["listeners"]["growth_limits"] = {
                "rela_syn": rela_syn,
                "spot_syn": spot_syn,
                "spot_deg": spot_deg,
                "spot_deg_inhibited": spot_deg_inhibited,
            }

            update["bulk"].append((self.process.ppgpp_rxn_metabolites_idx, delta_metabolites.astype(int)))
            states["bulk"][self.process.ppgpp_rxn_metabolites_idx] += delta_metabolites.astype(int)

        # Use the difference between (expected AA supply based on expected
        # doubling time and current DCW) and AA used to charge tRNA to update
        # the concentration target in metabolism during the next time step
        aa_used_trna = np.dot(self.process.aa_from_trna, total_charging_reactions)
        aa_diff = self.process.aa_supply - aa_used_trna

        update["listeners"]["growth_limits"]["trna_charged"] = aa_used_trna.astype(int)

        return (
            net_charged,
            aa_diff,
            update,
        )

    def distribution_from_aa(
        self,
        n_aa: npt.NDArray[np.int64],
        n_trna: npt.NDArray[np.int64],
        limited: bool = False,
    ) -> npt.NDArray[np.int64]:
        """
        Distributes counts of amino acids to tRNAs that are associated with
        each amino acid. Uses self.process.aa_from_trna mapping to distribute
        from amino acids to tRNA based on the fraction that each tRNA species
        makes up for all tRNA species that code for the same amino acid.

        Args:
            n_aa: counts of each amino acid to distribute to each tRNA
            n_trna: counts of each tRNA to determine the distribution
            limited: optional, if True, limits the amino acids
                distributed to each tRNA to the number of tRNA that are
                available (n_trna)

        Returns:
            Distributed counts for each tRNA
        """

        # Determine the fraction each tRNA species makes up out of all tRNA of
        # the associated amino acid
        with np.errstate(invalid="ignore"):
            f_trna = n_trna / np.dot(np.dot(self.process.aa_from_trna, n_trna), self.process.aa_from_trna)
        f_trna[~np.isfinite(f_trna)] = 0

        trna_counts = np.zeros(f_trna.shape, np.int64)
        for count, row in zip(n_aa, self.process.aa_from_trna):
            idx = row == 1
            frac = f_trna[idx]

            counts = np.floor(frac * count)
            diff = int(count - counts.sum())

            # Add additional counts to get up to counts to distribute
            # Prevent adding over the number of tRNA available if limited
            if diff > 0:
                if limited:
                    for _ in range(diff):
                        frac[(n_trna[idx] - counts) == 0] = 0
                        # normalize for multinomial distribution
                        frac /= frac.sum()
                        adjustment = self.process.random_state.multinomial(1, frac)
                        counts += adjustment
                else:
                    adjustment = self.process.random_state.multinomial(diff, frac)
                    counts += adjustment

            trna_counts[idx] = counts

        return trna_counts


def ppgpp_metabolite_changes(
    uncharged_trna_conc: Unum,
    charged_trna_conc: Unum,
    ribosome_conc: Unum,
    f: npt.NDArray[np.float64],
    rela_conc: Unum,
    spot_conc: Unum,
    ppgpp_conc: Unum,
    counts_to_molar: Unum,
    v_rib: Unum,
    charging_params: dict[str, Any],
    ppgpp_params: dict[str, Any],
    time_step: float,
    request: bool = False,
    limits: Optional[npt.NDArray[np.float64]] = None,
    random_state: Optional[np.random.RandomState] = None,
) -> tuple[npt.NDArray[np.int64], int, int, Unum, Unum, Unum, Unum]:
    """
    Calculates the changes in metabolite counts based on ppGpp synthesis and
    degradation reactions.

    Args:
        uncharged_trna_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`)
            of uncharged tRNA associated with each amino acid
        charged_trna_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`)
            of charged tRNA associated with each amino acid
        ribosome_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`)
            of active ribosomes
        f: fraction of each amino acid to be incorporated
            to total amino acids incorporated
        rela_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`) of RelA
        spot_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`) of SpoT
        ppgpp_conc: concentration (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`) of ppGpp
        counts_to_molar: conversion factor
            from counts to molarity (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`)
        v_rib: rate of amino acid incorporation at the ribosome (units of uM/s)
        charging_params: parameters used in charging equations
        ppgpp_params: parameters used in ppGpp reactions
        time_step: length of the current time step
        request: if True, only considers reactant stoichiometry,
            otherwise considers reactants and products. For use in
            calculateRequest. GDP appears as both a reactant and product
            and the request can be off the actual use if not handled in this
            manner.
        limits: counts of molecules that are available to prevent
            negative total counts as a result of delta_metabolites.
            If None, no limits are placed on molecule changes.
        random_state: random state for the process
    Returns:
        7-element tuple containing

        - **delta_metabolites**: the change in counts of each metabolite
          involved in ppGpp reactions
        - **n_syn_reactions**: the number of ppGpp synthesis reactions
        - **n_deg_reactions**: the number of ppGpp degradation reactions
        - **v_rela_syn**: rate of synthesis from RelA per amino
          acid tRNA species
        - **v_spot_syn**: rate of synthesis from SpoT
        - **v_deg**: rate of degradation from SpoT
        - **v_deg_inhibited**: rate of degradation from SpoT per
          amino acid tRNA species
    """

    if random_state is None:
        random_state = np.random.RandomState()

    uncharged_trna_conc = uncharged_trna_conc.asNumber(MICROMOLAR_UNITS)
    charged_trna_conc = charged_trna_conc.asNumber(MICROMOLAR_UNITS)
    ribosome_conc = ribosome_conc.asNumber(MICROMOLAR_UNITS)
    rela_conc = rela_conc.asNumber(MICROMOLAR_UNITS)
    spot_conc = spot_conc.asNumber(MICROMOLAR_UNITS)
    ppgpp_conc = ppgpp_conc.asNumber(MICROMOLAR_UNITS)
    counts_to_micromolar = counts_to_molar.asNumber(MICROMOLAR_UNITS)

    numerator = 1 + charged_trna_conc / charging_params["krta"] + uncharged_trna_conc / charging_params["krtf"]
    saturated_charged = charged_trna_conc / charging_params["krta"] / numerator
    saturated_uncharged = uncharged_trna_conc / charging_params["krtf"] / numerator
    if v_rib == 0:
        ribosome_conc_a_site = f * ribosome_conc
    else:
        ribosome_conc_a_site = f * v_rib / (saturated_charged * charging_params["max_elong_rate"])
    ribosomes_bound_to_uncharged = ribosome_conc_a_site * saturated_uncharged

    # Handle rare cases when tRNA concentrations are 0
    # Can result in inf and nan so assume a fraction of ribosomes
    # bind to the uncharged tRNA if any tRNA are present or 0 if not
    mask = ~np.isfinite(ribosomes_bound_to_uncharged)
    ribosomes_bound_to_uncharged[mask] = (
        ribosome_conc * f[mask] * np.array(uncharged_trna_conc[mask] + charged_trna_conc[mask] > 0)
    )

    # Calculate active fraction of RelA
    competitive_inhibition = 1 + ribosomes_bound_to_uncharged / ppgpp_params["KD_RelA"]
    inhibition_product = np.prod(competitive_inhibition)
    with np.errstate(divide="ignore"):
        frac_rela = 1 / (
            ppgpp_params["KD_RelA"] / ribosomes_bound_to_uncharged * inhibition_product / competitive_inhibition + 1
        )

    # Calculate rates for synthesis and degradation
    v_rela_syn = ppgpp_params["k_RelA"] * rela_conc * frac_rela
    v_spot_syn = ppgpp_params["k_SpoT_syn"] * spot_conc
    v_syn = v_rela_syn.sum() + v_spot_syn
    max_deg = ppgpp_params["k_SpoT_deg"] * spot_conc * ppgpp_conc
    fractions = uncharged_trna_conc / ppgpp_params["KI_SpoT"]
    v_deg = max_deg / (1 + fractions.sum())
    v_deg_inhibited = (max_deg - v_deg) * fractions / fractions.sum()

    # Convert to discrete reactions
    n_syn_reactions = stochasticRound(random_state, v_syn * time_step / counts_to_micromolar)[0]
    n_deg_reactions = stochasticRound(random_state, v_deg * time_step / counts_to_micromolar)[0]

    # Only look at reactant stoichiometry if requesting molecules to use
    if request:
        ppgpp_reaction_stoich = np.zeros_like(ppgpp_params["ppgpp_reaction_stoich"])
        reactants = ppgpp_params["ppgpp_reaction_stoich"] < 0
        ppgpp_reaction_stoich[reactants] = ppgpp_params["ppgpp_reaction_stoich"][reactants]
    else:
        ppgpp_reaction_stoich = ppgpp_params["ppgpp_reaction_stoich"]

    # Calculate the change in metabolites and adjust to limits if provided
    # Possible reactions are adjusted down to limits if the change in any
    # metabolites would result in negative counts
    max_iterations = int(n_deg_reactions + n_syn_reactions + 1)
    old_counts = None
    for it in range(max_iterations):
        delta_metabolites = (
            ppgpp_reaction_stoich[:, ppgpp_params["synthesis_index"]] * n_syn_reactions
            + ppgpp_reaction_stoich[:, ppgpp_params["degradation_index"]] * n_deg_reactions
        )

        if limits is None:
            break
        else:
            final_counts = delta_metabolites + limits

            if np.all(final_counts >= 0) or (old_counts is not None and np.all(final_counts == old_counts)):
                break

            limited_index = np.argmin(final_counts)
            if ppgpp_reaction_stoich[limited_index, ppgpp_params["synthesis_index"]] < 0:
                limited = np.ceil(
                    final_counts[limited_index] / ppgpp_reaction_stoich[limited_index, ppgpp_params["synthesis_index"]]
                )
                n_syn_reactions -= min(limited, n_syn_reactions)
            if ppgpp_reaction_stoich[limited_index, ppgpp_params["degradation_index"]] < 0:
                limited = np.ceil(
                    final_counts[limited_index]
                    / ppgpp_reaction_stoich[limited_index, ppgpp_params["degradation_index"]]
                )
                n_deg_reactions -= min(limited, n_deg_reactions)

            old_counts = final_counts
    else:
        raise ValueError("Failed to meet molecule limits with ppGpp reactions.")

    return (
        delta_metabolites,
        n_syn_reactions,
        n_deg_reactions,
        v_rela_syn,
        v_spot_syn,
        v_deg,
        v_deg_inhibited,
    )


def calculate_trna_charging(
    synthetase_conc: Unum,
    uncharged_trna_conc: Unum,
    charged_trna_conc: Unum,
    aa_conc: Unum,
    ribosome_conc: Unum,
    f: Unum,
    params: dict[str, Any],
    supply: Optional[Callable] = None,
    time_limit: float = 1000,
    limit_v_rib: bool = False,
    use_disabled_aas: bool = False,
) -> tuple[Unum, float, Unum, Unum, Unum]:
    """
    Calculates the steady state value of tRNA based on charging and
    incorporation through polypeptide elongation. The fraction of
    charged/uncharged is also used to determine how quickly the
    ribosome is elongating. All concentrations are given in units of
    :py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`.

    Args:
        synthetase_conc: concentration of synthetases associated with
            each amino acid
        uncharged_trna_conc: concentration of uncharged tRNA associated
            with each amino acid
        charged_trna_conc: concentration of charged tRNA associated with
            each amino acid
        aa_conc: concentration of each amino acid
        ribosome_conc: concentration of active ribosomes
        f: fraction of each amino acid to be incorporated to total amino
            acids incorporated
        params: parameters used in charging equations
        supply: function to get the rate of amino acid supply (synthesis
            and import) based on amino acid concentrations. If None, amino
            acid concentrations remain constant during charging
        time_limit: time limit to reach steady state
        limit_v_rib: if True, v_rib is limited to the number of amino acids
            that are available
        use_disabled_aas: if False, amino acids in
            :py:data:`~ecoli.processes.polypeptide_elongation.REMOVED_FROM_CHARGING`
            are excluded from charging

    Returns:
        5-element tuple containing

        - **new_fraction_charged**: fraction of total tRNA that is charged for each
          amino acid species
        - **v_rib**: ribosomal elongation rate in units of uM/s
        - **total_synthesis**: the total amount of amino acids synthesized during charging
          in units of MICROMOLAR_UNITS. Will be zeros if supply function is not given.
        - **total_import**: the total amount of amino acids imported during charging
          in units of MICROMOLAR_UNITS. Will be zeros if supply function is not given.
        - **total_export**: the total amount of amino acids exported during charging
          in units of MICROMOLAR_UNITS. Will be zeros if supply function is not given.
    """

    def negative_check(trna1: npt.NDArray[np.float64], trna2: npt.NDArray[np.float64]):
        """
        Check for floating point precision issues that can lead to small
        negative numbers instead of 0. Adjusts both species of tRNA to
        bring concentration of trna1 to 0 and keep the same total concentration.

        Args:
            trna1: concentration of one tRNA species (charged or uncharged)
            trna2: concentration of another tRNA species (charged or uncharged)
        """

        mask = trna1 < 0
        trna2[mask] = trna1[mask] + trna2[mask]
        trna1[mask] = 0

    def dcdt(t: float, c: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """
        Function for solve_ivp to integrate

        Args:
            c: 1D array of concentrations of uncharged and charged tRNAs
                dims: 2 * number of amino acids (uncharged tRNA come first, then charged)
            t: time of integration step

        Returns:
            Array of dc/dt for tRNA concentrations
                dims: 2 * number of amino acids (uncharged tRNA come first, then charged)
        """

        v_charging, dtrna, daa = dcdt_jit(
            t,
            c,
            n_aas_masked,
            n_aas,
            mask,
            params["kS"],
            synthetase_conc,
            params["KMaa"],
            params["KMtf"],
            f,
            params["krta"],
            params["krtf"],
            params["max_elong_rate"],
            ribosome_conc,
            limit_v_rib,
            aa_rate_limit,
            v_rib_max,
        )

        if supply is None:
            v_synthesis = np.zeros(n_aas)
            v_import = np.zeros(n_aas)
            v_export = np.zeros(n_aas)
        else:
            aa_conc = c[2 * n_aas_masked : 2 * n_aas_masked + n_aas]
            v_synthesis, v_import, v_export = supply(unit_conversion * aa_conc)
            v_supply = v_synthesis + v_import - v_export
            daa[mask] = v_supply[mask] - v_charging

        return np.hstack((-dtrna, dtrna, daa, v_synthesis, v_import, v_export))

    # Convert inputs for integration
    synthetase_conc = synthetase_conc.asNumber(MICROMOLAR_UNITS)
    uncharged_trna_conc = uncharged_trna_conc.asNumber(MICROMOLAR_UNITS)
    charged_trna_conc = charged_trna_conc.asNumber(MICROMOLAR_UNITS)
    aa_conc = aa_conc.asNumber(MICROMOLAR_UNITS)
    ribosome_conc = ribosome_conc.asNumber(MICROMOLAR_UNITS)
    unit_conversion = params["unit_conversion"]

    # Remove disabled amino acids from calculations
    n_total_aas = len(aa_conc)
    if use_disabled_aas:
        mask = np.ones(n_total_aas, bool)
    else:
        mask = params["charging_mask"]
    synthetase_conc = synthetase_conc[mask]
    original_uncharged_trna_conc = uncharged_trna_conc[mask]
    original_charged_trna_conc = charged_trna_conc[mask]
    original_aa_conc = aa_conc[mask]
    f = f[mask]

    n_aas = len(aa_conc)
    n_aas_masked = len(original_aa_conc)

    # Limits for integration
    aa_rate_limit = original_aa_conc / time_limit
    trna_rate_limit = original_charged_trna_conc / time_limit
    v_rib_max = max(0, ((aa_rate_limit + trna_rate_limit) / f).min())

    # Integrate rates of charging and elongation
    c_init = np.hstack((
        original_uncharged_trna_conc,
        original_charged_trna_conc,
        aa_conc,
        np.zeros(n_aas),
        np.zeros(n_aas),
        np.zeros(n_aas),
    ))
    sol = solve_ivp(dcdt, [0, time_limit], c_init, method="BDF")
    c_sol = sol.y.T

    # Determine new values from integration results
    final_uncharged_trna_conc = c_sol[-1, :n_aas_masked]
    final_charged_trna_conc = c_sol[-1, n_aas_masked : 2 * n_aas_masked]
    total_synthesis = c_sol[-1, 2 * n_aas_masked + n_aas : 2 * n_aas_masked + 2 * n_aas]
    total_import = c_sol[-1, 2 * n_aas_masked + 2 * n_aas : 2 * n_aas_masked + 3 * n_aas]
    total_export = c_sol[-1, 2 * n_aas_masked + 3 * n_aas : 2 * n_aas_masked + 4 * n_aas]

    negative_check(final_uncharged_trna_conc, final_charged_trna_conc)
    negative_check(final_charged_trna_conc, final_uncharged_trna_conc)

    fraction_charged = final_charged_trna_conc / (final_uncharged_trna_conc + final_charged_trna_conc)
    numerator_ribosome = 1 + np.sum(
        f
        * (
            params["krta"] / final_charged_trna_conc
            + final_uncharged_trna_conc / final_charged_trna_conc * params["krta"] / params["krtf"]
        )
    )
    v_rib = params["max_elong_rate"] * ribosome_conc / numerator_ribosome
    if limit_v_rib:
        v_rib_max = max(
            0,
            ((original_aa_conc + (original_charged_trna_conc - final_charged_trna_conc)) / time_limit / f).min(),
        )
        v_rib = min(v_rib, v_rib_max)

    # Replace SEL fraction charged with average
    new_fraction_charged = np.zeros(n_total_aas)
    new_fraction_charged[mask] = fraction_charged
    new_fraction_charged[~mask] = fraction_charged.mean()

    return new_fraction_charged, v_rib, total_synthesis, total_import, total_export


@njit(error_model="numpy")
def dcdt_jit(
    t,
    c,
    n_aas_masked,
    n_aas,
    mask,
    kS,
    synthetase_conc,
    KMaa,
    KMtf,
    f,
    krta,
    krtf,
    max_elong_rate,
    ribosome_conc,
    limit_v_rib,
    aa_rate_limit,
    v_rib_max,
):
    uncharged_trna_conc = c[:n_aas_masked]
    charged_trna_conc = c[n_aas_masked : 2 * n_aas_masked]
    aa_conc = c[2 * n_aas_masked : 2 * n_aas_masked + n_aas]
    masked_aa_conc = aa_conc[mask]

    v_charging = (
        kS
        * synthetase_conc
        * uncharged_trna_conc
        * masked_aa_conc
        / (KMaa[mask] * KMtf[mask])
        / (
            1
            + uncharged_trna_conc / KMtf[mask]
            + masked_aa_conc / KMaa[mask]
            + uncharged_trna_conc * masked_aa_conc / KMtf[mask] / KMaa[mask]
        )
    )
    numerator_ribosome = 1 + np.sum(
        f * (krta / charged_trna_conc + uncharged_trna_conc / charged_trna_conc * krta / krtf)
    )
    v_rib = max_elong_rate * ribosome_conc / numerator_ribosome

    # Handle case when f is 0 and charged_trna_conc is 0
    if not np.isfinite(v_rib):
        v_rib = 0

    # Limit v_rib and v_charging to the amount of available amino acids
    if limit_v_rib:
        v_charging = np.fmin(v_charging, aa_rate_limit)
        v_rib = min(v_rib, v_rib_max)

    dtrna = v_charging - v_rib * f
    daa = np.zeros(n_aas)

    return v_charging, dtrna, daa


def get_charging_supply_function(
    supply_in_charging: bool,
    mechanistic_supply: bool,
    mechanistic_aa_transport: bool,
    amino_acid_synthesis: Callable,
    amino_acid_import: Callable,
    amino_acid_export: Callable,
    aa_supply_scaling: Callable,
    counts_to_molar: Unum,
    aa_supply: npt.NDArray[np.float64],
    fwd_enzyme_counts: npt.NDArray[np.int64],
    rev_enzyme_counts: npt.NDArray[np.int64],
    dry_mass: Unum,
    importer_counts: npt.NDArray[np.int64],
    exporter_counts: npt.NDArray[np.int64],
    aa_in_media: npt.NDArray[np.bool_],
) -> Optional[Callable[[npt.NDArray[np.float64]], Tuple[Unum, Unum, Unum]]]:
    """
    Get a function mapping internal amino acid concentrations to the amount of
    amino acid supply expected.

    Args:
        supply_in_charging: True if using aa_supply_in_charging option
        mechanistic_supply: True if using mechanistic_translation_supply option
        mechanistic_aa_transport: True if using mechanistic_aa_transport option
        amino_acid_synthesis: function to provide rates of synthesis for amino
            acids based on the internal state
        amino_acid_import: function to provide import rates for amino
            acids based on the internal and external state
        amino_acid_export: function to provide export rates for amino
            acids based on the internal state
        aa_supply_scaling: function to scale the amino acid supply based
            on the internal state
        counts_to_molar: conversion factor for counts to molar
            (:py:data:`~ecoli.processes.polypeptide_elongation.MICROMOLAR_UNITS`)
        aa_supply: rate of amino acid supply expected
        fwd_enzyme_counts: enzyme counts in forward reactions for each amino acid
        rev_enzyme_counts: enzyme counts in loss reactions for each amino acid
        dry_mass: dry mass of the cell with mass units
        importer_counts: counts for amino acid importers
        exporter_counts: counts for amino acid exporters
        aa_in_media: True for each amino acid that is present in the media
    Returns:
        Function that provides the amount of supply (synthesis, import, export)
        for each amino acid based on the internal state of the cell
    """

    # Create functions that are only dependent on amino acid concentrations for more stable
    # charging and amino acid concentrations.  If supply_in_charging is not set, then
    # setting None will maintain constant amino acid concentrations throughout charging.
    supply_function = None
    if supply_in_charging:
        counts_to_molar = counts_to_molar.asNumber(MICROMOLAR_UNITS)
        zeros = counts_to_molar * np.zeros_like(aa_supply)
        if mechanistic_supply:
            if mechanistic_aa_transport:

                def supply_function(aa_conc):
                    return (
                        counts_to_molar * amino_acid_synthesis(fwd_enzyme_counts, rev_enzyme_counts, aa_conc)[0],
                        counts_to_molar
                        * amino_acid_import(
                            aa_in_media,
                            dry_mass,
                            aa_conc,
                            importer_counts,
                            mechanistic_aa_transport,
                        ),
                        counts_to_molar * amino_acid_export(exporter_counts, aa_conc, mechanistic_aa_transport),
                    )

            else:

                def supply_function(aa_conc):
                    return (
                        counts_to_molar * amino_acid_synthesis(fwd_enzyme_counts, rev_enzyme_counts, aa_conc)[0],
                        counts_to_molar
                        * amino_acid_import(
                            aa_in_media,
                            dry_mass,
                            aa_conc,
                            importer_counts,
                            mechanistic_aa_transport,
                        ),
                        zeros,
                    )

        else:

            def supply_function(aa_conc):
                return (
                    counts_to_molar * aa_supply * aa_supply_scaling(aa_conc, aa_in_media),
                    zeros,
                    zeros,
                )

    return supply_function


def test_polypeptide_elongation(return_data=False):
    def make_elongation_rates(random, base, time_step, variable_elongation=False):
        size = 1
        lengths = time_step * np.full(size, base, dtype=np.int64)
        lengths = stochasticRound(random, lengths) if random else np.round(lengths)
        return lengths.astype(np.int64)

    test_config = {
        "time_step": 2,
        "proteinIds": np.array(["TRYPSYN-APROTEIN[c]"]),
        "ribosome30S": "CPLX0-3953[c]",
        "ribosome50S": "CPLX0-3962[c]",
        "make_elongation_rates": make_elongation_rates,
        "proteinLengths": np.array([245]),  # this is the length of proteins in proteinSequences
        "translation_aa_supply": {
            "minimal": (units.mol / units.fg / units.min)
            * np.array([
                6.73304301e-21,
                3.63835219e-21,
                2.89772671e-21,
                3.88086822e-21,
                5.04645651e-22,
                4.45295877e-21,
                2.64600664e-21,
                5.35711230e-21,
                1.26817689e-21,
                3.81168405e-21,
                5.66834531e-21,
                4.30576056e-21,
                1.70428208e-21,
                2.24878356e-21,
                2.49335033e-21,
                3.47019761e-21,
                3.83858460e-21,
                6.34564026e-22,
                1.86880523e-21,
                1.40959498e-27,
                5.20884460e-21,
            ])
        },
        "proteinSequences": np.array([
            [
                12,
                10,
                18,
                9,
                13,
                1,
                10,
                9,
                9,
                16,
                20,
                9,
                18,
                15,
                9,
                10,
                20,
                4,
                20,
                13,
                7,
                15,
                9,
                18,
                4,
                10,
                13,
                15,
                14,
                1,
                2,
                14,
                11,
                8,
                20,
                0,
                16,
                13,
                7,
                8,
                12,
                13,
                7,
                1,
                10,
                0,
                14,
                10,
                13,
                7,
                10,
                11,
                20,
                5,
                4,
                1,
                11,
                14,
                16,
                3,
                0,
                5,
                15,
                18,
                7,
                2,
                0,
                9,
                18,
                9,
                0,
                2,
                8,
                6,
                2,
                2,
                18,
                3,
                12,
                20,
                16,
                0,
                15,
                2,
                9,
                20,
                6,
                14,
                14,
                16,
                20,
                16,
                20,
                7,
                11,
                11,
                15,
                10,
                10,
                17,
                9,
                14,
                13,
                13,
                7,
                6,
                10,
                18,
                17,
                10,
                16,
                7,
                2,
                10,
                10,
                9,
                3,
                1,
                2,
                2,
                1,
                16,
                11,
                0,
                8,
                7,
                16,
                9,
                0,
                5,
                20,
                20,
                2,
                8,
                13,
                11,
                11,
                1,
                1,
                9,
                15,
                9,
                17,
                12,
                13,
                14,
                5,
                7,
                16,
                1,
                15,
                1,
                7,
                1,
                7,
                10,
                10,
                14,
                13,
                11,
                16,
                7,
                0,
                13,
                8,
                0,
                0,
                9,
                0,
                0,
                7,
                20,
                14,
                9,
                9,
                14,
                20,
                4,
                20,
                15,
                16,
                16,
                15,
                2,
                11,
                9,
                2,
                10,
                2,
                1,
                10,
                8,
                2,
                7,
                10,
                20,
                9,
                20,
                5,
                12,
                10,
                14,
                14,
                9,
                3,
                20,
                15,
                6,
                18,
                7,
                11,
                3,
                6,
                20,
                1,
                5,
                10,
                0,
                0,
                8,
                4,
                1,
                15,
                9,
                12,
                5,
                6,
                11,
                9,
                0,
                5,
                10,
                3,
                11,
                5,
                20,
                0,
                5,
                1,
                5,
                0,
                0,
                7,
                11,
                20,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
                -1,
            ]
        ]).astype(np.int8),
    }

    polypep_elong = PolypeptideElongation(test_config)

    initial_state = {
        "environment": {"media_id": "minimal"},
        "bulk": np.array(
            [
                ("CPLX0-3953[c]", 100),
                ("CPLX0-3962[c]", 100),
                ("TRYPSYN-APROTEIN[c]", 0),
                ("RELA", 0),
                ("SPOT", 0),
                ("H2O", 0),
                ("PROTON", 0),
                ("ppGpp", 0),
            ]
            + [(aa, 100) for aa in DEFAULT_AA_NAMES],
            dtype=[("id", "U40"), ("count", int)],
        ),
        "unique": {
            "active_ribosome": np.array(
                [(1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
                dtype=[
                    ("_entryState", np.bool_),
                    ("unique_index", int),
                    ("protein_index", int),
                    ("peptide_length", int),
                    ("pos_on_mRNA", int),
                    ("massDiff_DNA", "<f8"),
                    ("massDiff_mRNA", "<f8"),
                    ("massDiff_metabolite", "<f8"),
                    ("massDiff_miscRNA", "<f8"),
                    ("massDiff_nonspecific_RNA", "<f8"),
                    ("massDiff_protein", "<f8"),
                    ("massDiff_rRNA", "<f8"),
                    ("massDiff_tRNA", "<f8"),
                    ("massDiff_water", "<f8"),
                ],
            )
        },
        "listeners": {"mass": {"dry_mass": 350.0}},
    }

    settings = {"total_time": 200, "initial_state": initial_state, "topology": TOPOLOGY}
    data = simulate_process(polypep_elong, settings)

    if return_data:
        return data, test_config


def run_plot(data, config):
    # plot a list of variables
    bulk_ids = [
        "CPLX0-3953[c]",
        "CPLX0-3962[c]",
        "TRYPSYN-APROTEIN[c]",
        "RELA",
        "SPOT",
        "H2O",
        "PROTON",
        "ppGpp",
    ] + [aa for aa in DEFAULT_AA_NAMES]
    variables = [(bulk_id,) for bulk_id in bulk_ids]

    # format data
    bulk_timeseries = np.array(data["bulk"])
    for i, bulk_id in enumerate(bulk_ids):
        data[bulk_id] = bulk_timeseries[:, i]

    plot_variables(
        data,
        variables=variables,
        out_dir="out/processes/polypeptide_elongation",
        filename="variables",
    )


"""
Functions to initialize molecule states from sim_data.
"""

import numpy as np
import numpy.typing as npt
from numpy.lib import recfunctions as rfn
from typing import Any
from unum import Unum

from sms_api.notebook.schema import (
    attrs,
    bulk_name_to_idx,
    counts,
    MetadataArray,
)
from sms_api.notebook.wholecell.utils import units
from sms_api.notebook.wholecell.utils.fitting import (
    countsFromMassAndExpression,
    masses_and_counts_for_homeostatic_target,
    normalize,
)

try:
    from sms_api.notebook.wholecell.utils.mc_complexation import mccFormComplexesWithPrebuiltMatrices
except ImportError as exc:
    raise RuntimeError("Failed to import Cython module. Try running 'make clean compile'.") from exc
from sms_api.notebook.wholecell.utils.polymerize import computeMassIncrease
from sms_api.notebook.wholecell.utils.random import stochasticRound

RAND_MAX = 2**31


def create_bulk_container(
    sim_data,
    n_seeds=1,
    condition=None,
    seed=0,
    ppgpp_regulation=True,
    trna_attenuation=True,
    mass_coeff=1,
    form_complexes=True,
):
    try:
        old_condition = sim_data.condition
        if condition is not None:
            sim_data.condition = condition
        media_id = sim_data.conditions[sim_data.condition]["nutrients"]
        exchange_data = sim_data.external_state.exchange_data_from_media(media_id)
        import_molecules = set(exchange_data["importUnconstrainedExchangeMolecules"]) | set(
            exchange_data["importConstrainedExchangeMolecules"]
        )

        random_state = np.random.RandomState(seed=seed)

        # Construct bulk container
        ids_molecules = sim_data.internal_state.bulk_molecules.bulk_data["id"]
        average_container = np.array(
            [mol_data for mol_data in zip(ids_molecules, np.zeros(len(ids_molecules)))],
            dtype=[("id", ids_molecules.dtype), ("count", np.float64)],
        )

        for n in range(n_seeds):
            random_state = np.random.RandomState(seed=seed + n)
            average_container["count"] += initialize_bulk_counts(
                sim_data,
                media_id,
                import_molecules,
                random_state,
                mass_coeff,
                ppgpp_regulation,
                trna_attenuation,
                form_complexes=form_complexes,
            )["count"]
    except Exception:
        raise RuntimeError(
            "sim_data might not be fully initialized. "
            "Make sure all attributes have been set before "
            "using this function."
        )

    sim_data.condition = old_condition
    average_container["count"] = average_container["count"] / n_seeds
    return average_container


def initialize_bulk_counts(
    sim_data,
    media_id,
    import_molecules,
    random_state,
    mass_coeff,
    ppgpp_regulation,
    trna_attenuation,
    form_complexes=True,
):
    # Allocate count array to populate
    bulk_counts = np.zeros(len(sim_data.internal_state.bulk_molecules.bulk_data["id"]), dtype=int)

    # Set protein counts from expression
    initialize_protein_monomers(
        bulk_counts,
        sim_data,
        random_state,
        mass_coeff,
        ppgpp_regulation,
        trna_attenuation,
    )

    # Set RNA counts from expression
    initialize_rna(
        bulk_counts,
        sim_data,
        random_state,
        mass_coeff,
        ppgpp_regulation,
        trna_attenuation,
    )

    # Set mature RNA counts
    initialize_mature_RNA(bulk_counts, sim_data)

    # Set other biomass components
    set_small_molecule_counts(bulk_counts, sim_data, media_id, import_molecules, mass_coeff)

    # Form complexes
    if form_complexes:
        initialize_complexation(bulk_counts, sim_data, random_state)

    bulk_masses = sim_data.internal_state.bulk_molecules.bulk_data["mass"].asNumber(
        units.fg / units.mol
    ) / sim_data.constants.n_avogadro.asNumber(1 / units.mol)
    bulk_submasses = []
    bulk_submass_dtypes = []
    for submass, idx in sim_data.submass_name_to_index.items():
        bulk_submasses.append(bulk_masses[:, idx])
        bulk_submass_dtypes.append((f"{submass}_submass", np.float64))
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data.struct_array["id"]
    bulk_array = np.array(
        [mol_data for mol_data in zip(bulk_ids, bulk_counts, *bulk_submasses)],
        dtype=[("id", bulk_ids.dtype), ("count", int)] + bulk_submass_dtypes,
    )

    return bulk_array


def initialize_unique_molecules(
    bulk_state,
    sim_data,
    cell_mass,
    random_state,
    unique_id_rng,
    superhelical_density,
    ppgpp_regulation,
    trna_attenuation,
    mechanistic_replisome,
):
    unique_molecules = {}

    # Initialize counts of full chromosomes
    initialize_full_chromosome(unique_molecules, sim_data, unique_id_rng)

    # Initialize unique molecules relevant to replication
    initialize_replication(
        bulk_state,
        unique_molecules,
        sim_data,
        cell_mass,
        mechanistic_replisome,
        unique_id_rng,
    )

    # Initialize bound transcription factors
    initialize_transcription_factors(bulk_state, unique_molecules, sim_data, random_state)

    # Initialize active RNAPs and unique molecule representations of RNAs
    initialize_transcription(
        bulk_state,
        unique_molecules,
        sim_data,
        random_state,
        unique_id_rng,
        ppgpp_regulation,
        trna_attenuation,
    )

    # Initialize linking numbers of chromosomal segments
    if superhelical_density:
        initialize_chromosomal_segments(unique_molecules, sim_data, unique_id_rng)
    else:
        unique_molecules["chromosomal_segment"] = create_new_unique_molecules(
            "chromosomal_segment", 0, sim_data, unique_id_rng
        )

    # Initialize active ribosomes
    initialize_translation(bulk_state, unique_molecules, sim_data, random_state, unique_id_rng)

    return unique_molecules


def create_new_unique_molecules(name, n_mols, sim_data, random_state, **attrs):
    """
    Helper function to create a new Numpy structured array with n_mols
    instances of the unique molecule called name. Accepts keyword arguments
    that become initial values for specified attributes of the new molecules.
    """
    dtypes = list(sim_data.internal_state.unique_molecule.unique_molecule_definitions[name].items())
    submasses = list(sim_data.submass_name_to_index)
    dtypes += [(f"massDiff_{submass}", "<f8") for submass in submasses]
    dtypes += [("_entryState", "i1"), ("unique_index", "<i8")]
    unique_mols = np.zeros(n_mols, dtype=dtypes)
    for attr_name, attr_value in attrs.items():
        unique_mols[attr_name] = attr_value
    # Each unique molecule has unique prefix for indices to prevent conflicts
    unique_mol_names = list(sim_data.internal_state.unique_molecule.unique_molecule_definitions.keys())
    unique_prefix = unique_mol_names.index(name) << 59
    unique_mols["unique_index"] = np.arange(unique_prefix, unique_prefix + n_mols)
    unique_mols["_entryState"] = 1
    unique_mols = MetadataArray(unique_mols, unique_prefix + n_mols)
    return unique_mols


def initialize_protein_monomers(bulk_counts, sim_data, random_state, mass_coeff, ppgpp_regulation, trna_attenuation):
    monomer_mass = (
        mass_coeff
        * sim_data.mass.get_component_masses(sim_data.condition_to_doubling_time[sim_data.condition])["proteinMass"]
        / sim_data.mass.avg_cell_to_initial_cell_conversion_factor
    )
    # TODO: unify this logic with the parca so it doesn]t fall out of step
    # again (look at teh calProteinCounts function)

    transcription = sim_data.process.transcription
    if ppgpp_regulation:
        rna_expression = sim_data.calculate_ppgpp_expression(sim_data.condition)
    else:
        rna_expression = transcription.rna_expression[sim_data.condition]

    if trna_attenuation:
        # Need to adjust expression (calculated without attenuation) by basal_adjustment
        # to get the expected expression without any attenuation and then multiply
        # by the condition readthrough probability to get the condition specific expression
        readthrough = transcription.attenuation_readthrough[sim_data.condition]
        basal_adjustment = transcription.attenuation_readthrough["basal"]
        rna_expression[transcription.attenuated_rna_indices] *= readthrough / basal_adjustment

    monomer_expression = normalize(
        sim_data.process.transcription.cistron_tu_mapping_matrix.dot(rna_expression)[
            sim_data.relation.cistron_to_monomer_mapping
        ]
        * sim_data.process.translation.translation_efficiencies_by_monomer
        / (
            np.log(2) / sim_data.condition_to_doubling_time[sim_data.condition].asNumber(units.s)
            + sim_data.process.translation.monomer_data["deg_rate"].asNumber(1 / units.s)
        )
    )

    n_monomers = countsFromMassAndExpression(
        monomer_mass.asNumber(units.g),
        sim_data.process.translation.monomer_data["mw"].asNumber(units.g / units.mol),
        monomer_expression,
        sim_data.constants.n_avogadro.asNumber(1 / units.mol),
    )

    # Get indices for monomers in bulk counts array
    monomer_ids = sim_data.process.translation.monomer_data["id"]
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"]
    monomer_idx = bulk_name_to_idx(monomer_ids, bulk_ids)
    # Calculate initial counts of each monomer from mutinomial distribution
    bulk_counts[monomer_idx] = random_state.multinomial(n_monomers, monomer_expression)


def initialize_rna(bulk_counts, sim_data, random_state, mass_coeff, ppgpp_regulation, trna_attenuation):
    """
    Initializes counts of RNAs in the bulk molecule container using RNA
    expression data. mRNA counts are also initialized here, but is later reset
    to zero when the representations for mRNAs are moved to the unique molecule
    container.
    """

    transcription = sim_data.process.transcription

    rna_mass = (
        mass_coeff
        * sim_data.mass.get_component_masses(sim_data.condition_to_doubling_time[sim_data.condition])["rnaMass"]
        / sim_data.mass.avg_cell_to_initial_cell_conversion_factor
    )

    if ppgpp_regulation:
        rna_expression = sim_data.calculate_ppgpp_expression(sim_data.condition)
    else:
        rna_expression = normalize(transcription.rna_expression[sim_data.condition])

    if trna_attenuation:
        # Need to adjust expression (calculated without attenuation) by basal_adjustment
        # to get the expected expression without any attenuation and then multiply
        # by the condition readthrough probability to get the condition specific expression
        readthrough = transcription.attenuation_readthrough[sim_data.condition]
        basal_adjustment = transcription.attenuation_readthrough["basal"]
        rna_expression[transcription.attenuated_rna_indices] *= readthrough / basal_adjustment
        rna_expression /= rna_expression.sum()

    n_rnas = countsFromMassAndExpression(
        rna_mass.asNumber(units.g),
        transcription.rna_data["mw"].asNumber(units.g / units.mol),
        rna_expression,
        sim_data.constants.n_avogadro.asNumber(1 / units.mol),
    )

    # Get indices for monomers in bulk counts array
    rna_ids = transcription.rna_data["id"]
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"]
    rna_idx = bulk_name_to_idx(rna_ids, bulk_ids)
    # Calculate initial counts of each RNA from mutinomial distribution
    bulk_counts[rna_idx] = random_state.multinomial(n_rnas, rna_expression)


def initialize_mature_RNA(bulk_counts, sim_data):
    """
    Initializes counts of mature RNAs in the bulk molecule container using the
    counts of unprocessed RNAs. Also consolidates the different variants of each
    rRNA molecule into the main type.
    """
    transcription = sim_data.process.transcription
    rna_data = transcription.rna_data
    unprocessed_rna_ids = rna_data["id"][rna_data["is_unprocessed"]]
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"]
    unprocessed_rna_idx = bulk_name_to_idx(unprocessed_rna_ids, bulk_ids)

    # Skip if there are no unprocessed RNAs represented
    if len(unprocessed_rna_ids) > 0:
        mature_rna_ids = transcription.mature_rna_data["id"]
        maturation_stoich_matrix = transcription.rna_maturation_stoich_matrix
        mature_rna_idx = bulk_name_to_idx(mature_rna_ids, bulk_ids)

        # Get counts of unprocessed RNAs
        unprocessed_rna_counts = bulk_counts[unprocessed_rna_idx]

        # Assume all unprocessed RNAs are converted to mature RNAs
        bulk_counts[unprocessed_rna_idx] = 0
        bulk_counts[mature_rna_idx] += maturation_stoich_matrix.dot(unprocessed_rna_counts)

    # Get IDs of rRNAs
    main_23s_rRNA_id = sim_data.molecule_groups.s50_23s_rRNA[0]
    main_16s_rRNA_id = sim_data.molecule_groups.s30_16s_rRNA[0]
    main_5s_rRNA_id = sim_data.molecule_groups.s50_5s_rRNA[0]
    variant_23s_rRNA_ids = sim_data.molecule_groups.s50_23s_rRNA[1:]
    variant_16s_rRNA_ids = sim_data.molecule_groups.s30_16s_rRNA[1:]
    variant_5s_rRNA_ids = sim_data.molecule_groups.s50_5s_rRNA[1:]

    # Get indices of main and variant rRNAs
    main_23s_rRNA_idx = bulk_name_to_idx(main_23s_rRNA_id, bulk_ids)
    main_16s_rRNA_idx = bulk_name_to_idx(main_16s_rRNA_id, bulk_ids)
    main_5s_rRNA_idx = bulk_name_to_idx(main_5s_rRNA_id, bulk_ids)
    variant_23s_rRNA_idx = bulk_name_to_idx(variant_23s_rRNA_ids, bulk_ids)
    variant_16s_rRNA_idx = bulk_name_to_idx(variant_16s_rRNA_ids, bulk_ids)
    variant_5s_rRNA_idx = bulk_name_to_idx(variant_5s_rRNA_ids, bulk_ids)

    # Evolve states
    bulk_counts[main_23s_rRNA_idx] += bulk_counts[variant_23s_rRNA_idx].sum()
    bulk_counts[main_16s_rRNA_idx] += bulk_counts[variant_16s_rRNA_idx].sum()
    bulk_counts[main_5s_rRNA_idx] += bulk_counts[variant_5s_rRNA_idx].sum()
    bulk_counts[variant_23s_rRNA_idx] -= bulk_counts[variant_23s_rRNA_idx]
    bulk_counts[variant_16s_rRNA_idx] -= bulk_counts[variant_16s_rRNA_idx]
    bulk_counts[variant_5s_rRNA_idx] -= bulk_counts[variant_5s_rRNA_idx]


# TODO: remove checks for zero concentrations (change to assertion)
# TODO: move any rescaling logic to KB/fitting
def set_small_molecule_counts(bulk_counts, sim_data, media_id, import_molecules, mass_coeff, cell_mass=None):
    doubling_time = sim_data.condition_to_doubling_time[sim_data.condition]

    conc_dict = sim_data.process.metabolism.concentration_updates.concentrations_based_on_nutrients(
        media_id=media_id, imports=import_molecules
    )
    conc_dict.update(sim_data.mass.getBiomassAsConcentrations(doubling_time))
    conc_dict[sim_data.molecule_ids.ppGpp] = sim_data.growth_rate_parameters.get_ppGpp_conc(doubling_time)
    molecule_ids = sorted(conc_dict)
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"]
    molecule_concentrations = (units.mol / units.L) * np.array([
        conc_dict[key].asNumber(units.mol / units.L) for key in molecule_ids
    ])

    if cell_mass is None:
        avg_cell_fraction_mass = sim_data.mass.get_component_masses(doubling_time)
        other_dry_mass = (
            mass_coeff
            * (
                avg_cell_fraction_mass["proteinMass"]
                + avg_cell_fraction_mass["rnaMass"]
                + avg_cell_fraction_mass["dnaMass"]
            )
            / sim_data.mass.avg_cell_to_initial_cell_conversion_factor
        )
    else:
        small_molecule_mass = 0 * units.fg
        for mol in conc_dict:
            mol_idx = bulk_name_to_idx(mol, bulk_ids)
            small_molecule_mass += bulk_counts[mol_idx] * sim_data.getter.get_mass(mol) / sim_data.constants.n_avogadro
        other_dry_mass = cell_mass - small_molecule_mass

    masses_to_add, counts_to_add = masses_and_counts_for_homeostatic_target(
        other_dry_mass,
        molecule_concentrations,
        sim_data.getter.get_masses(molecule_ids),
        sim_data.constants.cell_density,
        sim_data.constants.n_avogadro,
    )

    molecule_idx = bulk_name_to_idx(molecule_ids, bulk_ids)
    bulk_counts[molecule_idx] = counts_to_add


def initialize_complexation(bulk_counts, sim_data, random_state):
    molecule_names = sim_data.process.complexation.molecule_names
    bulk_ids = sim_data.internal_state.bulk_molecules.bulk_data["id"]
    molecule_idx = bulk_name_to_idx(molecule_names, bulk_ids)

    stoich_matrix = sim_data.process.complexation.stoich_matrix().astype(np.int64, order="F")

    molecule_counts = bulk_counts[molecule_idx]
    updated_molecule_counts, complexation_events = mccFormComplexesWithPrebuiltMatrices(
        molecule_counts,
        random_state.randint(1000),
        stoich_matrix,
        *sim_data.process.complexation.prebuilt_matrices,
    )

    bulk_counts[molecule_idx] = updated_molecule_counts

    if np.any(updated_molecule_counts < 0):
        raise ValueError("Negative counts after complexation")


def initialize_full_chromosome(unique_molecules, sim_data, unique_id_rng):
    """
    Initializes the counts of full chromosomes to one. The division_time of
    this initial chromosome is set to be zero for consistency.
    """
    unique_molecules["full_chromosome"] = create_new_unique_molecules(
        "full_chromosome",
        1,
        sim_data,
        unique_id_rng,
        division_time=0.0,
        has_triggered_division=True,
        domain_index=0,
    )


def initialize_replication(
    bulk_state,
    unique_molecules,
    sim_data,
    cell_mass,
    mechanistic_replisome,
    unique_id_rng,
):
    """
    Initializes replication by creating an appropriate number of replication
    forks given the cell growth rate. This also initializes the gene dosage
    bulk counts using the initial locations of the forks.
    """
    # Determine the number and location of replication forks at the start of
    # the cell cycle
    # Get growth rate constants
    tau = sim_data.condition_to_doubling_time[sim_data.condition].asUnit(units.min)
    critical_mass = sim_data.mass.get_dna_critical_mass(tau)
    replication_rate = sim_data.process.replication.basal_elongation_rate

    # Calculate length of replichore
    genome_length = sim_data.process.replication.genome_length
    replichore_length = np.ceil(0.5 * genome_length) * units.nt

    # Calculate the maximum number of replisomes that could be formed with
    # the existing counts of replisome subunits. If mechanistic_replisome option
    # is off, set to an arbitrary high number.
    replisome_trimer_idx = bulk_name_to_idx(sim_data.molecule_groups.replisome_trimer_subunits, bulk_state["id"])
    replisome_monomer_idx = bulk_name_to_idx(sim_data.molecule_groups.replisome_monomer_subunits, bulk_state["id"])
    if mechanistic_replisome:
        n_max_replisomes = np.min(
            np.concatenate((
                bulk_state["count"][replisome_trimer_idx] // 3,
                bulk_state["count"][replisome_monomer_idx],
            ))
        )
    else:
        n_max_replisomes = 1000

    # Generate arrays specifying appropriate initial replication conditions
    oric_state, replisome_state, domain_state = determine_chromosome_state(
        tau,
        replichore_length,
        n_max_replisomes,
        sim_data.process.replication.no_child_place_holder,
        cell_mass,
        critical_mass,
        replication_rate,
    )

    n_oric = oric_state["domain_index"].size
    n_replisome = replisome_state["domain_index"].size
    n_domain = domain_state["domain_index"].size

    # Add OriC molecules with the proposed attributes
    unique_molecules["oriC"] = create_new_unique_molecules(
        "oriC", n_oric, sim_data, unique_id_rng, domain_index=oric_state["domain_index"]
    )

    # Add chromosome domain molecules with the proposed attributes
    unique_molecules["chromosome_domain"] = create_new_unique_molecules(
        "chromosome_domain",
        n_domain,
        sim_data,
        unique_id_rng,
        domain_index=domain_state["domain_index"],
        child_domains=domain_state["child_domains"],
    )

    if n_replisome != 0:
        # Update mass of replisomes if the mechanistic replisome option is set
        if mechanistic_replisome:
            replisome_trimer_subunit_masses = np.vstack([
                sim_data.getter.get_submass_array(x).asNumber(units.fg / units.count)
                for x in sim_data.molecule_groups.replisome_trimer_subunits
            ])
            replisome_monomer_subunit_masses = np.vstack([
                sim_data.getter.get_submass_array(x).asNumber(units.fg / units.count)
                for x in sim_data.molecule_groups.replisome_monomer_subunits
            ])
            replisome_mass_array = 3 * replisome_trimer_subunit_masses.sum(
                axis=0
            ) + replisome_monomer_subunit_masses.sum(axis=0)
            replisome_protein_mass = replisome_mass_array.sum()
        else:
            replisome_protein_mass = 0.0

        # Update mass to account for DNA strands that have already been
        # elongated.
        sequences = sim_data.process.replication.replication_sequences
        fork_coordinates = replisome_state["coordinates"]
        sequence_elongations = np.abs(np.repeat(fork_coordinates, 2))

        mass_increase_dna = computeMassIncrease(
            np.tile(sequences, (n_replisome // 2, 1)),
            sequence_elongations,
            sim_data.process.replication.replication_monomer_weights.asNumber(units.fg),
        )

        # Add active replisomes as unique molecules and set attributes
        unique_molecules["active_replisome"] = create_new_unique_molecules(
            "active_replisome",
            n_replisome,
            sim_data,
            unique_id_rng,
            domain_index=replisome_state["domain_index"],
            coordinates=replisome_state["coordinates"],
            right_replichore=replisome_state["right_replichore"],
            massDiff_DNA=mass_increase_dna[0::2] + mass_increase_dna[1::2],
            massDiff_protein=replisome_protein_mass,
        )

        if mechanistic_replisome:
            # Remove replisome subunits from bulk molecules
            bulk_state["count"][replisome_trimer_idx] -= 3 * n_replisome
            bulk_state["count"][replisome_monomer_idx] -= n_replisome
    else:
        # For n_replisome = 0, still create an empty structured array with
        # the expected fields
        unique_molecules["active_replisome"] = create_new_unique_molecules(
            "active_replisome", n_replisome, sim_data, unique_id_rng
        )

    # Get coordinates of all genes, promoters and DnaA boxes
    all_gene_coordinates = sim_data.process.transcription.cistron_data["replication_coordinate"]
    all_promoter_coordinates = sim_data.process.transcription.rna_data["replication_coordinate"]
    all_DnaA_box_coordinates = sim_data.process.replication.motif_coordinates["DnaA_box"]

    # Define function that initializes attributes of sequence motifs given the
    # initial state of the chromosome
    def get_motif_attributes(all_motif_coordinates):
        """
        Using the initial positions of replication forks, calculate attributes
        of unique molecules representing DNA motifs, given their positions on
        the genome.

        Args:
            all_motif_coordinates (ndarray): Genomic coordinates of DNA motifs,
            represented in a specific order

        Returns:
            motif_index: Indices of all motif copies, in the case where
            different indexes imply a different functional role
            motif_coordinates: Genomic coordinates of all motif copies
            motif_domain_index: Domain indexes of the chromosome domain that
            each motif copy belongs to
        """
        motif_index, motif_coordinates, motif_domain_index = [], [], []

        def in_bounds(coordinates, lb, ub):
            return np.logical_and(coordinates < ub, coordinates > lb)

        # Loop through all chromosome domains
        for domain_idx in domain_state["domain_index"]:
            # If the domain is the mother domain of the initial chromosome,
            if domain_idx == 0:
                if n_replisome == 0:
                    # No replisomes - all motifs should fall in this domain
                    motif_mask = np.ones_like(all_motif_coordinates, dtype=bool)

                else:
                    # Get domain boundaries
                    domain_boundaries = replisome_state["coordinates"][replisome_state["domain_index"] == 0]

                    # Add motifs outside of this boundary
                    motif_mask = np.logical_or(
                        all_motif_coordinates > domain_boundaries.max(),
                        all_motif_coordinates < domain_boundaries.min(),
                    )

            # If the domain contains the origin,
            elif np.isin(domain_idx, oric_state["domain_index"]):
                # Get index of the parent domain
                parent_domain_idx = domain_state["domain_index"][
                    np.where(domain_state["child_domains"] == domain_idx)[0]
                ]

                # Get domain boundaries of the parent domain
                parent_domain_boundaries = replisome_state["coordinates"][
                    replisome_state["domain_index"] == parent_domain_idx
                ]

                # Add motifs inside this boundary
                motif_mask = in_bounds(
                    all_motif_coordinates,
                    parent_domain_boundaries.min(),
                    parent_domain_boundaries.max(),
                )

            # If the domain neither contains the origin nor the terminus,
            else:
                # Get index of the parent domain
                parent_domain_idx = domain_state["domain_index"][
                    np.where(domain_state["child_domains"] == domain_idx)[0]
                ]

                # Get domain boundaries of the parent domain
                parent_domain_boundaries = replisome_state["coordinates"][
                    replisome_state["domain_index"] == parent_domain_idx
                ]

                # Get domain boundaries of this domain
                domain_boundaries = replisome_state["coordinates"][replisome_state["domain_index"] == domain_idx]

                # Add motifs between the boundaries
                motif_mask = np.logical_or(
                    in_bounds(
                        all_motif_coordinates,
                        domain_boundaries.max(),
                        parent_domain_boundaries.max(),
                    ),
                    in_bounds(
                        all_motif_coordinates,
                        parent_domain_boundaries.min(),
                        domain_boundaries.min(),
                    ),
                )

            # Append attributes to existing list
            motif_index.extend(np.nonzero(motif_mask)[0])
            motif_coordinates.extend(all_motif_coordinates[motif_mask])
            motif_domain_index.extend(np.full(motif_mask.sum(), domain_idx))

        return motif_index, motif_coordinates, motif_domain_index

    # Use function to get attributes for promoters and DnaA boxes
    TU_index, promoter_coordinates, promoter_domain_index = get_motif_attributes(all_promoter_coordinates)
    cistron_index, gene_coordinates, gene_domain_index = get_motif_attributes(all_gene_coordinates)
    _, DnaA_box_coordinates, DnaA_box_domain_index = get_motif_attributes(all_DnaA_box_coordinates)

    # Add promoters as unique molecules and set attributes
    # Note: the bound_TF attribute is properly initialized in the function
    # initialize_transcription_factors
    n_promoter = len(TU_index)
    n_tf = len(sim_data.process.transcription_regulation.tf_ids)

    unique_molecules["promoter"] = create_new_unique_molecules(
        "promoter",
        n_promoter,
        sim_data,
        unique_id_rng,
        domain_index=promoter_domain_index,
        coordinates=promoter_coordinates,
        TU_index=TU_index,
        bound_TF=np.zeros((n_promoter, n_tf), dtype=bool),
    )

    # Add genes as unique molecules and set attributes
    n_gene = len(cistron_index)

    unique_molecules["gene"] = create_new_unique_molecules(
        "gene",
        n_gene,
        sim_data,
        unique_id_rng,
        cistron_index=cistron_index,
        coordinates=gene_coordinates,
        domain_index=gene_domain_index,
    )

    # Add DnaA boxes as unique molecules and set attributes
    n_DnaA_box = len(DnaA_box_coordinates)

    unique_molecules["DnaA_box"] = create_new_unique_molecules(
        "DnaA_box",
        n_DnaA_box,
        sim_data,
        unique_id_rng,
        domain_index=DnaA_box_domain_index,
        coordinates=DnaA_box_coordinates,
        DnaA_bound=np.zeros(n_DnaA_box, dtype=bool),
    )


def initialize_transcription_factors(bulk_state, unique_molecules, sim_data, random_state):
    """
    Initialize transcription factors that are bound to the chromosome. For each
    type of transcription factor, this function calculates the total number of
    transcription factors that should be bound to the chromosome using the
    binding probabilities of each transcription factor and the number of
    available promoter sites. The calculated number of transcription factors
    are then distributed randomly to promoters, whose bound_TF attributes and
    submasses are updated correspondingly.
    """
    # Get transcription factor properties from sim_data
    tf_ids = sim_data.process.transcription_regulation.tf_ids
    tf_to_tf_type = sim_data.process.transcription_regulation.tf_to_tf_type
    p_promoter_bound_TF = sim_data.process.transcription_regulation.p_promoter_bound_tf

    # Build dict that maps TFs to transcription units they regulate
    delta_prob = sim_data.process.transcription_regulation.delta_prob
    TF_to_TU_idx = {}

    for i, tf in enumerate(tf_ids):
        TF_to_TU_idx[tf] = delta_prob["deltaI"][delta_prob["deltaJ"] == i]

    # Get views into bulk molecule representations of transcription factors
    active_tf_view = {}
    inactive_tf_view = {}
    active_tf_view_idx = {}
    inactive_tf_view_idx = {}

    for tf in tf_ids:
        tf_idx = bulk_name_to_idx(tf + "[c]", bulk_state["id"])
        active_tf_view[tf] = bulk_state["count"][tf_idx]
        active_tf_view_idx[tf] = tf_idx

        if tf_to_tf_type[tf] == "1CS":
            if tf == sim_data.process.transcription_regulation.active_to_bound[tf]:
                inactive_tf_idx = bulk_name_to_idx(
                    sim_data.process.equilibrium.get_unbound(tf + "[c]"),
                    bulk_state["id"],
                )
                inactive_tf_view[tf] = bulk_state["count"][inactive_tf_idx]
            else:
                inactive_tf_idx = bulk_name_to_idx(
                    sim_data.process.transcription_regulation.active_to_bound[tf] + "[c]",
                    bulk_state["id"],
                )
                inactive_tf_view[tf] = bulk_state["count"][inactive_tf_idx]
        elif tf_to_tf_type[tf] == "2CS":
            inactive_tf_idx = bulk_name_to_idx(
                sim_data.process.two_component_system.active_to_inactive_tf[tf + "[c]"],
                bulk_state["id"],
            )
            inactive_tf_view[tf] = bulk_state["count"][inactive_tf_idx]
        inactive_tf_view_idx[tf] = inactive_tf_idx

    # Get masses of active transcription factors
    tf_indexes = [np.where(bulk_state["id"] == tf_id + "[c]")[0][0] for tf_id in tf_ids]
    active_tf_masses = (
        sim_data.internal_state.bulk_molecules.bulk_data["mass"][tf_indexes] / sim_data.constants.n_avogadro
    ).asNumber(units.fg)

    # Get TU indices of promoters
    TU_index = unique_molecules["promoter"]["TU_index"]

    # Initialize bound_TF array
    bound_TF = np.zeros((len(TU_index), len(tf_ids)), dtype=bool)

    for tf_idx, tf_id in enumerate(tf_ids):
        # Get counts of transcription factors
        active_tf_counts = active_tf_view[tf_id]

        # If there are no active transcription factors at initialization,
        # continue to the next transcription factor
        if active_tf_counts == 0:
            continue

        # Compute probability of binding the promoter
        if tf_to_tf_type[tf_id] == "0CS":
            p_promoter_bound = 1.0
        else:
            inactive_tf_counts = inactive_tf_view[tf_id]
            p_promoter_bound = p_promoter_bound_TF(active_tf_counts, inactive_tf_counts)

        # Determine the number of available promoter sites
        available_promoters = np.isin(TU_index, TF_to_TU_idx[tf_id])
        n_available_promoters = available_promoters.sum()

        # Calculate the number of promoters that should be bound
        n_to_bind = int(stochasticRound(random_state, np.full(n_available_promoters, p_promoter_bound)).sum())

        bound_locs = np.zeros(n_available_promoters, dtype=bool)
        if n_to_bind > 0:
            # Determine randomly which DNA targets to bind based on which of
            # the following is more limiting:
            # number of promoter sites to bind, or number of active
            # transcription factors
            bound_locs[
                random_state.choice(
                    n_available_promoters,
                    size=min(n_to_bind, active_tf_view[tf_id]),
                    replace=False,
                )
            ] = True

            # Update count of free transcription factors
            bulk_state["count"][active_tf_view_idx[tf_id]] -= bound_locs.sum()

            # Update bound_TF array
            bound_TF[available_promoters, tf_idx] = bound_locs

    # Calculate masses of bound TFs
    mass_diffs = bound_TF.dot(active_tf_masses)

    # Reset bound_TF attribute of promoters
    unique_molecules["promoter"]["bound_TF"] = bound_TF

    # Add mass_diffs array to promoter submass
    for submass, i in sim_data.submass_name_to_index.items():
        unique_molecules["promoter"][f"massDiff_{submass}"] = mass_diffs[:, i]


def initialize_transcription(
    bulk_state,
    unique_molecules,
    sim_data,
    random_state,
    unique_id_rng,
    ppgpp_regulation,
    trna_attenuation,
):
    """
    Activate RNA polymerases as unique molecules, and distribute them along
    lengths of trancription units, while decreasing counts of unactivated RNA
    polymerases (APORNAP-CPLX[c]). Also initialize unique molecule
    representations of fully transcribed mRNAs and partially transcribed RNAs,
    using counts of mRNAs initialized as bulk molecules, and the attributes of
    initialized RNA polymerases. The counts of full mRNAs represented as bulk
    molecules are reset to zero.

    RNA polymerases are placed randomly across the length of each transcription
    unit, with the synthesis probabilities for each TU determining the number of
    RNA polymerases placed at each gene.
    """
    # Load parameters
    rna_lengths = sim_data.process.transcription.rna_data["length"].asNumber()
    rna_masses = (sim_data.process.transcription.rna_data["mw"] / sim_data.constants.n_avogadro).asNumber(units.fg)
    current_media_id = sim_data.conditions[sim_data.condition]["nutrients"]
    frac_active_rnap = sim_data.process.transcription.rnapFractionActiveDict[current_media_id]
    inactive_rnap_idx = bulk_name_to_idx(sim_data.molecule_ids.full_RNAP, bulk_state["id"])
    inactive_RNAP_counts = bulk_state["count"][inactive_rnap_idx]
    rna_sequences = sim_data.process.transcription.transcription_sequences
    nt_weights = sim_data.process.transcription.transcription_monomer_weights
    end_weight = sim_data.process.transcription.transcription_end_weight
    replichore_lengths = sim_data.process.replication.replichore_lengths
    chromosome_length = replichore_lengths.sum()

    # Number of rnaPoly to activate
    n_RNAPs_to_activate = np.int64(frac_active_rnap * inactive_RNAP_counts)

    # Get attributes of promoters
    TU_index, bound_TF, domain_index_promoters = attrs(
        unique_molecules["promoter"], ["TU_index", "bound_TF", "domain_index"]
    )

    # Parameters for rnaSynthProb
    if ppgpp_regulation:
        doubling_time = sim_data.condition_to_doubling_time[sim_data.condition]
        ppgpp_conc = sim_data.growth_rate_parameters.get_ppGpp_conc(doubling_time)
        basal_prob, _ = sim_data.process.transcription.synth_prob_from_ppgpp(
            ppgpp_conc, sim_data.process.replication.get_average_copy_number
        )
        ppgpp_scale = basal_prob[TU_index]
        # Use original delta prob if no ppGpp basal prob
        ppgpp_scale[ppgpp_scale == 0] = 1
    else:
        basal_prob = sim_data.process.transcription_regulation.basal_prob.copy()
        ppgpp_scale = 1

    if trna_attenuation:
        basal_prob[sim_data.process.transcription.attenuated_rna_indices] += (
            sim_data.process.transcription.attenuation_basal_prob_adjustments
        )
    n_TUs = len(basal_prob)
    delta_prob_matrix = sim_data.process.transcription_regulation.get_delta_prob_matrix(
        dense=True, ppgpp=ppgpp_regulation
    )

    # Synthesis probabilities for different categories of genes
    rna_synth_prob_fractions = sim_data.process.transcription.rnaSynthProbFraction
    rna_synth_prob_R_protein = sim_data.process.transcription.rnaSynthProbRProtein
    rna_synth_prob_rna_polymerase = sim_data.process.transcription.rnaSynthProbRnaPolymerase

    # Get coordinates and transcription directions of transcription units
    replication_coordinate = sim_data.process.transcription.rna_data["replication_coordinate"]
    transcription_direction = sim_data.process.transcription.rna_data["is_forward"]

    # Determine changes from genetic perturbations
    genetic_perturbations = {}
    perturbations = getattr(sim_data, "genetic_perturbations", {})

    if len(perturbations) > 0:
        probability_indexes = [
            (index, sim_data.genetic_perturbations[rna_data["id"]])
            for index, rna_data in enumerate(sim_data.process.transcription.rna_data)
            if rna_data["id"] in sim_data.genetic_perturbations
        ]

        genetic_perturbations = {
            "fixedRnaIdxs": [pair[0] for pair in probability_indexes],
            "fixedSynthProbs": [pair[1] for pair in probability_indexes],
        }

    # ID Groups
    idx_rRNA = np.where(sim_data.process.transcription.rna_data["is_rRNA"])[0]
    idx_mRNA = np.where(sim_data.process.transcription.rna_data["is_mRNA"])[0]
    idx_tRNA = np.where(sim_data.process.transcription.rna_data["is_tRNA"])[0]
    idx_rprotein = np.where(sim_data.process.transcription.rna_data["includes_ribosomal_protein"])[0]
    idx_rnap = np.where(sim_data.process.transcription.rna_data["includes_RNAP"])[0]

    # Calculate probabilities of the RNAP binding to the promoters
    promoter_init_probs = basal_prob[TU_index] + ppgpp_scale * np.multiply(
        delta_prob_matrix[TU_index, :], bound_TF
    ).sum(axis=1)

    if len(genetic_perturbations) > 0:
        rescale_initiation_probs(
            promoter_init_probs,
            TU_index,
            genetic_perturbations["fixedSynthProbs"],
            genetic_perturbations["fixedRnaIdxs"],
        )

    # Adjust probabilities to not be negative
    promoter_init_probs[promoter_init_probs < 0] = 0.0
    promoter_init_probs /= promoter_init_probs.sum()
    if np.any(promoter_init_probs < 0):
        raise Exception("Have negative RNA synthesis probabilities")

    # Adjust synthesis probabilities depending on environment
    synth_prob_fractions = rna_synth_prob_fractions[current_media_id]

    # Create masks for different types of RNAs
    is_mRNA = np.isin(TU_index, idx_mRNA)
    is_tRNA = np.isin(TU_index, idx_tRNA)
    is_rRNA = np.isin(TU_index, idx_rRNA)
    is_rprotein = np.isin(TU_index, idx_rprotein)
    is_rnap = np.isin(TU_index, idx_rnap)
    is_fixed = is_tRNA | is_rRNA | is_rprotein | is_rnap

    # Rescale initiation probabilities based on type of RNA
    promoter_init_probs[is_mRNA] *= synth_prob_fractions["mRna"] / promoter_init_probs[is_mRNA].sum()
    promoter_init_probs[is_tRNA] *= synth_prob_fractions["tRna"] / promoter_init_probs[is_tRNA].sum()
    promoter_init_probs[is_rRNA] *= synth_prob_fractions["rRna"] / promoter_init_probs[is_rRNA].sum()

    # Set fixed synthesis probabilities for RProteins and RNAPs
    rescale_initiation_probs(
        promoter_init_probs,
        TU_index,
        np.concatenate((
            rna_synth_prob_R_protein[current_media_id],
            rna_synth_prob_rna_polymerase[current_media_id],
        )),
        np.concatenate((idx_rprotein, idx_rnap)),
    )

    assert promoter_init_probs[is_fixed].sum() < 1.0

    # Adjust for attenuation that will stop transcription after initiation
    if trna_attenuation:
        attenuation_readthrough = {
            idx: prob
            for idx, prob in zip(
                sim_data.process.transcription.attenuated_rna_indices,
                sim_data.process.transcription.attenuation_readthrough[sim_data.condition],
            )
        }
        readthrough_adjustment = np.array([attenuation_readthrough.get(idx, 1) for idx in TU_index])
        promoter_init_probs *= readthrough_adjustment

    scale_the_rest_by = (1.0 - promoter_init_probs[is_fixed].sum()) / promoter_init_probs[~is_fixed].sum()
    promoter_init_probs[~is_fixed] *= scale_the_rest_by

    # normalize to length of rna
    init_prob_length_adjusted = promoter_init_probs * rna_lengths[TU_index]
    init_prob_normalized = init_prob_length_adjusted / init_prob_length_adjusted.sum()

    # Sample a multinomial distribution of synthesis probabilities to determine
    # what RNA are initialized
    n_initiations = random_state.multinomial(n_RNAPs_to_activate, init_prob_normalized)

    # Build array of transcription unit indexes for partially transcribed mRNAs
    # and domain indexes for RNAPs
    TU_index_partial_RNAs = np.repeat(TU_index, n_initiations)
    domain_index_rnap = np.repeat(domain_index_promoters, n_initiations)

    # Build arrays of starting coordinates and transcription directions
    starting_coordinates = replication_coordinate[TU_index_partial_RNAs]
    is_forward = transcription_direction[TU_index_partial_RNAs]

    # Randomly advance RNAPs along the transcription units
    # TODO (Eran): make sure there aren't any RNAPs at same location on same TU
    updated_lengths = np.array(
        random_state.rand(n_RNAPs_to_activate) * rna_lengths[TU_index_partial_RNAs],
        dtype=int,
    )

    # Rescale boolean array of directions to an array of 1's and -1's.
    direction_rescaled = (2 * (is_forward - 0.5)).astype(np.int64)

    # Compute the updated coordinates of RNAPs. Coordinates of RNAPs moving in
    # the positive direction are increased, whereas coordinates of RNAPs moving
    # in the negative direction are decreased.
    updated_coordinates = starting_coordinates + np.multiply(direction_rescaled, updated_lengths)

    # Reset coordinates of RNAPs that cross the boundaries between right and
    # left replichores
    updated_coordinates[updated_coordinates > replichore_lengths[0]] -= chromosome_length
    updated_coordinates[updated_coordinates < -replichore_lengths[1]] += chromosome_length

    # Update mass
    sequences = rna_sequences[TU_index_partial_RNAs]
    added_mass = computeMassIncrease(sequences, updated_lengths, nt_weights)
    added_mass[updated_lengths != 0] += end_weight  # add endWeight to all new Rna

    # Masses of partial mRNAs are counted as mRNA mass as they are already
    # functional, but the masses of other types of partial RNAs are counted as
    # generic RNA mass.
    added_RNA_mass = added_mass.copy()
    added_mRNA_mass = added_mass.copy()

    is_mRNA_partial_RNAs = np.isin(TU_index_partial_RNAs, idx_mRNA)
    added_RNA_mass[is_mRNA_partial_RNAs] = 0
    added_mRNA_mass[np.logical_not(is_mRNA_partial_RNAs)] = 0

    # Add active RNAPs and get their unique indexes
    unique_molecules["active_RNAP"] = create_new_unique_molecules(
        "active_RNAP",
        n_RNAPs_to_activate,
        sim_data,
        unique_id_rng,
        domain_index=domain_index_rnap,
        coordinates=updated_coordinates,
        is_forward=is_forward,
    )

    # Decrement counts of bulk inactive RNAPs
    rnap_idx = bulk_name_to_idx(sim_data.molecule_ids.full_RNAP, bulk_state["id"])
    bulk_state["count"][rnap_idx] = inactive_RNAP_counts - n_RNAPs_to_activate

    # Add partially transcribed RNAs
    partial_rnas = create_new_unique_molecules(
        "RNA",
        n_RNAPs_to_activate,
        sim_data,
        unique_id_rng,
        TU_index=TU_index_partial_RNAs,
        transcript_length=updated_lengths,
        is_mRNA=is_mRNA_partial_RNAs,
        is_full_transcript=np.zeros(n_RNAPs_to_activate, dtype=bool),
        can_translate=is_mRNA_partial_RNAs,
        RNAP_index=unique_molecules["active_RNAP"]["unique_index"],
        massDiff_nonspecific_RNA=added_RNA_mass,
        massDiff_mRNA=added_mRNA_mass,
    )

    # Get counts of mRNAs initialized as bulk molecules
    mRNA_ids = sim_data.process.transcription.rna_data["id"][sim_data.process.transcription.rna_data["is_mRNA"]]
    mRNA_idx = bulk_name_to_idx(mRNA_ids, bulk_state["id"])
    mRNA_counts = bulk_state["count"][mRNA_idx]

    # Subtract number of partially transcribed mRNAs that were initialized.
    # Note: some mRNAs with high degradation rates have more partial mRNAs than
    # the expected total number of mRNAs - for these mRNAs we simply set the
    # initial full mRNA counts to be zero.
    partial_mRNA_counts = np.bincount(TU_index_partial_RNAs[is_mRNA_partial_RNAs], minlength=n_TUs)[idx_mRNA]
    full_mRNA_counts = (mRNA_counts - partial_mRNA_counts).clip(min=0)

    # Get array of TU indexes for each full mRNA
    TU_index_full_mRNAs = np.repeat(idx_mRNA, full_mRNA_counts)

    # Add fully transcribed mRNAs. The RNAP_index attribute of these molecules
    # are set to -1.
    full_rnas = create_new_unique_molecules(
        "RNA",
        len(TU_index_full_mRNAs),
        sim_data,
        unique_id_rng,
        TU_index=TU_index_full_mRNAs,
        transcript_length=rna_lengths[TU_index_full_mRNAs],
        is_mRNA=np.ones_like(TU_index_full_mRNAs, dtype=bool),
        is_full_transcript=np.ones_like(TU_index_full_mRNAs, dtype=bool),
        can_translate=np.ones_like(TU_index_full_mRNAs, dtype=bool),
        RNAP_index=np.full(TU_index_full_mRNAs.shape, -1, dtype=np.int64),
        massDiff_mRNA=rna_masses[TU_index_full_mRNAs],
    )
    unique_molecules["RNA"] = np.concatenate((partial_rnas, full_rnas))
    # Have to recreate unique indices or else there will be conflicts between
    # full and partial RNAs
    unique_prefix = np.min(unique_molecules["RNA"]["unique_index"])
    unique_molecules["RNA"]["unique_index"] = np.arange(unique_prefix, unique_prefix + len(unique_molecules["RNA"]))
    unique_molecules["RNA"] = MetadataArray(
        unique_molecules["RNA"],
        unique_prefix + len(unique_molecules["RNA"]),
    )

    # Reset counts of bulk mRNAs to zero
    bulk_state["count"][mRNA_idx] = 0


def initialize_chromosomal_segments(unique_molecules, sim_data, unique_id_rng):
    """
    Initialize unique molecule representations of chromosomal segments. All
    chromosomal segments are assumed to be at their relaxed states upon
    initialization.
    """
    # Load parameters
    relaxed_DNA_base_pairs_per_turn = sim_data.process.chromosome_structure.relaxed_DNA_base_pairs_per_turn
    terC_index = sim_data.process.chromosome_structure.terC_dummy_molecule_index
    replichore_lengths = sim_data.process.replication.replichore_lengths
    min_coordinates = -replichore_lengths[1]
    max_coordinates = replichore_lengths[0]

    # Get attributes of replisomes, active RNAPs, chromosome domains, full
    # chromosomes, and oriCs
    (replisome_coordinates, replisome_domain_indexes, replisome_unique_indexes) = attrs(
        unique_molecules["active_replisome"],
        ["coordinates", "domain_index", "unique_index"],
    )

    (
        active_RNAP_coordinates,
        active_RNAP_domain_indexes,
        active_RNAP_unique_indexes,
    ) = attrs(unique_molecules["active_RNAP"], ["coordinates", "domain_index", "unique_index"])

    chromosome_domain_domain_indexes, child_domains = attrs(
        unique_molecules["chromosome_domain"], ["domain_index", "child_domains"]
    )

    (full_chromosome_domain_indexes,) = attrs(unique_molecules["full_chromosome"], ["domain_index"])

    (origin_domain_indexes,) = attrs(unique_molecules["oriC"], ["domain_index"])

    # Initialize chromosomal segment attributes
    all_boundary_molecule_indexes = np.empty((0, 2), dtype=np.int64)
    all_boundary_coordinates = np.empty((0, 2), dtype=np.int64)
    all_segment_domain_indexes = np.array([], dtype=np.int32)
    all_linking_numbers = np.array([], dtype=np.float64)

    def get_chromosomal_segment_attributes(coordinates, unique_indexes, spans_oriC, spans_terC):
        """
        Returns the attributes of all chromosomal segments from a continuous
        stretch of DNA, given the coordinates and unique indexes of all
        boundary molecules.
        """
        coordinates_argsort = np.argsort(coordinates)
        coordinates_sorted = coordinates[coordinates_argsort]
        unique_indexes_sorted = unique_indexes[coordinates_argsort]

        # Add dummy molecule at terC if domain spans terC
        if spans_terC:
            coordinates_sorted = np.insert(
                coordinates_sorted,
                [0, len(coordinates_sorted)],
                [min_coordinates, max_coordinates],
            )
            unique_indexes_sorted = np.insert(unique_indexes_sorted, [0, len(unique_indexes_sorted)], terC_index)

        boundary_molecule_indexes = np.hstack((
            unique_indexes_sorted[:-1][:, np.newaxis],
            unique_indexes_sorted[1:][:, np.newaxis],
        ))
        boundary_coordinates = np.hstack((
            coordinates_sorted[:-1][:, np.newaxis],
            coordinates_sorted[1:][:, np.newaxis],
        ))

        # Remove segment that spans oriC if the domain does not span oriC
        if not spans_oriC:
            oriC_segment_index = np.where(np.sign(boundary_coordinates).sum(axis=1) == 0)[0]
            assert len(oriC_segment_index) == 1

            boundary_molecule_indexes = np.delete(boundary_molecule_indexes, oriC_segment_index, 0)
            boundary_coordinates = np.delete(boundary_coordinates, oriC_segment_index, 0)

        # Assumes all segments are at their relaxed state at initialization
        linking_numbers = (boundary_coordinates[:, 1] - boundary_coordinates[:, 0]) / relaxed_DNA_base_pairs_per_turn

        return boundary_molecule_indexes, boundary_coordinates, linking_numbers

    # Loop through each domain index
    for domain_index in chromosome_domain_domain_indexes:
        domain_spans_oriC = domain_index in origin_domain_indexes
        domain_spans_terC = domain_index in full_chromosome_domain_indexes

        # Get coordinates and indexes of all RNAPs on this domain
        RNAP_domain_mask = active_RNAP_domain_indexes == domain_index
        molecule_coordinates_this_domain = active_RNAP_coordinates[RNAP_domain_mask]
        molecule_indexes_this_domain = active_RNAP_unique_indexes[RNAP_domain_mask]

        # Append coordinates and indexes of replisomes on this domain, if any
        if not domain_spans_oriC:
            replisome_domain_mask = replisome_domain_indexes == domain_index
            molecule_coordinates_this_domain = np.concatenate((
                molecule_coordinates_this_domain,
                replisome_coordinates[replisome_domain_mask],
            ))
            molecule_indexes_this_domain = np.concatenate((
                molecule_indexes_this_domain,
                replisome_unique_indexes[replisome_domain_mask],
            ))

        # Append coordinates and indexes of parent domain replisomes, if any
        if not domain_spans_terC:
            parent_domain_index = chromosome_domain_domain_indexes[np.where(child_domains == domain_index)[0][0]]
            replisome_parent_domain_mask = replisome_domain_indexes == parent_domain_index
            molecule_coordinates_this_domain = np.concatenate((
                molecule_coordinates_this_domain,
                replisome_coordinates[replisome_parent_domain_mask],
            ))
            molecule_indexes_this_domain = np.concatenate((
                molecule_indexes_this_domain,
                replisome_unique_indexes[replisome_parent_domain_mask],
            ))

        # Get attributes of chromosomal segments on this domain
        (
            boundary_molecule_indexes_this_domain,
            boundary_coordinates_this_domain,
            linking_numbers_this_domain,
        ) = get_chromosomal_segment_attributes(
            molecule_coordinates_this_domain,
            molecule_indexes_this_domain,
            domain_spans_oriC,
            domain_spans_terC,
        )

        # Append to existing array of attributes
        all_boundary_molecule_indexes = np.vstack([
            all_boundary_molecule_indexes,
            boundary_molecule_indexes_this_domain,
        ])
        all_boundary_coordinates = np.vstack((all_boundary_coordinates, boundary_coordinates_this_domain))
        all_segment_domain_indexes = np.concatenate((
            all_segment_domain_indexes,
            np.full(len(linking_numbers_this_domain), domain_index, dtype=np.int32),
        ))
        all_linking_numbers = np.concatenate((all_linking_numbers, linking_numbers_this_domain))

    # Confirm total counts of all segments
    n_segments = len(all_linking_numbers)
    assert n_segments == len(active_RNAP_unique_indexes) + 1.5 * len(replisome_unique_indexes) + 1

    # Add chromosomal segments
    unique_molecules["chromosomal_segment"] = create_new_unique_molecules(
        "chromosomal_segment",
        n_segments,
        sim_data,
        unique_id_rng,
        boundary_molecule_indexes=all_boundary_molecule_indexes,
        boundary_coordinates=all_boundary_coordinates,
        domain_index=all_segment_domain_indexes,
        linking_number=all_linking_numbers,
    )


def initialize_translation(bulk_state, unique_molecules, sim_data, random_state, unique_id_rng):
    """
    Activate ribosomes as unique molecules, and distribute them along lengths
    of mRNAs, while decreasing counts of unactivated ribosomal subunits (30S
    and 50S).

    Ribosomes are placed randomly across the lengths of each mRNA.
    """
    # Load translation parameters
    current_nutrients = sim_data.conditions[sim_data.condition]["nutrients"]
    frac_active_ribosome = sim_data.process.translation.ribosomeFractionActiveDict[current_nutrients]
    protein_sequences = sim_data.process.translation.translation_sequences
    protein_lengths = sim_data.process.translation.monomer_data["length"].asNumber()
    translation_efficiencies = normalize(sim_data.process.translation.translation_efficiencies_by_monomer)
    aa_weights_incorporated = sim_data.process.translation.translation_monomer_weights
    end_weight = sim_data.process.translation.translation_end_weight
    cistron_lengths = sim_data.process.transcription.cistron_data["length"].asNumber(units.nt)
    TU_ids = sim_data.process.transcription.rna_data["id"]
    monomer_index_to_tu_indexes = sim_data.relation.monomer_index_to_tu_indexes
    monomer_index_to_cistron_index = {
        i: sim_data.process.transcription._cistron_id_to_index[monomer["cistron_id"]]
        for (i, monomer) in enumerate(sim_data.process.translation.monomer_data)
    }

    # Get attributes of RNAs
    (
        TU_index_all_RNAs,
        length_all_RNAs,
        is_mRNA,
        is_full_transcript_all_RNAs,
        unique_index_all_RNAs,
    ) = attrs(
        unique_molecules["RNA"],
        [
            "TU_index",
            "transcript_length",
            "is_mRNA",
            "is_full_transcript",
            "unique_index",
        ],
    )
    TU_index_mRNAs = TU_index_all_RNAs[is_mRNA]
    length_mRNAs = length_all_RNAs[is_mRNA]
    is_full_transcript_mRNAs = is_full_transcript_all_RNAs[is_mRNA]
    unique_index_mRNAs = unique_index_all_RNAs[is_mRNA]

    # Calculate available template lengths of each mRNA cistron from fully
    # transcribed mRNA transcription units
    TU_index_full_mRNAs = TU_index_mRNAs[is_full_transcript_mRNAs]
    TU_counts_full_mRNAs = np.bincount(TU_index_full_mRNAs, minlength=len(TU_ids))
    cistron_counts_full_mRNAs = sim_data.process.transcription.cistron_tu_mapping_matrix.dot(TU_counts_full_mRNAs)
    available_cistron_lengths = np.multiply(cistron_counts_full_mRNAs, cistron_lengths)

    # Add available template lengths from each partially transcribed mRNAs
    TU_index_incomplete_mRNAs = TU_index_mRNAs[np.logical_not(is_full_transcript_mRNAs)]
    length_incomplete_mRNAs = length_mRNAs[np.logical_not(is_full_transcript_mRNAs)]

    TU_index_to_mRNA_lengths = {}
    for TU_index, length in zip(TU_index_incomplete_mRNAs, length_incomplete_mRNAs):
        TU_index_to_mRNA_lengths.setdefault(TU_index, []).append(length)

    for TU_index, available_lengths in TU_index_to_mRNA_lengths.items():
        cistron_indexes = sim_data.process.transcription.rna_id_to_cistron_indexes(TU_ids[TU_index])
        cistron_start_positions = np.array([
            sim_data.process.transcription.cistron_start_end_pos_in_tu[(cistron_index, TU_index)][0]
            for cistron_index in cistron_indexes
        ])

        for length in available_lengths:
            available_cistron_lengths[cistron_indexes] += np.clip(
                length - cistron_start_positions, 0, cistron_lengths[cistron_indexes]
            )

    # Find number of ribosomes to activate
    ribosome30S_idx = bulk_name_to_idx(sim_data.molecule_ids.s30_full_complex, bulk_state["id"])
    ribosome30S = bulk_state["count"][ribosome30S_idx]
    ribosome50S_idx = bulk_name_to_idx(sim_data.molecule_ids.s50_full_complex, bulk_state["id"])
    ribosome50S = bulk_state["count"][ribosome50S_idx]
    inactive_ribosome_count = np.minimum(ribosome30S, ribosome50S)
    n_ribosomes_to_activate = np.int64(frac_active_ribosome * inactive_ribosome_count)

    # Add total available template lengths as weights and normalize
    protein_init_probs = normalize(
        available_cistron_lengths[sim_data.relation.cistron_to_monomer_mapping] * translation_efficiencies
    )

    # Sample a multinomial distribution of synthesis probabilities to determine
    # which types of mRNAs are initialized
    n_new_proteins = random_state.multinomial(n_ribosomes_to_activate, protein_init_probs)

    # Build attributes for active ribosomes
    protein_indexes = np.empty(n_ribosomes_to_activate, np.int64)
    cistron_start_positions_on_mRNA = np.empty(n_ribosomes_to_activate, np.int64)
    positions_on_mRNA_from_cistron_start_site = np.empty(n_ribosomes_to_activate, np.int64)
    mRNA_indexes = np.empty(n_ribosomes_to_activate, np.int64)
    start_index = 0
    nonzero_count = n_new_proteins > 0

    for protein_index, protein_counts in zip(
        np.arange(n_new_proteins.size)[nonzero_count], n_new_proteins[nonzero_count]
    ):
        # Set protein index
        protein_indexes[start_index : start_index + protein_counts] = protein_index

        # Get index of cistron corresponding to this protein
        cistron_index = monomer_index_to_cistron_index[protein_index]

        # Initialize list of available lengths for each transcript and the
        # indexes of each transcript in the list of mRNA attributes
        available_lengths = []
        attribute_indexes = []
        cistron_start_positions = []

        # Distribute ribosomes among mRNAs that produce this protein, weighted
        # by their lengths
        for TU_index in monomer_index_to_tu_indexes[protein_index]:
            attribute_indexes_this_TU = np.where(TU_index_mRNAs == TU_index)[0]
            cistron_start_position = sim_data.process.transcription.cistron_start_end_pos_in_tu[
                (cistron_index, TU_index)
            ][0]
            available_lengths.extend(
                np.clip(
                    length_mRNAs[attribute_indexes_this_TU] - cistron_start_position,
                    0,
                    cistron_lengths[cistron_index],
                )
            )
            attribute_indexes.extend(attribute_indexes_this_TU)
            cistron_start_positions.extend([cistron_start_position] * len(attribute_indexes_this_TU))

        available_lengths = np.array(available_lengths)
        attribute_indexes = np.array(attribute_indexes)
        cistron_start_positions = np.array(cistron_start_positions)

        n_ribosomes_per_RNA = random_state.multinomial(protein_counts, normalize(available_lengths))

        # Get unique indexes of each mRNA
        mRNA_indexes[start_index : start_index + protein_counts] = np.repeat(
            unique_index_mRNAs[attribute_indexes], n_ribosomes_per_RNA
        )

        # Get full length of this polypeptide
        peptide_full_length = protein_lengths[protein_index]

        # Randomly place ribosomes along the length of each mRNA, capped by the
        # mRNA length expected from the full polypeptide length to prevent
        # ribosomes from overshooting full peptide lengths
        cistron_start_positions_on_mRNA[start_index : start_index + protein_counts] = np.repeat(
            cistron_start_positions, n_ribosomes_per_RNA
        )
        positions_on_mRNA_from_cistron_start_site[start_index : start_index + protein_counts] = np.floor(
            random_state.rand(protein_counts)
            * np.repeat(
                np.minimum(available_lengths, peptide_full_length * 3),
                n_ribosomes_per_RNA,
            )
        )

        start_index += protein_counts

    # Calculate the lengths of the partial polypeptide, and rescale position on
    # mRNA to be a multiple of three using this peptide length
    peptide_lengths = np.floor_divide(positions_on_mRNA_from_cistron_start_site, 3)
    positions_on_mRNA = cistron_start_positions_on_mRNA + 3 * peptide_lengths

    # Update masses of partially translated proteins
    sequences = protein_sequences[protein_indexes]
    mass_increase_protein = computeMassIncrease(sequences, peptide_lengths, aa_weights_incorporated)

    # Add end weight
    mass_increase_protein[peptide_lengths != 0] += end_weight

    # Add active ribosomes
    unique_molecules["active_ribosome"] = create_new_unique_molecules(
        "active_ribosome",
        n_ribosomes_to_activate,
        sim_data,
        unique_id_rng,
        protein_index=protein_indexes,
        peptide_length=peptide_lengths,
        mRNA_index=mRNA_indexes,
        pos_on_mRNA=positions_on_mRNA,
        massDiff_protein=mass_increase_protein,
    )

    # Decrease counts of free 30S and 50S ribosomal subunits
    bulk_state["count"][ribosome30S_idx] = ribosome30S - n_ribosomes_to_activate
    bulk_state["count"][ribosome50S_idx] = ribosome50S - n_ribosomes_to_activate


def determine_chromosome_state(
    tau: Unum,
    replichore_length: Unum,
    n_max_replisomes: int,
    place_holder: int,
    cell_mass: Unum,
    critical_mass: Unum,
    replication_rate: float,
) -> tuple[
    dict[str, npt.NDArray[np.int32]],
    dict[str, npt.NDArray[Any]],
    dict[str, npt.NDArray[np.int32]],
]:
    """
    Calculates the attributes of oriC's, replisomes, and chromosome domains on
    the chromosomes at the beginning of the cell cycle.

    Args:
        tau: the doubling time of the cell (with Unum time unit)
        replichore_length: the amount of DNA to be replicated per fork, usually
            half of the genome, in base-pairs (with Unum nucleotide unit)
        n_max_replisomes: the maximum number of replisomes that can be formed
            given the initial counts of replisome subunits
        place_holder: placeholder value for chromosome domains without child
            domains
        cell_mass: total mass of the cell with mass units (with Unum mass unit)
        critical_mass: mass per oriC before replication is initiated
            (with Unum mass unit)
        replication_rate: rate of nucleotide elongation
            (with Unum nucleotides per time unit)

    Returns:
        Three dictionaries, each containing updates to attributes of a unique molecule type.

        - ``oric_state``: dictionary of the following format::

            {'domain_index': a vector of integers indicating which chromosome domain the
                oriC sequence belongs to.}

        - ``replisome_state``: dictionary of the following format::

            {'coordinates': a vector of integers that indicates where the replisomes
                are located on the chromosome relative to the origin in base pairs,
            'right_replichore': a vector of boolean values that indicates whether the
                replisome is on the right replichore (True) or the left replichore (False),
            'domain_index': a vector of integers indicating which chromosome domain the
                replisomes belong to. The index of the "mother" domain of the replication
                fork is assigned to the replisome}

        - ``domain_state``: dictionary of the following format::

            {'domain_index': the indexes of the domains,
            'child_domains': the (n_domain X 2) array of the domain indexes of the two
                children domains that are connected on the oriC side with the given domain.}

    """

    # All inputs must be positive numbers
    unitless_tau = tau.asNumber(units.s)
    unitless_replichore_length = replichore_length.asNumber(units.nt)
    assert unitless_tau >= 0, "tau value can't be negative."
    assert unitless_replichore_length > 0, "replichore_length must be positive."

    # Convert to unitless
    unitless_cell_mass = cell_mass.asNumber(units.fg)
    unitless_critical_mass = critical_mass.asNumber(units.fg)

    # Calculate the maximum number of replication rounds given the maximum
    # count of replisomes
    n_max_rounds = int(np.log2(n_max_replisomes / 2 + 1))

    # Calculate the number of active replication rounds
    n_rounds = min(
        n_max_rounds,
        max(0, int(np.ceil(np.log2(unitless_cell_mass / unitless_critical_mass)))),
    )

    # Initialize arrays for replisomes
    n_replisomes = 2 * (2**n_rounds - 1)
    coordinates = np.zeros(n_replisomes, dtype=np.int64)
    right_replichore_replisome = np.zeros(n_replisomes, dtype=bool)
    domain_index_replisome = np.zeros(n_replisomes, dtype=np.int32)

    # Initialize child domain array for chromosome domains
    n_domains = 2 ** (n_rounds + 1) - 1
    child_domains = np.full((n_domains, 2), place_holder, dtype=np.int32)

    # Set domain_index attribute of oriC's and chromosome domains
    domain_index_oric = np.arange(2**n_rounds - 1, 2 ** (n_rounds + 1) - 1, dtype=np.int32)
    domain_index_domains = np.arange(0, n_domains, dtype=np.int32)

    def n_events_before_this_round(round_idx):
        """
        Calculates the number of replication events that happen before the
        replication round index given as an argument. Since 2**i events happen
        at each round i = 0, 1, ..., the sum of the number of events before
        round j is 2**j - 1.
        """
        return 2**round_idx - 1

    # Loop through active replication rounds, starting from the oldest round.
    # If n_round = 0 skip loop entirely - no active replication round.
    for round_idx in np.arange(n_rounds):
        # Determine at which location (base) of the chromosome the replication
        # forks should be initialized to
        round_critical_mass = 2**round_idx * unitless_critical_mass
        growth_rate = np.log(2) / unitless_tau
        replication_time = np.log(unitless_cell_mass / round_critical_mass) / growth_rate
        # TODO: this should handle completed replication (instead of taking min)
        # for accuracy but will likely never start with multiple chromosomes
        fork_location = min(
            np.floor(replication_time * replication_rate),
            unitless_replichore_length - 1,
        )

        # Add 2^n initiation events per round. A single initiation event
        # generates two replication forks.
        n_events_this_round = int(2**round_idx)

        # Set attributes of replisomes for this replication round
        coordinates[2 * n_events_before_this_round(round_idx) : 2 * n_events_before_this_round(round_idx + 1)] = (
            np.tile(np.array([fork_location, -fork_location]), n_events_this_round)
        )

        right_replichore_replisome[
            2 * n_events_before_this_round(round_idx) : 2 * n_events_before_this_round(round_idx + 1)
        ] = np.tile(np.array([True, False]), n_events_this_round)

        for i, domain_index in enumerate(
            np.arange(
                n_events_before_this_round(round_idx),
                n_events_before_this_round(round_idx + 1),
            )
        ):
            domain_index_replisome[
                2 * n_events_before_this_round(round_idx) + 2 * i : 2 * n_events_before_this_round(round_idx)
                + 2 * (i + 1)
            ] = np.repeat(domain_index, 2)

        # Set attributes of chromosome domains for this replication round
        for i, domain_index in enumerate(
            np.arange(
                n_events_before_this_round(round_idx + 1),
                n_events_before_this_round(round_idx + 2),
                2,
            )
        ):
            child_domains[n_events_before_this_round(round_idx) + i, :] = np.array([domain_index, domain_index + 1])

    # Convert to numpy arrays and wrap into dictionaries
    oric_state: dict[str, npt.NDArray[np.int32]] = {"domain_index": domain_index_oric}

    replisome_state = {
        "coordinates": coordinates,
        "right_replichore": right_replichore_replisome,
        "domain_index": domain_index_replisome,
    }

    domain_state = {
        "child_domains": child_domains,
        "domain_index": domain_index_domains,
    }

    return oric_state, replisome_state, domain_state


def rescale_initiation_probs(init_probs, TU_index, fixed_synth_probs, fixed_TU_indexes):
    """
    Rescales the initiation probabilities of each promoter such that the total
    synthesis probabilities of certain types of RNAs are fixed to a
    predetermined value. For instance, if there are two copies of promoters for
    RNA A, whose synthesis probability should be fixed to 0.1, each promoter is
    given an initiation probability of 0.05.
    """
    for rna_idx, synth_prob in zip(fixed_TU_indexes, fixed_synth_probs):
        fixed_rna_mask = TU_index == rna_idx
        init_probs[fixed_rna_mask] = synth_prob / fixed_rna_mask.sum()


def calculate_cell_mass(bulk_state, unique_molecules, sim_data):
    """
    Calculates cell mass in femtograms.
    """
    bulk_submass_names = [f"{submass}_submass" for submass in sim_data.submass_name_to_index.keys()]
    cell_mass = bulk_state["count"].dot(rfn.structured_to_unstructured(bulk_state[bulk_submass_names])).sum()

    if len(unique_molecules) > 0:
        unique_masses = sim_data.internal_state.unique_molecule.unique_molecule_masses["mass"].asNumber(
            units.fg / units.mol
        ) / sim_data.constants.n_avogadro.asNumber(1 / units.mol)
        unique_ids = sim_data.internal_state.unique_molecule.unique_molecule_masses["id"]
        unique_submass_names = [f"massDiff_{submass}" for submass in sim_data.submass_name_to_index.keys()]
        for unique_id, unique_submasses in zip(unique_ids, unique_masses):
            if unique_id in unique_molecules:
                cell_mass += (unique_molecules[unique_id]["_entryState"].sum() * unique_submasses).sum()
                cell_mass += rfn.structured_to_unstructured(unique_molecules[unique_id][unique_submass_names]).sum()

    return units.fg * cell_mass


def initialize_trna_charging(
    bulk_state: np.ndarray,
    unique_molecules: dict[str, np.ndarray],
    sim_data: Any,
    variable_elongation: bool,
):
    """
    Initializes charged tRNA from uncharged tRNA and amino acids

    Args:
        bulk_state: Structured array with IDs and counts of all bulk molecules
        unique_molecules: Mapping of unique molecule names to structured
            arrays of their current simulation states
        sim_data: Simulation data loaded from pickle generated by ParCa
        variable_elongation: Sets max elongation higher if True

    .. note::
        Does not adjust for mass of amino acids on charged tRNA (~0.01% of cell mass)
    """
    # Calculate cell volume for concentrations
    cell_volume = calculate_cell_mass(bulk_state, unique_molecules, sim_data) / sim_data.constants.cell_density
    counts_to_molar = 1 / (sim_data.constants.n_avogadro * cell_volume)

    # Get molecule views and concentrations
    transcription = sim_data.process.transcription
    aa_from_synthetase = transcription.aa_from_synthetase
    aa_from_trna = transcription.aa_from_trna
    synthetases = counts(bulk_state, bulk_name_to_idx(transcription.synthetase_names, bulk_state["id"]))
    uncharged_trna_idx = bulk_name_to_idx(transcription.uncharged_trna_names, bulk_state["id"])
    uncharged_trna = counts(bulk_state, uncharged_trna_idx)
    charged_trna_idx = bulk_name_to_idx(transcription.charged_trna_names, bulk_state["id"])
    charged_trna = counts(bulk_state, charged_trna_idx)
    aas = counts(
        bulk_state,
        bulk_name_to_idx(sim_data.molecule_groups.amino_acids, bulk_state["id"]),
    )

    ribosome_counts = unique_molecules["active_ribosome"]["_entryState"].sum()

    synthetase_conc = counts_to_molar * np.dot(aa_from_synthetase, synthetases)
    uncharged_trna_conc = counts_to_molar * np.dot(aa_from_trna, uncharged_trna)
    charged_trna_conc = counts_to_molar * np.dot(aa_from_trna, charged_trna)
    aa_conc = counts_to_molar * aas
    ribosome_conc = counts_to_molar * ribosome_counts

    # Estimate fraction of amino acids from sequences, excluding first index for padding of -1
    _, aas_in_sequences = np.unique(sim_data.process.translation.translation_sequences, return_counts=True)
    f = aas_in_sequences[1:] / np.sum(aas_in_sequences[1:])

    # Estimate initial charging state
    constants = sim_data.constants
    transcription = sim_data.process.transcription
    metabolism = sim_data.process.metabolism
    elongation_max = (
        constants.ribosome_elongation_rate_max if variable_elongation else constants.ribosome_elongation_rate_basal
    )
    charging_params = {
        "kS": constants.synthetase_charging_rate.asNumber(1 / units.s),
        "KMaa": transcription.aa_kms.asNumber(MICROMOLAR_UNITS),
        "KMtf": transcription.trna_kms.asNumber(MICROMOLAR_UNITS),
        "krta": constants.Kdissociation_charged_trna_ribosome.asNumber(MICROMOLAR_UNITS),
        "krtf": constants.Kdissociation_uncharged_trna_ribosome.asNumber(MICROMOLAR_UNITS),
        "max_elong_rate": float(elongation_max.asNumber(units.aa / units.s)),
        "charging_mask": np.array([aa not in REMOVED_FROM_CHARGING for aa in sim_data.molecule_groups.amino_acids]),
        "unit_conversion": metabolism.get_amino_acid_conc_conversion(MICROMOLAR_UNITS),
    }
    fraction_charged, *_ = calculate_trna_charging(
        synthetase_conc,
        uncharged_trna_conc,
        charged_trna_conc,
        aa_conc,
        ribosome_conc,
        f,
        charging_params,
    )

    # Update counts of tRNA to match charging
    total_trna_counts = uncharged_trna + charged_trna
    charged_trna_counts = np.round(total_trna_counts * np.dot(fraction_charged, aa_from_trna))
    uncharged_trna_counts = total_trna_counts - charged_trna_counts
    bulk_state["count"][charged_trna_idx] = charged_trna_counts
    bulk_state["count"][uncharged_trna_idx] = uncharged_trna_counts
