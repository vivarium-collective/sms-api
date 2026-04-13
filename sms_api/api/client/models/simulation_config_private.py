from enum import Enum


class SimulationConfigPrivate(str, Enum):
    API_FINAL_MEC_JSON = "api_final_mec.json"
    API_SIMULATION_DEFAULT_JSON = "api_simulation_default.json"
    API_TEST_VIOLACEIN_NO_METABOLISM_JSON = "api_test_violacein_no_metabolism.json"
    API_TEST_VIOLACEIN_WITH_METABOLISM_JSON = "api_test_violacein_with_metabolism.json"

    def __str__(self) -> str:
        return str(self.value)
