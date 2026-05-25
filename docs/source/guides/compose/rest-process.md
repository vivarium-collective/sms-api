# Process Runtime (REST-Process Mirror)

*Available since v0.9.3*

The **process runtime** subsystem exposes every class registered in the
process-bigraph `link_registry` as a stateful, UUID-keyed REST resource.
It mirrors the paradigm from
[rest-process](https://github.com/vivarium-collective/rest-process) —
a sketch that was always intended to inform this integration — and
implements it as a first-class API surface inside Atlantis with full
database persistence.

## Concepts

| Term | Meaning |
|---|---|
| **link_registry** | The dict populated by `allocate_core()` mapping process names → classes |
| **instance** | One live instantiation of a registered process, identified by a UUID |
| **update** | One timestep execution: call `process.update(state, interval)` |
| **end** | Terminate an instance and release its memory |
| **registry** | PostgreSQL audit trail of every initialize/update/end call |

The 42 bigraph-schema primitive types are exposed via `GET /compose/v1/types`.
The 11 registered processes from `pbsim_common` and `process_bigraph` are
each addressable by name.

## Quick Demo: MSEComparison

No SBML file needed. This walks through the full instance lifecycle.

```bash
BASE=https://sms.cam.uchc.edu

# 1. See what's registered
uv run atlantis compose list-types --base-url $BASE
uv run atlantis compose processes --base-url $BASE

# 2. Inspect config schema
uv run atlantis compose config-schema MSEComparison --base-url $BASE
# → {"ignore_nans": false, "columns_of_interest": []}

# 3. Initialize an instance
uv run atlantis compose init MSEComparison --base-url $BASE
# → Process ID: a3f1c2d4-...

# 4. Inspect its ports
uv run atlantis compose inputs MSEComparison a3f1c2d4-... --base-url $BASE
uv run atlantis compose outputs MSEComparison a3f1c2d4-... --base-url $BASE

# 5. Terminate
uv run atlantis compose end MSEComparison a3f1c2d4-... --base-url $BASE
```

## Registered Processes

Every process available in the live deployment:

| Name | Package | SBML required | Config fields |
|---|---|---|---|
| `MSEComparison` | `pbsim_common` | no | `ignore_nans`, `columns_of_interest` |
| `ComparisonTool` | `pbsim_common` | no | `ignore_nans`, `columns_of_interest` |
| `CopasiUTCStep` | `pbsim_common` | yes | `model_source`, `time`, `n_points`, `output_dir` |
| `CopasiUTCProcess` | `pbsim_common` | yes | `model_source`, `time`, `intervals` |
| `CopasiSteadyStateStep` | `pbsim_common` | yes | `model_source`, `time` |
| `TelluriumUTCStep` | `pbsim_common` | yes | `model_source`, `time`, `n_points`, `output_dir` |
| `TelluriumSteadyStateStep` | `pbsim_common` | yes | `model_source` |
| `TelluriumStep` | `pbsim_common` | no | *(none)* |
| `Step` | `process_bigraph` | no | *(none)* |
| `Process` | `process_bigraph` | no | *(none)* |
| `edge` | `bigraph_schema` | no | *(none)* |

## CLI Reference

```bash
# List all bigraph-schema type names (42 types)
uv run atlantis compose list-types --base-url <URL>

# Config schema for a named process or step
uv run atlantis compose config-schema <NAME> --base-url <URL>

# Instantiate; prints the UUID
uv run atlantis compose init <NAME> --base-url <URL>

# Inputs / outputs schemas for an active instance
uv run atlantis compose inputs <NAME> <UUID> --base-url <URL>
uv run atlantis compose outputs <NAME> <UUID> --base-url <URL>

# Run one update step
uv run atlantis compose update <NAME> <UUID> --base-url <URL>

# Terminate instance
uv run atlantis compose end <NAME> <UUID> --base-url <URL>
```

## REST API Reference

All endpoints are under `/compose/v1/`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/types` | List all bigraph-schema type names |
| `GET` | `/process/{name}/config-schema` | Config schema for a registered process or step |
| `POST` | `/process/{name}/initialize` | Create instance; returns `{"process_id": "<uuid>"}` |
| `GET` | `/process/{name}/inputs/{id}` | Inputs schema for an active instance |
| `GET` | `/process/{name}/outputs/{id}` | Outputs schema for an active instance |
| `POST` | `/process/{name}/update/{id}` | Run one update step |
| `POST` | `/process/{name}/end/{id}` | Terminate instance and release memory |

### Initialize request

```bash
curl -X POST https://sms.cam.uchc.edu/compose/v1/process/MSEComparison/initialize \
    -H "Content-Type: application/json" \
    -d '{"config": {"ignore_nans": false, "columns_of_interest": []}}'
```

Response:
```json
{"process_id": "a3f1c2d4-5678-90ab-cdef-1234567890ab"}
```

### Update request

```bash
curl -X POST https://sms.cam.uchc.edu/compose/v1/process/MSEComparison/update/a3f1c2d4-... \
    -H "Content-Type: application/json" \
    -d '{"state": {}, "interval": 1.0}'
```

## Process Registry (Persistence + Audit)

Every `initialize`, `update`, and `end` call is mirrored to PostgreSQL —
providing a full audit trail and cross-pod observability.

### Read-only registry endpoints

```bash
# All instances (optionally filter by status)
curl https://sms.cam.uchc.edu/compose/v1/process/instances
curl https://sms.cam.uchc.edu/compose/v1/process/instances?status=active
curl https://sms.cam.uchc.edu/compose/v1/process/instances?status=ended

# Full update history for a specific instance
curl https://sms.cam.uchc.edu/compose/v1/process/instances/<uuid>/history
```

### Database tables

| Table | Contents |
|---|---|
| `compose_process_instance` | One row per initialized instance (UUID, name, config, status, timestamps) |
| `compose_process_update` | One row per `update` call (instance FK, inputs, outputs, interval, timestamp) |

### Instance record shape

```json
{
    "process_id": "a3f1c2d4-...",
    "process_name": "MSEComparison",
    "config": {"ignore_nans": false, "columns_of_interest": []},
    "status": "ended",
    "created_at": "2026-05-11T14:30:00",
    "ended_at": "2026-05-11T14:30:45"
}
```

## Correspondence with rest-process

The Atlantis implementation maps directly to the
[rest-process](https://github.com/vivarium-collective/rest-process) sketch:

| rest-process endpoint | Atlantis equivalent |
|---|---|
| `GET /process_types` | `GET /compose/v1/types` |
| `POST /process/{name}` | `POST /compose/v1/process/{name}/initialize` |
| `GET /process/{name}/inputs/{id}` | `GET /compose/v1/process/{name}/inputs/{id}` |
| `GET /process/{name}/outputs/{id}` | `GET /compose/v1/process/{name}/outputs/{id}` |
| `PUT /process/{name}/update/{id}` | `POST /compose/v1/process/{name}/update/{id}` |
| `DELETE /process/{name}/{id}` | `POST /compose/v1/process/{name}/end/{id}` |

Atlantis extends this with:
- Full database persistence (audit trail, cross-pod observability)
- CLI commands (`atlantis compose init/inputs/outputs/update/end`)
- Registry read endpoints (`/process/instances`, `/process/instances/{id}/history`)
- Integration with the [PBG Live Sandbox](sandbox.md)
