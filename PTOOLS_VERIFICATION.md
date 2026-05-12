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

## 1. Cache hit — repeated identical request

`experiment_id: sim3-test-677a` — exactly the same params as a prior run
to confirm the server returns cached results instead of re-running the job.

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
| **Wall time** | **~0.5 s** (cache hit — same params were run earlier this session) |

**Response:**

```json
[
  {
    "filename":     "ptools_rna_v0_s0_g1.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t5\t10\t15\t21\t26\t31\t36\nEG10001\t0.0601\t0.0000\t0.3639\t0.3703\t0.2025\t0.1076\t0.8291\t0.2057\nEG10002\t1.0000\t0.6772\t1.0000\t0.7690\t0.8165\t1.1076\t1.1614\t1.7532\nEG10003\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.1772\t0.8892\n..."
  }
]
```

> Note: cached responses use a fully-qualified filename (`ptools_rna_v0_s0_g1.tsv`) rather than the bare name; data content is identical.

**TSV (first 3 rows):**

| `$` | `0` | `5` | `10` | `15` | `21` | `26` | `31` | `36` |
|---|---|---|---|---|---|---|---|---|
| EG10001 | 0.0601 | 0.0000 | 0.3639 | 0.3703 | 0.2025 | 0.1076 | 0.8291 | 0.2057 |
| EG10002 | 1.0000 | 0.6772 | 1.0000 | 0.7690 | 0.8165 | 1.1076 | 1.1614 | 1.7532 |
| EG10003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1772 | 0.8892 |

> **WORKS** ✅

---

## 2. Fresh run — two modules, new `n_tp` values

`experiment_id: sim3-test-45c5` — `ptools_rna` (`n_tp=11`) + `ptools_rxns` (`n_tp=6`).
Different `n_tp` from any prior run forces a fresh analysis job.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-45c5",
    "single": [
      { "name": "ptools_rna",  "n_tp": 11, "variant": 0 },
      { "name": "ptools_rxns", "n_tp": 6,  "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | **~35 s** (fresh run) |

**Response** — two result objects, one per module:

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t3\t7\t11\t15\t19\t22\t26\t30\t34\t38\nEG10001\t0.0000\t0.0826\t0.0000\t0.5000\t0.0565\t0.6681\t0.0652\t0.0000\t0.9000\t0.3870\t0.2838\n..."
  },
  {
    "filename":     "ptools_rxns.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t7\t14\t21\t28\t35\n1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\n..."
  }
]
```

**`ptools_rna.tsv` (n_tp=11 → 11 time-point columns):**

| `$` | `0` | `3` | `7` | `11` | `15` | `19` | `22` | `26` | `30` | `34` | `38` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EG10001 | 0.0000 | 0.0826 | 0.0000 | 0.5000 | 0.0565 | 0.6681 | 0.0652 | 0.0000 | 0.9000 | 0.3870 | 0.2838 |
| EG10002 | 1.0000 | 0.9739 | 0.5826 | 1.0000 | 0.9391 | 0.7424 | 0.6217 | 1.0261 | 1.4696 | 1.1043 | 1.9345 |
| EG10003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9435 | 0.5240 |

**`ptools_rxns.tsv` (n_tp=6 → 6 time-point columns):**

| `$` | `0` | `7` | `14` | `21` | `28` | `35` |
|---|---|---|---|---|---|---|
| 1-ACYLGLYCEROL-3-P-ACYLTRANSFER-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 1.1.1.127-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 1.1.1.215-RXN | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

> **WORKS** ✅

---

## 3. Fresh run — generation filter, `n_tp=13`

`experiment_id: sim3-test-677a` — restrict to generation 1 only; `n_tp=13` forces a fresh run.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id":    "sim3-test-677a",
    "generation_start": 1,
    "generation_end":   1,
    "single": [
      { "name": "ptools_rna", "n_tp": 13, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | **~16 s** (fresh run) |

**Response:**

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t3\t6\t9\t12\t16\t19\t22\t25\t29\t32\t35\t38\nEG10001\t0.0000\t0.0979\t0.0000\t0.1546\t0.4359\t0.1649\t0.6000\t0.1649\t0.0000\t0.4278\t0.8667\t0.2268\t0.3351\n..."
  }
]
```

