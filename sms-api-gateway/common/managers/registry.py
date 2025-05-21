from typing import Callable
from process_bigraph import ProcessTypes, Process, Step


class RegistryManager:
    def __init__(self, registries: dict[str, ProcessTypes] | None = None) -> None:
        self.registries = registries or {}
    
    def verify(self, registry_id: str) -> bool:
        return self.registries.get(registry_id) is not None
    
    def get(self, registry_id: str) -> ProcessTypes:
        exists = self.verify(registry_id)
        if exists:
            return self.registries[registry_id]
        else:
            raise RuntimeError(f"Registry with ID: {registry_id} has not yet been registered. Use this class' add_registry method first.")

    def set(self, reg_id: str, new: ProcessTypes):
        exists = self.verify(reg_id)
        if exists:
            self._set(reg_id, new)
        else:
            raise RuntimeError("This registry has not yet been registered. Use this class' add_registry method instead.")

    def add(self, registry_id: str, reg: ProcessTypes):
        exists = self.verify(registry_id)
        if not exists:
            self._set(registry_id, reg)
        else:
            raise RuntimeError("This registry has already been registered. Use this class' set_registry method instead.")
    
    def register_processes(self, reg_id: str, library: dict[str, Process | Step]):
        for name, process in library.items():
            self.registries[reg_id].register_process(name, process)
    
    def register_types(self, reg_id: str, library: dict[str, dict[str, dict[str, str | Callable]]]):
        return self.registries[reg_id].register_types(library)
    
    def _set(self, reg_id: str, reg: ProcessTypes):
        self.registries[reg_id] = reg
            
