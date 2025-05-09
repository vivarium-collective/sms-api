# setup utils
from typing import Callable

import numpy as np
import rustworkx as rx
from qiskit.circuit.library import QAOAAnsatz


def rustworkx_graph_setup(w: list[list[float]]):
    num_nodes = len(w)
    w = np.array(w)

    # Create graph from adjacency matrix
    edges = []
    for i in range(num_nodes):
        for j in range(num_nodes):
            if w[i, j] > 0:  # Add edges where weight > 0
                edges.append((i, j, w[i, j]))

    G = rx.PyGraph()
    G.add_nodes_from(range(num_nodes))  # Add nodes
    G.add_edges_from(edges)  # Add edges with weights
    return G


def configure_runtime(circuit: QAOAAnsatz):
    import os
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    QiskitRuntimeService.save_account(channel="ibm_quantum", token=os.getenv("IBM_QUANTUM_TOKEN"), overwrite=True, set_as_default=True)
    service = QiskitRuntimeService(channel='ibm_quantum')
    backend = service.least_busy(min_num_qubits=127)
    print(backend)

    # Create pass manager for transpilation
    pm = generate_preset_pass_manager(optimization_level=3,
                                      backend=backend)

    candidate_circuit = pm.run(circuit)
    candidate_circuit.draw('mpl', fold=False, idle_wires=False)

    return backend, pm, candidate_circuit


def get_node_pairs(nodes: list) -> list[tuple]:
    from itertools import combinations
    return list(combinations(nodes, 2))


def random_weight() -> float:
    n = np.random.rand()
    return n ** n / n if n > 0.5 else n ** n * n


def get_weights(node_pairs: list[tuple], generator: Callable, as_tuple: bool = False) -> list[tuple[int, int, float]]:
    # node_list = [(0, 1), (0, 2), (0, 4), (1, 2), (2, 3), (3, 4)]
    return list(map(
        lambda nodes: (*nodes, generator()) if as_tuple else [*nodes, generator()],
        node_pairs
    ))


def get_random_weights(node_pairs: list[tuple]):
    return get_weights(node_pairs, random_weight)


def random_connection():
    n = np.random.rand()
    return 1.0 if n > 0.5 else 0.0


def random_adjacency_matrix(num_nodes: int):
    r = range(num_nodes)
    w = [[random_connection() for _ in r] for _ in r]
    return w


def draw_graph(graph, node_size=600):
    from rustworkx.visualization import mpl_draw as _draw_graph
    return _draw_graph(graph, node_size=node_size, with_labels=True)


def initialize_graph_k(n_nodes_k: int) -> rx.PyGraph:
    """
    Initialize new graph for iteration k.

    :params n_nodes_k: (`int`) Number of nodes (variables) at iteration k for the N-var qaoa solution.

    :rtype: `rustworkx.PyGraph` instance parameterized by n nodes.
    """
    graph_k = rx.PyGraph()

    # add num_nodes for iteration k (n_variables for k)
    nodes_k = np.arange(0, n_nodes_k, 1).tolist()
    graph_k.add_nodes_from(nodes_k)

    # add edge list for iteration k
    node_pairs = get_node_pairs(nodes_k)
    edges_k = get_weights(node_pairs, random_weight)
    graph_k.add_edges_from(edges_k)
    return graph_k