**TSV (n_tp=13 → 13 time-point columns, first 3 rows):**

| `$` | `0` | `3` | `6` | `9` | `12` | `16` | `19` | `22` | `25` | `29` | `32` | `35` | `38` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EG10001 | 0.0000 | 0.0979 | 0.0000 | 0.1546 | 0.4359 | 0.1649 | 0.6000 | 0.1649 | 0.0000 | 0.4278 | 0.8667 | 0.2268 | 0.3351 |
| EG10002 | 1.0000 | 1.0000 | 0.4769 | 1.0000 | 1.0000 | 0.8402 | 0.7846 | 0.8247 | 0.7179 | 1.5876 | 1.0103 | 1.2320 | 1.9948 |
| EG10003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.3918 | 0.3454 |

> Note: requesting a range with no matching data (e.g. `generation_start: 2` on a 1-generation simulation) returns `[]`.

> **WORKS** ✅

---

## 4. Fresh run — seed filter, `n_tp=7`

`experiment_id: sim3-test-45c5` — restrict to lineage seed 0; `n_tp=7` forces a fresh run.

```bash
curl -s -X POST "https://sms.cam.uchc.edu/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "sim3-test-45c5",
    "seeds": [0],
    "single": [
      { "name": "ptools_rna", "n_tp": 7, "variant": 0 }
    ]
  }'
```

| | |
|---|---|
| **Status** | `200 OK` |
| **Wall time** | **~16 s** (fresh run) |

**Response:**

```json
[
  {
    "filename":     "ptools_rna.tsv",
    "variant":      0,
    "lineage_seed": 0,
    "generation":   1,
    "content":      "$\t0\t6\t12\t18\t24\t30\t36\nEG10001\t0.0525\t0.0000\t0.3186\t0.5014\t0.0000\t0.7729\t0.2271\nEG10002\t1.0000\t0.7175\t1.0000\t0.7978\t0.7535\t1.3213\t1.6593\nEG10003\t0.0000\t0.0000\t0.0000\t0.0000\t0.0000\t0.0305\t0.9030\n..."
  }
]
```

**TSV (n_tp=7 → 7 time-point columns, first 3 rows):**

| `$` | `0` | `6` | `12` | `18` | `24` | `30` | `36` |
|---|---|---|---|---|---|---|---|
| EG10001 | 0.0525 | 0.0000 | 0.3186 | 0.5014 | 0.0000 | 0.7729 | 0.2271 |
| EG10002 | 1.0000 | 0.7175 | 1.0000 | 0.7978 | 0.7535 | 1.3213 | 1.6593 |
| EG10003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0305 | 0.9030 |

> Only results whose `lineage_seed` matches the requested seed list are returned.

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

| # | Request | `n_tp` | Status | Wall time | Verdict |
|---|---|---|---|---|---|
| 1 | `ptools_rna`, no filters — `sim3-test-677a` | 8 (cached) | 200 | **~0.5 s** | ✅ cache hit |
| 2 | `ptools_rna` + `ptools_rxns` — `sim3-test-45c5` | 11, 6 (fresh) | 200 | ~35 s | ✅ |
| 3 | `ptools_rna`, `generation_start/end: 1` — `sim3-test-677a` | 13 (fresh) | 200 | ~16 s | ✅ |
| 4 | `ptools_rna`, `seeds: [0]` — `sim3-test-45c5` | 7 (fresh) | 200 | ~16 s | ✅ |

All requests verified live against `https://sms.cam.uchc.edu` (v0.9.3) on 2026-05-11.
