# Plan for Todo #2: Simulation Search Filter

> **Status**: IMPLEMENTED — PR #163
> **Last updated**: 2026-07-10
> **Plan file**: `artifacts/plans/todo-2.md`

---

## Overview

Create a production-grade, lightweight filter mechanism for the `GET /api/v1/simulations` endpoint that allows users to filter simulations by experiment ID(s) or by predefined "tags" (named bundles of experiment IDs).

## Design Decisions

1. **Query parameters on GET, not a new HTTP method.** The QUERY method is not available in FastAPI. Query parameters are the standard approach and match existing patterns in this codebase.

2. **Two orthogonal filter parameters: `experiment_id` and `tag`.**

   - **`experiment_id`**: Comma-separated list of experiment IDs. Satisfies the "array of experiment IDs" use case.
   - **`tag`**: A single tag name that resolves to a predefined bundle of experiment IDs. Satisfies the "tag=cd1" use case.

3. **Tag registry as a Python dict, not a database table.** A dict is zero-migration, trivially extensible, and fully testable. If tags ever need to be dynamic/user-defined, that can be a follow-up.

4. **Both filters can be combined.** If both are specified, the result is the union of both sets.

5. **Backwards compatible.** When neither parameter is provided, behavior is identical to today.

## Implementation Steps

### Step 1: Create tag registry module
- **File**: `sms_api/simulation/simulation_tags.py` (new)
- Define `SIMULATION_TAGS` dict and `resolve_tag()` helper.

### Step 2: Add filter params to the list_simulations endpoint
- **File**: `sms_api/api/routers/sms.py`
- Add `experiment_id` and `tag` query parameters to `list_simulations()`.

### Step 3: Add filtered query method to DatabaseService
- **File**: `sms_api/simulation/database_service.py`
- Add `list_simulations_filtered(experiment_ids)` abstract method and SQL implementation.

### Step 4: Add handler for filtered list
- **File**: `sms_api/common/handlers/simulations.py`
- Add `list_simulations_filtered()` handler that resolves tags, parses experiment IDs, and calls the database service.

### Step 5: Add tags discovery endpoint
- **File**: `sms_api/api/routers/sms.py`
- Add `GET /api/v1/simulations/tags` to return available tags and their experiment IDs.

### Step 6: Update CLI simulation list command
- **File**: `app/cli.py`
- Add `--experiment-id` and `--tag` options.

### Step 7: Update app_data_service
- **File**: `app/app_data_service.py`
- Pass filter params in `submit_list_workflows()`.

### Step 8: Write tests
- **File**: `tests/api/ecoli/test_simulations.py` (add to existing)
- **File**: `tests/simulation/test_simulation_tags.py` (new)
- Test: filtered by experiment IDs, by tag, combined, no results, backwards compat, unknown tag error.

### Step 9: Regenerate OpenAPI spec and client
- Run `make spec` and `make api_client`.

### Step 10: Run quality checks
- Run `make check` and `uv run pytest`.

### Step 11: Add documentation
- Add a guide to `docs/source/guides/` for the new filter feature.

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `sms_api/simulation/simulation_tags.py` | **New** | Tag registry + resolve function |
| `sms_api/api/routers/sms.py` | Modify | Add filter params + tags endpoint |
| `sms_api/simulation/database_service.py` | Modify | Add filtered query method |
| `sms_api/common/handlers/simulations.py` | Modify | Add filtered list handler |
| `app/cli.py` | Modify | Add filter options to `simulation list` |
| `app/app_data_service.py` | Modify | Pass filter params |
| `sms_api/api/client/...` | Auto-gen | Regenerated |
| `sms_api/api/spec/...` | Auto-gen | Regenerated |
| `tests/api/ecoli/test_simulations.py` | Modify | Add filter tests |
| `tests/simulation/test_simulation_tags.py` | **New** | Tag registry unit tests |
| `docs/source/guides/simulation-filtering.md` | **New** | User-facing docs |

## Progress

- [x] Write plan to artifacts/plans/todo-2.md
- [x] Update todo.md to reference plan file
- [x] Step 1: Create tag registry module
- [x] Step 2: Add filter params to endpoint
- [x] Step 3: Add filtered query method to DatabaseService
- [x] Step 4: Add handler for filtered list
- [x] Step 5: Add tags discovery endpoint
- [x] Step 6: Update CLI simulation list command
- [x] Step 7: Update app_data_service
- [x] Step 8: Write tests
- [x] Step 9: Regenerate OpenAPI spec and client
- [x] Step 10: Run quality checks (`make check` passes, 9 filter tests pass)
- [ ] Step 11: Add documentation (readthedocs guide)
- [x] Commit, push, and open PR (#163)
