# PBG Wrapper Generation

*Available since v0.9.3*

The **wrapper generation** subsystem lets users programmatically create
`pbg-<tool>` packages — process-bigraph wrappers for arbitrary simulator
repositories — via a REST API and CLI, without writing Python by hand.

## Concept

A `pbg-<tool>` package is a pip-installable Python library that wraps a
simulator in the process-bigraph port/update interface, making it
composable with any other registered process. The wrapper generation pipeline:

```text
User submits GitHub repo URL
        │
        ▼
Claude agent (pbg-expert skill)
  reads SKILL.md as system prompt
  explores repo, writes pbg-<tool>/ package
        │
        ▼
Bundle tarball → store in FileService (S3/GCS/Qumulo)
        │
        ▼
Generate Singularity .def → SCP to HPC → SLURM build job
        │
        ▼
Wrapper status: GENERATING → BUILDING → AVAILABLE (or FAILED)
```

## Quick Start

```bash
BASE=https://sms.cam.uchc.edu

# Submit a wrapper generation job
uv run atlantis compose wrapper-create \
    https://github.com/vivarium-collective/mem3dg \
    --base-url $BASE

# Poll until available/failed
uv run atlantis compose wrapper-create \
    https://github.com/vivarium-collective/mem3dg \
    --poll \
    --base-url $BASE

# Check status of a specific wrapper
uv run atlantis compose wrapper-status 1 --base-url $BASE

# List all wrappers (optionally filter by status)
uv run atlantis compose wrapper-list --base-url $BASE
uv run atlantis compose wrapper-list --status available --base-url $BASE
```

## Status Lifecycle

| Status | Meaning |
|---|---|
| `generating` | Claude agent is writing the `pbg-<tool>` package |
| `building` | Singularity container build job running on SLURM |
| `available` | Container built and registered; wrapper ready to use |
| `failed` | Generation or build failed; see `error_message` field |

## CLI Reference

### `wrapper-create`

```
uv run atlantis compose wrapper-create <REPO_URL> [OPTIONS]

Arguments:
  REPO_URL          GitHub URL of the simulator to wrap

Options:
  --tool-name TEXT       Override the tool name (default: derived from repo)
  --ref TEXT             Git ref/branch/tag (default: main)
  --instructions TEXT    Extra instructions for the agent
  --poll                 Wait until status reaches available or failed
  --base-url TEXT        API server URL
```

### `wrapper-status`

```
uv run atlantis compose wrapper-status <WRAPPER_ID> [OPTIONS]

Arguments:
  WRAPPER_ID    Database ID of the wrapper

Options:
  --base-url TEXT    API server URL
```

### `wrapper-list`

```
uv run atlantis compose wrapper-list [OPTIONS]

Options:
  --status TEXT      Filter by status (generating/building/available/failed)
  --base-url TEXT    API server URL
```

## REST API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/compose/v1/wrappers` | Submit wrapper generation job |
| `GET` | `/compose/v1/wrappers/{id}/status` | Get wrapper status and detail |
| `GET` | `/compose/v1/wrappers` | List wrappers (optional `?status=` filter) |

### Submit request body

```json
{
    "source_repo_url": "https://github.com/vivarium-collective/mem3dg",
    "tool_name": "mem3dg",
    "source_ref": "main",
    "extra_instructions": "focus on the membrane model"
}
```

### Response

```json
{
    "wrapper_id": 1,
    "tool_name": "mem3dg",
    "source_repo_url": "https://github.com/vivarium-collective/mem3dg",
    "source_ref": "main",
    "status": "generating",
    "simulator_id": null,
    "storage_uri": null,
    "error_message": null,
    "created_at": "2026-05-11T13:14:44"
}
```

## Configuration

To enable agent-based wrapper generation, set the Anthropic API key in the
deployment's `shared-secrets` SealedSecret:

```
COMPOSE_PBG_ANTHROPIC_API_KEY=sk-ant-...
```

Without this key, submitted jobs immediately transition to `failed` with
`error_message: "COMPOSE_PBG_ANTHROPIC_API_KEY is not configured"`. The
full pipeline (DB record, background task, status transitions, error surfacing)
works end-to-end; only the agent call is gated on the key.

Optional configuration:

| Env var | Default | Description |
|---|---|---|
| `COMPOSE_PBG_WRAPPERS_STORAGE_PREFIX` | `compose/wrappers` | S3/GCS key prefix for stored tarballs |
| `COMPOSE_PBG_EXPERT_SKILL_PATH` | *(built-in SKILL.md)* | Override path to custom skill prompt |

## Database

Wrapper state is persisted in the `compose_pbg_wrapper` table:

| Column | Type | Description |
|---|---|---|
| `id` | int | Database ID |
| `tool_name` | str | Derived tool name (e.g. `mem3dg`) |
| `source_repo_url` | str | GitHub URL submitted |
| `source_ref` | str | Git ref |
| `status` | enum | `generating / building / available / failed` |
| `simulator_id` | int FK | Linked `compose_pbg_wrapper` simulator once built |
| `storage_uri` | str | S3/GCS URI of the stored tarball |
| `error_message` | str | Failure reason if status=failed |
| `created_at` | datetime | Submission timestamp |
