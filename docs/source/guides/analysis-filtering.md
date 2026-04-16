# Analysis Data Filtering

*Available since v0.7.7*

The `POST /api/v1/analyses` endpoint supports optional filtering parameters that let you
restrict which generations and seeds are included in an analysis run. This is useful when
you want results for a specific subset of your simulation data — for example, skipping
early generations or isolating a single seed.

## Filter Parameters

There are two ways to filter:

1. **Top-level filters** — applied at the dataset level before any analysis module runs:

   | Parameter          | Type         | Description                                      |
   |--------------------|--------------|--------------------------------------------------|
   | `generation_start` | `int`        | Inclusive lower bound for generations (default: 0) |
   | `generation_end`   | `int`        | Inclusive upper bound for generations (default: last) |
   | `seeds`            | `list[int]`  | Explicit list of lineage seeds to include          |

2. **Per-module filters** — specified inside each module config entry:

   | Parameter      | Type   | Description                          |
   |----------------|--------|--------------------------------------|
   | `generation`   | `int`  | Restrict to a single generation      |
   | `lineage_seed` | `int`  | Restrict to a single seed            |
   | `variant`      | `int`  | Restrict to a single variant index   |

```{important}
Use the **`single`** analysis type when you need filtered results.
`multiseed` aggregates across all seeds and generations by design and does not
apply generation or seed filters to its output.
```

## Examples

All examples below use `POST /api/v1/analyses` with experiment `sim3-test-5062`
(3 seeds, 10 generations).

### No filters (backwards compatible)

Returns aggregated data across all seeds, generations, and variants:

```json
{
  "experiment_id": "sim3-test-5062",
  "multiseed": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Generation range

Analyze only generations 2 through 5 (inclusive):

```json
{
  "experiment_id": "sim3-test-5062",
  "generation_start": 2,
  "generation_end": 5,
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Skip first N generations

Exclude generations 0–2, analyze generation 3 onward:

```json
{
  "experiment_id": "sim3-test-5062",
  "generation_start": 3,
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Single generation

Analyze only generation 5:

```json
{
  "experiment_id": "sim3-test-5062",
  "generation_start": 5,
  "generation_end": 5,
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Single seed

Analyze only seed 0:

```json
{
  "experiment_id": "sim3-test-5062",
  "seeds": [0],
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Per-module generation filter

The `generation` and `lineage_seed` fields can also be specified directly inside
the module config. Here, seed 0 and generation 3:

```json
{
  "experiment_id": "sim3-test-5062",
  "seeds": [0],
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0, "generation": 3 }
  ]
}
```

### Combined top-level filters

Generations 3 onward, from seeds 0 and 2 only:

```json
{
  "experiment_id": "sim3-test-5062",
  "generation_start": 3,
  "seeds": [0, 2],
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ]
}
```

### Multiple modules in one request

Run `ptools_rna` and `ptools_rxns` together with the same generation filter:

```json
{
  "experiment_id": "sim3-test-5062",
  "generation_start": 2,
  "generation_end": 8,
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 },
    { "name": "ptools_rxns", "n_tp": 8, "variant": 0 }
  ]
}
```

### Mixed analysis types

Combine a filtered `single` analysis with an unfiltered `multiseed` analysis
in one request. Top-level filters apply to all types, but only `single` reflects
them in output:

```json
{
  "experiment_id": "sim3-test-5062",
  "seeds": [0],
  "single": [
    { "name": "ptools_rna", "n_tp": 8, "variant": 0 }
  ],
  "multiseed": [
    { "name": "ptools_rxns", "n_tp": 8, "variant": 0 }
  ]
}
```

## Notes

- **`single`** runs the analysis per seed/generation/agent combination individually.
  Returns one TSV per combination. Use this when filtering.
- **`multiseed`** aggregates across all seeds into a single result. Use this for the
  default cross-seed summary when no filtering is needed.
- All filter parameters are optional. Omit them entirely for the full dataset.
- `generation_start` and `generation_end` are inclusive on both ends.
- No breaking changes to existing API calls.
