from math import pi
from typing import *

import numpy as np
import rustworkx as rx
import networkx as nx
from qiskit_nature.second_q.hamiltonians.lattices import (
    BoundaryCondition,
    HyperCubicLattice,
    Lattice,
    LatticeDrawStyle,
    LineLattice,
    SquareLattice,
    TriangularLattice,
)
from qiskit_nature.second_q.hamiltonians import FermiHubbardModel
from qiskit_nature.second_q.problems import LatticeModelProblem
from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit_nature.second_q.algorithms import GroundStateEigensolver
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit.quantum_info import Pauli, SparsePauliOp
from qiskit.primitives import Sampler
from qiskit.quantum_info import Pauli
from qiskit.result import QuasiDistribution
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals

from process_bigraph import Composite, Process
# TODO: import more qiskit nature for sbml processes here
from biosimulators_processes import CORE


class QiskitProcess(Process):
    config_schema = {
        'num_qbits': 'int',
        'duration': 'int'
    }

    def __init__(self, config=None, core=CORE):
        super().__init__(config, core)

    def initial_state(self):
        return {}

    def inputs(self):
        return {}

    def outputs(self):
        return {}

    def update(self, state, interval):
        return {}


class QAOAProcess(QiskitProcess):
    config_schema = {
        'bigraph_instance': 'tree[any]'}

    def __init__(self, config=None, core=CORE):
        # TODO: Finish this based on https://qiskit-community.github.io/qiskit-algorithms/tutorials/05_qaoa.html
        super().__init__(config, core)
        self.num_nodes = len(list(self.config['bigraph_instance'].keys()))

        # TODO: Enable dynamic setting of these weights with np.stack
        weights = []
        for i, n in enumerate(list(range(self.num_nodes))):
            adj = [0.0, 1.0, 1.0, 0.0]  # TODO: Finish this below
            weights.append(adj)

        # self.w = np.stack(weights)
        self.w = np.array([
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 0.0, 1.0, 1.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0, 0.0]])

        self.G = nx.from_numpy_array(self.w)
        self.sampler = Sampler()

        print('Drawing graph: ')
        self._draw_graph()

    def initial_state(self):
        return {}

    def inputs(self):
        return {'weights': 'list[float]', 'objective_result': 'int'}

    def outputs(self):
        return {'weights': 'list[float]', 'objective_result': 'int'}

    def update(self, state, interval):
        qubit_op, offset = self._get_operator(self.w)
        algorithm_globals.random_seed = 10598

        optimizer = COBYLA()
        qaoa = QAOA(self.sampler, optimizer, reps=2)

        result = qaoa.compute_minimum_eigenvalue(qubit_op)

        x = self._sample_most_likely(result.eigenstate)
        objective_result = self._objective_value(x, self.w)
        # TODO: somehow update the weights assigned to self.w here.
        return {'weights': self.w, 'objective_result': objective_result}

    @classmethod
    def _sample_most_likely(cls, state_vector):
        """Compute the most likely binary string from state vector.
        Args:
            state_vector: State vector or quasi-distribution.

        Returns:
            Binary string as an array of ints.
        """
        if isinstance(state_vector, QuasiDistribution):
            values = list(state_vector.values())
        else:
            values = state_vector
        n = int(np.log2(len(values)))
        k = np.argmax(np.abs(values))
        x = cls._bitfield(k, n)
        x.reverse()
        return np.asarray(x)

    @classmethod
    def _objective_value(cls, x, w):
        """Compute the value of a cut.
        Args:
            x: Binary string as numpy array.
            w: Adjacency matrix.
        Returns:
            Value of the cut.
        """
        X = np.outer(x, (1 - x))
        w_01 = np.where(w != 0, 1, 0)
        return np.sum(w_01 * X)

    @classmethod
    def _bitfield(cls, n, L):
        result = np.binary_repr(n, L)
        return [int(digit) for digit in result]

    @classmethod
    def _get_operator(cls, weight_matrix) -> Tuple[SparsePauliOp, int]:
        r"""Generate Hamiltonian for the graph partitioning
        Notes:
            Goals:
                1 Separate the vertices into two set of the same size.
                2 Make sure the number of edges between the two set is minimized.
            Hamiltonian:
                H = H_A + H_B
                H_A = sum\_{(i,j)\in E}{(1-ZiZj)/2}
                H_B = (sum_{i}{Zi})^2 = sum_{i}{Zi^2}+sum_{i!=j}{ZiZj}
                H_A is for achieving goal 2 and H_B is for achieving goal 1.
        Args:
            weight_matrix: Adjacency matrix.
        Returns:
            Operator for the Hamiltonian
            A constant shift for the obj function.
        """
        num_nodes = len(weight_matrix)
        pauli_list = []
        coeffs = []
        shift = 0

        for i in range(num_nodes):
            for j in range(i):
                if weight_matrix[i, j] != 0:
                    x_p = np.zeros(num_nodes, dtype=bool)
                    z_p = np.zeros(num_nodes, dtype=bool)
                    z_p[i] = True
                    z_p[j] = True
                    pauli_list.append(Pauli((z_p, x_p)))
                    coeffs.append(-0.5)
                    shift += 0.5

        for i in range(num_nodes):
            for j in range(num_nodes):
                if i != j:
                    x_p = np.zeros(num_nodes, dtype=bool)
                    z_p = np.zeros(num_nodes, dtype=bool)
                    z_p[i] = True
                    z_p[j] = True
                    pauli_list.append(Pauli((z_p, x_p)))
                    coeffs.append(1.0)
                else:
                    shift += 1

        return SparsePauliOp(pauli_list, coeffs=coeffs), shift

    def _draw_graph(self):
        layout = nx.random_layout(self.G, seed=10)
        colors = ["r", "g", "b", "y"]
        nx.draw(self.G, layout, node_color=colors)
        labels = nx.get_edge_attributes(self.G, "weight")
        return nx.draw_networkx_edge_labels(self.G, pos=layout, edge_labels=labels)


