from process_bigraph import ProcessTypes
from process_bigraph.processes import TOY_PROCESSES

from common.managers.registry import RegistryManager

manager = RegistryManager()

base_reg_id = "base"
base_registry = ProcessTypes()  # define base process TODO: expand this, fine for now.
manager.add(base_reg_id, base_registry)

# TODO: register types for api and processes here if needed.

manager.register_processes(base_reg_id, TOY_PROCESSES)
