import json
from typing import Any, Callable
import warnings


class RunsDb(object):
    _existing_runs: set[str] = set()
    _existing_results: list = []

    @property
    def existing_results(self):
        return self._existing_results
    
    @existing_results.setter 
    def existing_results(self, new):
        is_same = self._compare_results(new)
        print(f'Is same data: {is_same}')
        self._existing_results = new 
    
    def _compare_results(self, new: dict[str, str]):
        # this method serves to maintain as much concurrency as possible by comparing the
        # currently set runs to the ones being set (for safety)
        return self._existing_results == new
    
    async def add_run(self, response: dict):
        response.pop("_id", None)
        self._existing_results.append(json.dumps(response))
        print(f'Added response: {response}')
    
    async def get_run(self, simulation_id: str):
        matcher = filter(
            lambda v: simulation_id in v,
            self.existing_results
        )
        try:
            serialized_run = next(matcher)
            run = await self.hydrate_run(serialized_run)
            return run 
        except StopIteration:
            warnings.warn(f"No run exists for simulation id: {simulation_id}")
            return None
    
    async def hydrate_run(self, run: str):
        return json.loads(run)