class QuantumAutoencoderProcess(QiskitProcess):
    config_schema = {
        'num_qbits': 'int',
        'duration': 'int',
        'global_random_seed': {
            '_default': 42,
            '_type': 'string'
        }}

    def __init__(self, config=None, core=CORE):
        super().__init__(config, core)
        """
            TODO: See https://qiskit-community.github.io/qiskit-machine-learning/tutorials/12_quantum_autoencoder.html
        """


class LatticeGroundStateSolverProcess(QiskitProcess):
    config_schema = {
        'num_nodes': 'int',
        'interaction_parameters': {
            '_type': 'tree[float]',
            '_default': {'t': -1.0, 'u': 5.0}},
        'onsite_potential': {  # <--alias for v
            '_default': 0.0,
            '_type': 'float'}}

    def __init__(self, config=None, core=CORE):
        super().__init__(config, core)

        num_nodes = self.config['num_nodes']
        boundary_condition = BoundaryCondition.OPEN
        line_lattice = LineLattice(num_nodes=num_nodes, boundary_condition=boundary_condition)
        interaction_parameters = self.config['interaction_parameters']
        t = interaction_parameters['t']
        u = interaction_parameters['u']
        v = self.config['onsite_potential']
        lattice = line_lattice.uniform_parameters(uniform_interaction=t, uniform_onsite_potential=v)
        fhm = FermiHubbardModel(lattice=lattice, onsite_interaction=u)
        self.lmp = LatticeModelProblem(fhm)

    def initial_state(self):
        return {}

    def inputs(self):
        """TODO: Take in instances of bigraphs and convert and then fit them into the Fermi Hubbard Model."""
        return {}

    def outputs(self):
        return {'ground_state': 'float'}

    def update(self, state, interval):
        numpy_solver = NumPyMinimumEigensolver()
        qubit_mapper = JordanWignerMapper()
        calc = GroundStateEigensolver(qubit_mapper, numpy_solver)
        res = calc.solve(self.lmp)
        print(res)
        # TODO: somehow be able to create a new instance from this ground state.
        return {'ground_state': res}
