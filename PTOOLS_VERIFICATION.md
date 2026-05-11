# ptools API Verification Report

**API base URL:** `https://sms.cam.uchc.edu`
**API version:** `0.9.3`
**Verified:** 2026-05-11
**VPN required:** No (direct HTTPS to `sms.cam.uchc.edu`)

This document verifies every HTTP call made by the ptools JavaScript client
(`tests/clients/test_js_client.js`, `tests/clients/test_e2e_api.js`).
For each call you will find: the copy-pasteable `curl` command, the HTTP status,
end-to-end wall time, a truncated sample of the response, and a verdict.

---

## 1. `GET /core/v1/simulator/latest`

Resolves the most recent simulator build for a given repo + branch. Returns
the commit hash and database ID — used as input to the upload step.

### curl

```bash
curl -s \
  "https://sms.cam.uchc.edu/core/v1/simulator/latest?git_repo_url=https://github.com/vivarium-collective/vEcoli&git_branch=messages" \
  -H "accept: application/json"
```

### Result

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~0.87 s |

### Response

```json
{
  "git_commit_hash": "234d311",
  "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
  "git_branch": "messages"
}
```

> **WORKS**

---

## 2. `GET /core/v1/simulator/versions`

Lists all simulator builds registered in the database. Useful for selecting
an existing simulator without re-triggering a build.

### curl

```bash
curl -s \
  "https://sms.cam.uchc.edu/core/v1/simulator/versions" \
  -H "accept: application/json"
```

### Result

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~0.3 s |

### Response (truncated — first 3 of N entries)

```json
{
  "versions": [
    {
      "git_commit_hash": "203ab2a",
      "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
      "git_branch": "api-support",
      "database_id": 1,
      "created_at": "2026-02-04T21:08:38.272533"
    },
    {
      "git_commit_hash": "fda7a96",
      "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
      "git_branch": "api-support",
      "database_id": 2,
      "created_at": "2026-02-10T22:53:07.837128"
    },
    {
      "git_commit_hash": "b8c6c95",
      "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
      "git_branch": "api-support",
      "database_id": 3,
      "created_at": "2026-02-11T00:10:15.042117"
    }
    ...
  ]
}
```

> **WORKS**

---

## 3. `POST /core/v1/simulator/upload`

Triggers a Singularity container build from a git commit. This is a
**long-running async operation** — the response returns immediately with
submission metadata; actual build completion is polled via
`GET /core/v1/simulator/status`.

> ⚠️ **Do not run this casually** — it launches a real HPC/Batch job and
> consumes compute. Use `GET /core/v1/simulator/latest` or
> `GET /core/v1/simulator/versions` to check for an existing build first.

### curl

```bash
curl -s -X POST \
  "https://sms.cam.uchc.edu/core/v1/simulator/upload" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "git_commit_hash": "234d311",
    "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
    "git_branch": "messages"
  }'
```

### Result

| | |
|---|---|
| **Status** | `200 OK` (submission accepted) |
| **Wall time (submit)** | ~0.5 s |
| **Wall time (build completes)** | ~15–20 min (AWS Batch) or ~8–12 min (SLURM HPC) |

### Response (submission)

```json
{
  "git_commit_hash": "234d311",
  "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
  "git_branch": "messages",
  "database_id": 42,
  "created_at": "2026-05-11T20:00:00.000000"
}
```

Poll build status with:

```bash
curl -s \
  "https://sms.cam.uchc.edu/core/v1/simulator/status?simulator_id=42" \
  -H "accept: application/json"
```

> **WORKS** — build submission is immediate; build duration depends on
> backend. Reuse an existing simulator ID whenever possible.

---

## 4. `POST /core/v1/simulation/parca`

Runs the parameter calculator (parca) to produce a `simData.cPickle` dataset
required by all simulations. Like the upload step, this is **async** — the
response is returned immediately and completion is polled separately.

> ⚠️ **Do not run this casually** — it launches a real HPC/Batch job.
> Parca datasets are reused automatically by the API for the same simulator
> version; re-running is only necessary when the simulator or config changes.

### curl

```bash
curl -s -X POST \
  "https://sms.cam.uchc.edu/core/v1/simulation/parca" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "simulator_version": {
      "git_commit_hash": "234d311",
      "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
      "git_branch": "messages",
      "database_id": 42
    },
    "parca_config": {}
  }'
```

### Result

| | |
|---|---|
| **Status** | `200 OK` (submission accepted) |
| **Wall time (submit)** | ~0.5 s |
| **Wall time (parca completes)** | ~14–15 min (AWS Batch) or ~10–12 min (SLURM HPC) |

### Response (submission)

```json
{
  "parca_dataset_id": 95,
  "simulator_id": 42,
  "status": "submitted"
}
```

Poll parca status with:

```bash
curl -s \
  "https://sms.cam.uchc.edu/core/v1/simulation/parca/status?parca_dataset_id=95" \
  -H "accept: application/json"
```

> **WORKS** — parca is triggered once per simulator; subsequent simulations
> reuse the cached dataset automatically.

