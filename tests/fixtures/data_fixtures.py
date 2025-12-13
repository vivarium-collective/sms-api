from pathlib import Path
from random import randint
from typing import Any

import httpx
import numpy as np
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from sms_api.data.sim_analysis_service import AnalysisService, AnalysisServiceHpc


@pytest_asyncio.fixture(scope="function")
async def simulation_data() -> dict[str, Any]:
    return {
        "bulk": {
            "a": 1111,
            "b": 22,
            "c": 3
        },
        "env": {
            "exchange": {
                "1": 11.11,
                "2": 2.2
            }
        },
        "cell": {
            "metabolite": [1.0, 2.3, 0.5],
            "protein": 10,
            "env": {"temp": 37, "pH": 7.2}
        }
    }


@pytest_asyncio.fixture(scope="function")
async def data_fixture() -> dict[str, np.ndarray]:
    n = 1111
    cols = ['x', 'y']
    return dict(zip(
        cols,
        [np.random.random(n,) for _ in range(len(cols))]
    ))


@pytest_asyncio.fixture(scope="function")
async def analysis_service() -> AnalysisServiceHpc:
    return AnalysisServiceHpc()
