# ptools API Verification

**Endpoint:** `POST https://sms.cam.uchc.edu/api/v1/analyses`
**API version:** 0.9.3  |  **Verified:** 2026-05-11  |  **VPN required:** No

Reference: [Analysis Data Filtering Guide](https://sms-api.readthedocs.io/en/latest/guides/analysis-filtering.html)

---

## Request body schema

```json
{
  "experiment_id":    "<string, required>",
  "generation_start": "<int, optional — inclusive lower bound (default: 0)>",
  "generation_end":   "<int, optional — inclusive upper bound (default: last)>",
  "seeds":            "<list[int], optional — explicit lineage seeds to include>",
  "single": [
    { "name": "<module>", "n_tp": "<int>", "variant": "<int>" }
  ],
  "multiseed": [...],
  "multigeneration": [...]
}
```

Available module names: `ptools_rna`, `ptools_rxns`

---

## 1. Basic single-module request

`experiment_id: sim3-test-677a` — no filters, one module.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-677a",
    "single": [
      { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~31 s |

**Response** — array with one result object:

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t5\t10\t15\t21\t26\t31\t36\nEG10001\t0.0601\t0.0000\t0.3639\t0.3703\t0.2025\t0.1076\t0.8291\t0.2057\nEG10002\t1.0000\t0.6772\t1.0000\t0.7690\t0.8165\t1.1076\t1.1614\t1.7532\nEG10003\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.1772\t0.8892\n..."
  }
]
```

**Content field (TSV, first 3 data rows):**

| `$` (gene/rxn ID) | `0` | `5` | `10` | `15` | `21` | `26` | `31` | `36` |
|---|---|---|---|---|---|---|---|---|
| EG10001 | 0.0601 | 0.0000 | 0.3639 | 0.3703 | 0.2025 | 0.1076 | 0.8291 | 0.2057 |
| EG10002 | 1.0000 | 0.6772 | 1.0000 | 0.7690 | 0.8165 | 1.1076 | 1.1614 | 1.7532 |
| EG10003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1772 | 0.8892 |

> **WORKS** ✅

---

## 2. Two modules in one request

`experiment_id: sim3-test-45c5` — `ptools_rna` + `ptools_rxns` together.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-45c5",
    "single": [
      { "name": "ptools_rna",  "n_tp": 8, "variant": 0 },
      { "name": "ptools_rxns", "n_tp": 8, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~23 s |

**Response** — array with two result objects (one per module):

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t5\t10\t15\t21\t26\t31\t36\nEG10001\t0.0601\t0.0000\t0.3639\t...\n..."
  },
  {
    "filename":     "ptools_rxns.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t5\t10\t15\t21\t26\t31\t36\n1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN\t0.0000\t0.0000\t...\n..."
  }
]
```

**`ptools_rxns.tsv` content (first 3 data rows):**

| `$` (reaction ID) | `0` | `5` | `10` | `15` | `21` | `26` | `31` | `36` |
|---|---|---|---|---|---|---|---|---|
| 1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 1.1.1.127-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 1.1.1.215-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

> **WORKS** ✅

---

## 3. Filter by generation range

`experiment_id: sim3-test-677a` — restrict to generations 1–1.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id":    "sim3-test-677a",
    "generation_start": 1,
    "generation_end":   1,
    "single": [
      { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~2 s (data already cached from request 1) |

**Response** — same shape as request 1; only results whose `generation` falls in `[generation_start, generation_end]` are included. Requesting a range with no matching data (e.g. `generation_start: 2` on a 1-generation simulation) returns `[]`.

> **WORKS** ✅

---

## 4. Filter by seed

`experiment_id: sim3-test-45c5` — restrict to lineage seed 0 only.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-45c5",
    "seeds": [0],
    "single": [
      { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | ~15 s |

**Response** — only result objects whose `lineage_seed` matches the requested seeds are returned.

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t5\t10\t15\t21\t26\t31\t36\nEG10001\t0.0601\t...\n..."
  }
]
```

> **WORKS** ✅

---

## Parsing the response in JavaScript

```js
const res = await fetch("https://sms.cam.uchc.edu/api/v1/analyses", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    experiment_id: "sim3-test-677a",
    single: [{ name: "ptools_rna", n_tp: 8, variant: 0 }],
  }),
});

const results = await res.json(); // array — one item per module requested

for (const result of results) {
  const rows = result.content.split("\n").map(r => r.split("\t"));
  const header = rows[0]; // ["$", "0", "5", "10", ...]  — time point indices
  const data   = rows.slice(1); // [["EG10001", "0.0601", ...], ...]
  console.log(result.filename, result.lineage_seed, result.generation, data.length, "rows");
}
```

---

## Summary

| # | Request | Status | Wall time | Verdict |
|---|---|---|---|---|
| 1 | `single: [ptools_rna]`, no filters — `sim3-test-677a` | 200 | ~31 s | ✅ |
| 2 | `single: [ptools_rna, ptools_rxns]` — `sim3-test-45c5` | 200 | ~23 s | ✅ |
| 3 | `single: [ptools_rna]`, `generation_start/end: 1` — `sim3-test-677a` | 200 | ~2 s | ✅ |
| 4 | `single: [ptools_rna]`, `seeds: [0]` — `sim3-test-45c5` | 200 | ~15 s | ✅ |

All requests verified live against `https://sms.cam.uchc.edu` (v0.9.3) on 2026-05-11.