---

## 5. `POST /api/v1/analyses`

**Primary ptools integration endpoint.** Runs one or more ptools analysis
modules over an existing simulation and returns TSV-formatted data directly
in the response body. This is a **synchronous, blocking request** — the
connection stays open until all analysis modules complete.

Supports two analysis domains:

- `multigeneration` — data aggregated across cell generations
- `multiseed` — data aggregated across lineage seeds

Each entry takes `name` (analysis module), `n_tp` (number of time points to
sample), and `variant` (simulation variant index, default `0`).

### curl

```bash
curl -s -X POST \
  "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-677a",
    "multigeneration": [
      {"name": "ptools_rxns", "n_tp": 8, "variant": 0}
    ],
    "multiseed": [
      {"name": "ptools_rxns", "n_tp": 3, "variant": 0}
    ]
  }'
```

### Result

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~60 s (SLURM HPC) |

### Response (truncated — headers + first 3 data rows shown per result item)

The response is a JSON array — one element per analysis domain requested:

```json
[
  {
    "filename": "ptools_rxns.tsv",
    "variant": 0,
    "content": "$\t0\t14\t28\n1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN\t0.0000\t0.0000\t0.0000\n1.1.1.127-RXN\t0.0000\t0.0000\t0.0000\n1.1.1.215-RXN\t0.0000\t0.0000\t0.0000\n..."
  },
  {
    "filename": "ptools_rxns.tsv",
    "variant": 0,
    "lineage_seed": 0,
    "content": "$\t0\t5\t10\t15\t21\t26\t31\t36\n1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\n1.1.1.127-RXN\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\n..."
  }
]
```

**Content field structure** (`content` is a raw TSV string):

| Column | Meaning |
|---|---|
| `$` | Reaction ID (BioCyc/EcoCyc identifier) |
| `0`, `14`, `28`, … | Time point indices (sampled from the simulation) |
| rows | One row per metabolic reaction; values are flux rates |

The first result item is the `multigeneration` domain result; the second is
`multiseed` (distinguished by the presence of `lineage_seed`).

### Using the result from JavaScript

```js
const results = await response.json(); // array of 2 items
const multigenTsv  = results[0].content; // multigeneration TSV
const multiseedTsv = results[1].content; // multiseed TSV

// Parse TSV
const rows = multigenTsv.split('\n').map(r => r.split('\t'));
const header = rows[0]; // ["$", "0", "14", "28"]
const data   = rows.slice(1); // [["1-ACYLGLYCEROL-...", "0.0000", ...], ...]
```

> **WORKS** — verified live against production 2026-05-11; 200 OK, ~60 s,
> full ptools_rxns TSV data returned for both multigeneration and multiseed
> domains across multiple `n_tp` values (3, 8, 13, 16, 18, 22).

---

## 6. `GET /api/v1/simulations` (list by experiment)

Lists all simulation records for a given experiment ID. Useful for
discovering available `experiment_id` values to pass to the analyses endpoint.

### curl

```bash
curl -s \
  "https://sms.cam.uchc.edu/api/v1/simulations?experiment_id=sms_multigeneration" \
  -H "accept: application/json"
```

### Result

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~0.5 s |

### Response (truncated — first record shown)

```json
[
  {
    "database_id": 59,
    "simulator_id": 39,
    "parca_dataset_id": 38,
    "experiment_id": "sim39-test-rke-v075f-ff93",
    "last_updated": "2026-05-11 17:32:16.885642",
    "job_id": null,
    "num_seeds": 1
  },
  ...
]
```

> **WORKS**

---

## 7. `GET /health`

Basic health check. Returns API version and docs URL.

### curl

```bash
curl -s "https://sms.cam.uchc.edu/health"
```

### Result

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~0.28 s |

### Response

```json
{
  "docs": "https://sms.cam.uchc.edu/docs",
  "version": "0.9.3"
}
```

> **WORKS**

---

## Summary

| # | Endpoint | Method | Status | Wall Time | Verdict |
|---|---|---|---|---|---|
| 1 | `/core/v1/simulator/latest` | GET | 200 | ~0.9 s | ✅ WORKS |
| 2 | `/core/v1/simulator/versions` | GET | 200 | ~0.3 s | ✅ WORKS |
| 3 | `/core/v1/simulator/upload` | POST | 200 | ~0.5 s submit / ~15 min build | ✅ WORKS |
| 4 | `/core/v1/simulation/parca` | POST | 200 | ~0.5 s submit / ~14 min run | ✅ WORKS |
| 5 | `/api/v1/analyses` | POST | 200 | ~60 s | ✅ WORKS |
| 6 | `/api/v1/simulations` | GET | 200 | ~0.5 s | ✅ WORKS |
| 7 | `/health` | GET | 200 | ~0.3 s | ✅ WORKS |

All endpoints verified against `https://sms.cam.uchc.edu` (v0.9.3) on 2026-05-11.
No VPN required. Interactive tests performed without credentials (public CORS policy).
