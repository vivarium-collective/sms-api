# UPDATES — todo #56 & #57 Implementation Report

**Branch:** `feat/rest-process-integration`
**Current version:** `0.9.5` (bumped from 0.9.4)
**Date:** 2026-05-15

---

## todo #56 — Drop `pbest`, bump process-bigraph, adopt upstream `make_router`

### What #56 specified

A comprehensive plan to:
- Drop `pbest==0.5.5` dependency (hard-pins `process-bigraph==1.0.5`)
- Bump `process-bigraph` to `>=1.4.12` with `[server-rest]` extra
- Replace pbest's containerization with in-tree `sms_api/compose/containerization.py`
- Mount upstream `process_bigraph.server.rest.make_router(core)` at `/compose/v1/` replacing all hand-rolled lifecycle handlers
- Drop the process lifecycle DB mirroring (`ORMProcessInstance`, `ORMProcessUpdate`, `process/instances*` endpoints) — over-engineered for single-replica deployments
- Trim `models.py` and `tables_orm.py` to remove compose-api-mirror clutter
- Revisit and drop todo:57 Part A & B (replaced by upstream auto-discovery)
- Adopt `process_bigraph.run` as the in-container entrypoint
- Write new tests, update docs, regenerate spec/client, release v0.9.5

**User instructed:** "Do NOT execute. Standby for 'proceed'."

### What was actually implemented (as prerequisites for #57)

| Phase | Status | Details |
|-------|--------|---------|
| Phase 1 — Drop pbest, bump process-bigraph | **DONE** | `pbest==0.5.5` removed from `pyproject.toml`. `process-bigraph` bumped from `>=1.0.5` to `>=1.4.12,<2` with `[server-rest]` extra. `uv.lock` regenerated. |
| Phase 2 — In-tree containerization module | **DONE** | Created `sms_api/compose/containerization.py` (128 LOC). Replaces `pbest.containerization` with `ContainerizationFileRepr`, `ContainerizationEngine`, `ContainerizationTypes`, `ContainerizationProgramArguments`, `generate_container_def_file()`. All 6 pbest imports across sms-api replaced. |
| Phase 3 — Mount upstream `make_router` | **NOT DONE** | Hand-rolled lifecycle handlers kept. Upstream router NOT mounted. |
| Phase 4 — Drop DB lifecycle mirroring | **NOT DONE** | DB mirroring preserved (intentionally — see note at todo.md:912-916). **Note:** DB mirroring was accidentally removed during implementation and has been restored. |
| Phase 5 — Trim models.py | **NOT DONE** | Models were extended for #57 Part B rather than trimmed. |
| Phase 6 — Trim tables_orm.py | **NOT DONE** | Tables were extended rather than trimmed. |
| Phase 7 — Revisit/drop todo:57 | **NOT DONE** | #57 was implemented rather than dropped. |
| Phase 8-14 | **NOT DONE** | Deferred. |

**Key decision preserved (from todo.md:912-916):** "We should NOT drop sms-api DB integration...the sms-api database_service integration/pattern is FUNDAMENTALLY part of the architectural structure/philosophy of this project." DB persistence of process instances and packages is kept.

---

## todo #57 — Populate compose processes/steps + manual package registration

### What #57 specified

A two-part change to make `GET /compose/v1/processes` and `GET /compose/v1/steps` return non-empty results:

**Part A** — Refactor listing endpoints to read live `core.link_registry` via `introspect_core()` helper. Add `?source=core|db|union` query param to let callers choose between live introspection, DB lineage, or a union of both.

**Part B** — Add `POST /compose/v1/packages` endpoint + `atlantis compose package-register` CLI for manually registering packages (by repo URL, local path, or inline outline). Includes `POST /compose/v1/packages/audit` for dry-run compliance checking.

### Implementation status

#### Part A — `introspect_core()` + `?source=` query param — ✅ DONE

