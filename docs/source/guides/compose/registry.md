# Package Registry

*Available since v0.9.5*

The **package registry** subsystem lets users register `pbg-<tool>` packages
and other process-bigraph compatible Python packages in the sms-api database.
Once registered, the package's Process and Step classes appear in the
`/compose/v1/processes?source=db` and `/compose/v1/steps?source=db` endpoints,
making them available alongside the core process-bigraph library's built-in
registry.

## Concepts

| Term | Meaning |
|---|---|
| **Package** | A pip-installable Python library containing Process or Step subclasses |
| **Package registration** | Storing a package's metadata and compute outlines in the database |
| **Compute outline** | A description of a single Process or Step class (module, name, compute_type, inputs/outputs schema) |
| **Audit** | A dry-run check that a repo has the required `pyproject.toml`, `bigraph-schema` dependency, and `process-bigraph` dependency |

## Source modes

The `/compose/v1/processes` and `/compose/v1/steps` endpoints accept a `?source` query parameter:

| Source | Returns |
|---|---|
| `core` | Classes registered in the process-bigraph `core.link_registry` (in-memory) |
| `db` | Packages registered in the sms-api PostgreSQL database |
| `union` (default) | Both sources merged, deduplicated by `(module, name)` |

## CLI usage

### List registered packages

```bash
uv run atlantis compose packages
```

### Show a single package

```bash
uv run atlantis compose package-get 1
```

### Audit a repo (dry run)

Check whether a local directory or GitHub URL meets package requirements:

```bash
uv run atlantis compose package-audit /path/to/pbg-tool-repo
uv run atlantis compose package-audit https://github.com/vivarium-collective/pbg-cobra
```

### Register a package

Three modes:

```bash
# 1. From a local path (audits automatically)
uv run atlantis compose package-register /path/to/pbg-tool-repo

# 2. From a GitHub URL (audits automatically)
uv run atlantis compose package-register https://github.com/vivarium-collective/pbg-cobra

# 3. From an inline JSON outline (skip audit)
uv run atlantis compose package-register --from-file outline.json
```

The `--no-audit` flag skips the audit step and registers directly.
The `--ref` flag specifies a git branch/tag/commit for URL registration.

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/compose/v1/packages` | List all registered packages |
| `GET` | `/compose/v1/packages/{id}` | Get a single package by database ID |
| `POST` | `/compose/v1/packages/audit` | Dry-run audit of a repo without registering |
| `POST` | `/compose/v1/packages` | Register a package (repo URL, local path, or inline outline) |
| `GET` | `/compose/v1/processes?source=db` | List all registered processes from DB |
| `GET` | `/compose/v1/steps?source=db` | List all registered steps from DB |

### Register request format

```json
{
  "kind": "repo_url",
  "url": "https://github.com/vivarium-collective/pbg-cobra",
  "ref": "main"
}
```

```json
{
  "kind": "local_path",
  "path": "/path/to/pbg-tool-repo"
}
```

```json
{
  "kind": "outline",
  "outline": {
    "package_type": "pypi",
    "name": "my-custom-pkg",
    "compute": [
      {
        "module": "my_pkg.processes",
        "name": "MyProcess",
        "compute_type": "process",
        "inputs": "{}",
        "outputs": "{}"
      }
    ]
  }
}
```

## Auto-discovery from audit

When registering via `repo_url` or `local_path`, the system:

1. Clones (or resolves) the repository
2. Runs an audit: checks for `pyproject.toml`, `bigraph-schema` dependency, `process-bigraph` dependency
3. Scans Python source files for `class X(Process)` and `class Y(Step)` declarations
4. Auto-generates a compute outline from the discovered classes
5. Inserts the package into the database

This means any well-structured `pbg-<tool>` repo can be registered without
manually writing a compute outline.

## Duplicate detection

Registration is idempotent with respect to package **name** — if a package
with the same name already exists in the database, the server returns
`409 Conflict`. To update a package, delete and re-register (no
update-in-place endpoint yet).
