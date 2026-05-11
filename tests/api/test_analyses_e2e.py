"""E2E tests for POST /api/v1/analyses against the live production API.

Verifies that ptools_rna single analysis requests complete successfully
for representative experiment IDs.

Prerequisites:
- VPN must be OFF (sms.cam.uchc.edu is externally reachable)
- Experiments must exist in the production database

Run with:
    uv run pytest tests/api/test_analyses_e2e.py -v -s

Timeout: each request can take several minutes while the SLURM job runs.
The default per-test timeout is 900 seconds (15 minutes).
"""

from __future__ import annotations

import os

import httpx
import pytest

PROD_BASE_URL = os.environ.get("ANALYSES_E2E_BASE_URL", "https://sms.cam.uchc.edu")
ENDPOINT = f"{PROD_BASE_URL}/api/v1/analyses"
TIMEOUT_SECONDS = 900  # 15 min — SLURM job may queue briefly


def _post_analysis(body: dict) -> httpx.Response:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        return client.post(ENDPOINT, json=body)


def _assert_valid_results(response: httpx.Response, experiment_id: str) -> None:
    assert response.status_code == 200, (
        f"[{experiment_id}] Expected 200, got {response.status_code}: {response.text[:500]}"
    )
    results = response.json()
    assert isinstance(results, list), f"[{experiment_id}] Response is not a list: {results}"
    assert len(results) > 0, f"[{experiment_id}] Response list is empty"

    for item in results:
        assert "filename" in item, f"[{experiment_id}] Missing 'filename' in result: {item}"
        assert "content" in item, f"[{experiment_id}] Missing 'content' in result: {item}"
        assert item["content"], f"[{experiment_id}] 'content' is empty for {item.get('filename')}"

    print(f"\n[{experiment_id}] OK — {len(results)} result(s):")
    for item in results:
        lines = item["content"].splitlines()
        print(
            f"  {item['filename']}  ({len(lines)} lines, variant={item.get('variant')}, "
            f"seed={item.get('lineage_seed')}, gen={item.get('generation')})"
        )


@pytest.mark.skipif(
    os.environ.get("SKIP_ANALYSES_E2E", "").lower() in ("1", "true", "yes"),
    reason="SKIP_ANALYSES_E2E is set",
)
def test_ptools_rna_sim3_test_677a() -> None:
    """ptools_rna single analysis on sim3-test-677a."""
    body = {
        "experiment_id": "sim3-test-677a",
        "single": [{"name": "ptools_rna", "n_tp": 16}],
    }
    print(f"\nPOST {ENDPOINT}")
    print(f"Body: {body}")
    response = _post_analysis(body)
    _assert_valid_results(response, "sim3-test-677a")


@pytest.mark.skipif(
    os.environ.get("SKIP_ANALYSES_E2E", "").lower() in ("1", "true", "yes"),
    reason="SKIP_ANALYSES_E2E is set",
)
def test_ptools_rna_sim3_test_45c5() -> None:
    """ptools_rna single analysis on sim3-test-45c5."""
    body = {
        "experiment_id": "sim3-test-45c5",
        "single": [{"name": "ptools_rna", "n_tp": 16}],
    }
    print(f"\nPOST {ENDPOINT}")
    print(f"Body: {body}")
    response = _post_analysis(body)
    _assert_valid_results(response, "sim3-test-45c5")