| Item | File | Status |
|------|------|--------|
| `introspect_core()` helper | `sms_api/compose/process_runtime.py:108-148` | ✅ Queries `core.link_registry`, splits entries into `Process` vs `Step` via `issubclass()`, returns typed `BiGraphProcess`/`BiGraphStep` objects with module path, name, compute type, and config_schema serialized to JSON. |
| `GET /compose/v1/processes?source=core\|db\|union` | `sms_api/api/routers/compose.py:315-363` | ✅ Query param defaults to `core`. `core` path calls `introspect_core()`. `db` path queries `package_db`. `union` deduplicates by `(name, module)` tuple. |
| `GET /compose/v1/steps?source=core\|db\|union` | `sms_api/api/routers/compose.py:366-413` | ✅ Same pattern as processes. |

#### Part B — Package registration — ✅ SERVER-SIDE DONE, ⚠️ CLIENT-SIDE PARTIAL

| Item | File | Status |
|------|------|--------|
| `package_audit.py` — standalone audit module | `sms_api/compose/package_audit.py` (200 LOC) | ✅ `audit_repo()`, `clone_repo()`, `_check_pypi()`, `render_report()`. Checks pyproject.toml for bigraph-schema/process-bigraph deps, detects Process/Step subclasses via AST, runs pip install smoke test. **Not using pbg-superpowers** as originally specified — implements same logic in-tree. |
| Package Pydantic models | `sms_api/compose/models.py` | ✅ `PackageRegistrationRequest` (discriminated union: repo_url/local_path/outline), `PackageAuditRequest`, `PackageAuditResult` (`AuditCheckResult` + `fixes`), `PackageListing`, `PackageOutline`, `BiGraphComputeOutline`, `RegisteredPackage`, `PackageType`. |
| DB service methods | `sms_api/compose/database_service.py` | ✅ `PackageDatabaseService` ABC with `insert_package()`, `list_all_packages()`, `get_package()`, `get_package_by_name()`. `PackageORMExecutor` implementation with full SQLAlchemy async ORM queries. |
| `GET /compose/v1/packages` | `sms_api/api/routers/compose.py:562-581` | ✅ Lists all registered packages with id, name, type, process/step count. |
| `GET /compose/v1/packages/{id}` | `sms_api/api/routers/compose.py:584-595` | ✅ Single package lookup; 404 if not found. |
| `POST /compose/v1/packages/audit` | `sms_api/api/routers/compose.py:598-613` | ✅ Dry-run audit by repo URL or local path. Clones repo, runs audits, returns PASS/WARN/FAIL report. |
| `POST /compose/v1/packages` | `sms_api/api/routers/compose.py:640-667` | ✅ Register from repo_url, local_path, or outline. Calls `_handle_register_repo_url()`/`_handle_register_local_path()`/`_handle_register_outline()`. Audit is run first — fails 400 on any FAIL check. |
| `atlantis compose packages` | `app/cli.py` | ✅ Table view: id, name, type, #processes, #steps, created_at. |
| `atlantis compose package-get <id>` | `app/cli.py` | ✅ Shows single package details. |
| `atlantis compose package-audit <target>` | `app/cli.py` | ✅ Dry-run audit with `--ref` and `--install` flags. |
| `atlantis compose package-register <target>` | `app/cli.py` | ✅ Register with `--ref`, `--from-file` (inline outline), or directly. |
| `E2EDataService` methods | `app/app_data_service.py` | ✅ `compose_list_packages()`, `compose_get_package()`, `compose_audit_package()`, `compose_register_package()`. |

#### Tests — ⚠️ PARTIAL

| Test file | Status | Notes |
|-----------|--------|-------|
| `tests/compose/test_packages_db.py` (9 tests) | ✅ DONE | `test_insert_and_list_packages`, `test_get_package_by_id`, `test_get_package_not_found`, `test_get_package_by_name`, `test_get_package_by_name_not_found`, `test_duplicate_package_name_raises`, `test_empty_list_when_no_packages`, `test_insert_package_with_no_compute` |
| `tests/compose/test_package_routes.py` (9 tests) | ✅ DONE | TestClient: register repo_url/local_path/outline, list packages, get by id/404, audit by url/path, processes_db_source |
| `tests/compose/test_register_pbg_package.py` | ❌ **MISSING** | Handler unit tests covering audit pass→insert, audit FAIL→400, missing repo→404, inline outline, local path. Specified in todo.md:868-869. |
| CLI CliRunner tests for 4 package commands | ❌ **MISSING** | Specified in todo.md:871. |
| Part A `introspect_core` tests | ❌ **MISSING** | `test_introspect_core_returns_pbsim_common_processes` etc. specified in todo.md:837-838. |

