import numpy as np
import networkx as nx
from qiskit.primitives import Sampler
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals
from qiskit_algorithms import QAOA as QAOASolver
from process_bigraph import Process

from bsp.utils.quantum_utils import get_operator, sample_most_likely


class QAOA(Process):
    config_schema = {
        "n_variables": "integer",
        "random_seed": "integer"
        # "edge_list": "list[tuple[float]]",  # in the format: [(node_a, node_b, weight/is_connected(1 or 0)), ...]
    }

    def __init__(self, config, core):
        super().__init__(config, core)
        self.n_variables = self.config["n_variables"]
        self.random_seed = self.config.get("random_seed", 10598)

        # initial params for probablistic terms
        self.initial_gamma = np.pi
        self.initial_beta = np.pi/2
        self.init_params = [self.initial_gamma, self.initial_beta, self.initial_gamma, self.initial_beta]

    def initial_state(self):
        return {
            "bitstring": [0 for _ in range(self.n_variables)],
            "n_nodes": self.n_variables
        }

    def inputs(self):
        return {
            "n_nodes": "integer",
            "adjacentcy_matrix": "list[list[float]]"
        }

    def outputs(self):
        return {
            "bitstring": "list[integer]",
            "n_nodes": "integer"
        }

    def update(self, inputs, interval):
        # graph = initialize_graph_k(n_nodes_k)

        # initialize graph
        n_nodes_k = inputs.get("n_nodes")
        w = np.array(
            inputs.get("adjacentcy_matrix")
        )
        G = nx.from_numpy_array(w)

        # get quantum operator
        qubit_op, offset = get_operator(w, n_nodes_k)

        # set up optimizer and sampler
        optimizer = COBYLA()
        sampler = Sampler()
        algorithm_globals.random_seed = self.random_seed

        # perform qaoa
        qaoa = QAOASolver(sampler, optimizer, reps=2)

        # extract bitstring
        result = qaoa.compute_minimum_eigenvalue(qubit_op)
        bitstring_k = sample_most_likely(result.eigenstate)

        return {
            "bitstring": bitstring_k.tolist(),
            "n_nodes": n_nodes_k - 1
        }