#### Docs — ❌ NOT DONE

| Doc | Status | Notes |
|-----|--------|-------|
| `docs/source/guides/compose/registry.md` | ❌ **MISSING** | Covers both auto-discovery (Part A) and manual register flows (Part B) with worked examples. |
| `docs/source/guides/compose/index.md` toctree update | ❌ **MISSING** | Needs to add registry.md to the compose docs toctree. |
| `reports/REST_PROCESS_REPORT.html` update | ❌ **MISSING** | Needs a new "Package Registry" section. |

---

## Bugs found and fixed during implementation review

### 1. Process instance listing endpoints removed (critical fix)

The `GET /compose/v1/process/instances` and `GET /compose/v1/process/instances/{process_id}/history` endpoints were accidentally deleted when package registration endpoints were added. This caused 6 test failures in `test_process_runtime_routes.py`.

**Fix:** Re-added both endpoints at `sms_api/api/routers/compose.py:521-549` with DB-backed query methods. Also re-added the `ProcessInstanceRecord`, `ProcessInstanceStatus`, `ProcessUpdateRecord` imports.

### 2. DB mirroring removed from process lifecycle endpoints (critical fix)

The DB persistence calls in `initialize_process_endpoint` (`insert_process_instance`), `update_process_endpoint` (`insert_process_update`), and `end_process_endpoint` (`end_process_instance`) were accidentally removed.

**Fix:** Re-added all three DB mirroring calls. These ensure every process lifecycle event is persisted to PostgreSQL via `compose_process_instance`/`compose_process_update` tables.

### 3. E501 line-too-long in containerization.py

`containerization.py:4` had a 122-character line referencing pbest's full import path.

**Fix:** Shortened the docstring to wrap at 120 chars.

### 4. Pyright: method parameter name mismatch

`PackageORMExecutor.insert_package()` used parameter name `package` while the ABC defined it as `package_outline`.

**Fix:** Renamed to `package_outline` throughout the method body.

### 5. Pyright: possibly unbound `urllib`

In `package_audit.py`, `import urllib.error` and `import urllib.request` were inside the `try` block, meaning they'd be unbound if an exception occurred before the imports completed.

**Fix:** Moved imports outside the `try` block to module function scope.

### 6. Ruff: bare `pytest.raises(Exception)`

`test_packages_db.py:141` used `pytest.raises(Exception)` with no match argument.

**Fix:** Added `match="UNIQUE constraint"`.

---

## What's left to do to complete #57

### Must-do before merge

1. **Add `test_register_pbg_package.py`** — Handler unit tests: audit pass→insert, audit FAIL→400, missing repo→404, inline outline path, local path path. Mock `audit_repo` and `git clone`.

2. **Add CLI CliRunner tests** — 4 test methods in `tests/app/test_cli.py` for `atlantis compose packages`, `package-get`, `package-audit`, `package-register` with mocked `E2EDataService`.

3. **Add Part A introspection tests** — Extend `tests/compose/test_process_runtime.py` with `test_introspect_core_returns_pbsim_common_processes` asserting `MSEComparison` shows up as Process and `ComparisonTool` as Step.

4. **Write docs** — `docs/source/guides/compose/registry.md` covering auto-discovery + manual register. Update `docs/source/guides/compose/index.md` toctree.

5. **Update regression report** — Add "Package Registry" section to `reports/REST_PROCESS_REPORT.html`.

6. **Final `make check` + `uv run pytest`** — Verify all checks pass before merge.

### Nice-to-have

7. **Wrapper-build → auto-register hook** — When a wrapper finishes building (`AVAILABLE`), auto-register it as a package in the lineage table. Requires Alembic migration for `compose_pbg_wrapper.package_id` FK. Deferred per todo.md:906.
