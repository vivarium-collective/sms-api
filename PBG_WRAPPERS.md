# PBG Wrappers: pbg-superpowers Integration & REST API Plan

This document covers two things:
1. How to install `pbg-superpowers` skills into Claude Code
2. A design plan for exposing pbg-expert wrapper generation as a first-class sms-api REST workflow, reachable via the Atlantis CLI

---

## Part 1: Installing pbg-superpowers into Claude Code

### What is pbg-superpowers?

`pbg-superpowers` is a Claude Code plugin (`../pbg-superpowers/plugin.yaml`, v0.3.0) that adds six user-invocable skills for building process-bigraph research projects. The plugin lives at `../pbg-superpowers/` and consists of:

- **`plugin.yaml`** — declares the plugin name, version, and skill list
- **`skills/`** — one `SKILL.md` per skill; each is a self-contained prompt + protocol Claude reads when you invoke that skill
- **`pbg_superpowers/`** — Python package with scaffold helpers, schema validators, workspace YAML management, and a CLI (`pbg-scaffold`)
- **`templates/`** — Jinja2 templates for model repos (`pbg_<model>/`, tests, pyproject, demo, CI)
- **`server/`** — optional local dashboard server (Python + Node.js)

### The Six Skills

| Skill | Invocation | What it does |
|---|---|---|
| `pbg-workspace` | `/pbg-workspace <name>` | Clones `pbg-template`, runs `template-init.sh`, scaffolds a research workspace |
| `pbg-server` | `/pbg-server start\|stop\|status` | Starts a local dashboard server for live phase-tracker updates |
| `pbg-report` | `/pbg-report` | Regenerates `reports/index.html` dashboard after manual state changes |
| `pbg-phase` | `/pbg-phase <n>` | Drives implementation phase n: walks tasks, dispatches `/pbg-expert` if needed, writes code + tests, runs gate |
| **`pbg-expert`** | `/pbg-expert <tool or GitHub URL>` | **Wraps a single simulator as a `pbg-<tool>` package** (primary skill for our use case) |
| `pbg-composer` | `/pbg-composer <name> <tools...>` | Composes two or more `pbg-*` wrappers into a `pbg-composite-<name>` repo |

### Installation Steps

From inside Claude Code (any project):

```
/plugin install pbg-superpowers
/reload-plugins
```

That's it. After reload, all six skills are available as `/pbg-*` slash commands.

**To point at the local clone** (during development, rather than fetching from a registry):

```bash
# The plugin is at ../pbg-superpowers relative to sms-api.
# Symlink or reference it as needed per your Claude Code plugin resolution path.
```

The `pbg_superpowers` Python package itself can be installed into any venv independently:

```bash
uv pip install -e ../pbg-superpowers
# exposes: pbg-scaffold CLI + pbg_superpowers.scaffold module
```

### The pbg-expert Skill in Detail

When you invoke `/pbg-expert <tool-name or GitHub URL>`, Claude:

1. **Phase 1 — Study the tool**: reads source, docs, examples; identifies inputs/outputs/parameters/time model
2. **Phase 2 — Design the wrapper**: decides `Step` vs `Process`; designs port schemas; chooses bridge or direct pattern
3. **Phase 3 — Implement**: creates `pbg-<tool>/` with `processes.py`, `types.py`, `composites.py`, `__init__.py`, `pyproject.toml`
4. **Phase 4 — Test**: writes unit + integration tests, runs them, fixes all failures
5. **Phase 5 — Demo report**: generates `demo/report.html` with Plotly charts, bigraph-viz diagram, PBG document viewer
6. **Final**: `pip install -e .`, `pytest`, `git commit`, open report in browser

The output repo lives at `${PBG_WORKSPACE:-$HOME/code}/pbg-<tool>/` and is a fully pip-installable Python package that auto-registers with `allocate_core()` via `bigraph_schema.package.discover`.

**Auto-discovery contract** (required for any `pbg-*` package):
- `pyproject.toml` lists `bigraph-schema` and `process-bigraph` in `dependencies`
- Process/Step classes inherit from `process_bigraph.Process` or `process_bigraph.Step`
- `pbg_<tool>/__init__.py` re-exports all process classes via `__all__`

---

## Part 2: REST API Design — Programmatic PBG Wrapper Generation

### Goal

Enable users to submit a simulator's GitHub URL to the sms-api and receive back a fully wrapped, containerized, compose-ready `pbg-<tool>` simulator — all via the Atlantis CLI, without ever running Claude Code locally.

### The Full Imagined Workflow (Atlantis CLI perspective)

```
# Step 1: Request wrapper generation
atlantis compose wrapper create https://github.com/vivarium-collective/mem3dg --tool-name mem3dg

# Step 2: Poll until wrapper code is generated and stored
atlantis compose wrapper status <wrapper_id>

# Step 3: Poll until the Singularity container build is done
atlantis compose simulator build-status <simulator_id>

# Step 4: Register the new wrapper's processes
atlantis compose processes list   # verify it appears

# Step 5: Use in a compose simulation
atlantis compose run --document my_composite.json   # references the new processes by address
```

### How the pbg-expert Logic Runs Server-Side

The `pbg-expert` skill is Claude Code intelligence — it is not an importable Python module. Server-side execution requires invoking Claude as an **agentic subprocess** using the Anthropic Agent SDK (`claude_agent_sdk` / `anthropic` Python SDK with tool use).

The server:
1. Loads the `pbg-expert` SKILL.md content as a system prompt
2. Sends the tool GitHub URL as a user message to the Claude API with file-system tool grants
3. The agent creates all wrapper files inside a temporary working directory on the server
4. The server bundles the result and stores it

This is the only correct design — the pbg-expert skill IS Claude's intelligence; porting it to deterministic code would lose the model analysis step that reads the target simulator's source and designs compositionally correct port schemas.

### Architecture Overview

```
POST /compose/v1/wrappers
        |
        v
 [WrapperGenerationService]
   1. Write SKILL.md as system prompt
   2. Call Anthropic Agent SDK with target repo URL
   3. Agent generates pbg-<tool>/ files in tmp dir
   4. Bundle as tarball
   5. Upload tarball to FileService (GCS/S3/Qumulo)
   6. Insert ORMPbgWrapper DB record
   7. Return wrapper_id
        |
        v (background task, after generation completes)
 [ComposeSimulationService.build_wrapper_container]
   8. Pull wrapper tarball from storage to HPC
   9. Submit SLURM/Batch container build job (same pattern as /core/v1/simulator/upload)
  10. Update ORMPbgWrapper.simulator_id once build completes
        |
        v (user polls)
GET /compose/v1/wrappers/{wrapper_id}/status
GET /compose/v1/simulator/{simulator_id}/build/status  (existing endpoint, reused)
        |
        v (once built, auto-registers via allocate_core discovery)
GET /compose/v1/processes  (existing endpoint, returns new processes)
        |
        v (user composes)
POST /compose/v1/simulation/run  (existing endpoint, references new process by address)
```

---

### New Database Table: `ORMPbgWrapper`

Add to `sms_api/compose/tables_orm.py`:

```python
class WrapperStatus(enum.Enum):
    GENERATING = "generating"   # Claude agent is running
    STORING    = "storing"      # tarball upload in progress
    READY      = "ready"        # tarball stored; container build dispatched
    BUILDING   = "building"     # Singularity/Docker build running on HPC
    AVAILABLE  = "available"    # container built; processes registered
    FAILED     = "failed"

class ORMPbgWrapper(Base):
    __tablename__ = "pbg_wrappers"

    id              : Mapped[int]           = mapped_column(Integer, primary_key=True)
    tool_name       : Mapped[str]           = mapped_column(String, nullable=False)
    source_repo_url : Mapped[str]           = mapped_column(String, nullable=False)
    source_ref      : Mapped[str]           = mapped_column(String, default="main")
    storage_uri     : Mapped[str | None]    = mapped_column(String, nullable=True)   # GCS/S3 URI of tarball
    status          : Mapped[str]           = mapped_column(String, default=WrapperStatus.GENERATING.value)
    simulator_id    : Mapped[int | None]    = mapped_column(Integer, ForeignKey("compose_simulators.id"), nullable=True)
    error_message   : Mapped[str | None]    = mapped_column(Text, nullable=True)
    created_at      : Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
    updated_at      : Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### New Pydantic Models

Add to `sms_api/compose/models.py`:

```python
class WrapperStatus(StrEnum):
    GENERATING = "generating"
    STORING    = "storing"
    READY      = "ready"
    BUILDING   = "building"
    AVAILABLE  = "available"
    FAILED     = "failed"

class PbgWrapperCreateRequest(BaseModel):
    source_repo_url: str = Field(..., description="GitHub URL of the simulator to wrap, e.g. https://github.com/vivarium-collective/mem3dg")
    source_ref: str = Field(default="main", description="Git branch/tag/commit to target")
    tool_name: str | None = Field(default=None, description="Override the derived tool name (default: inferred from repo name)")
    extra_instructions: str | None = Field(default=None, description="Optional extra context for the wrapper agent")

class PbgWrapperRecord(BaseModel):
    wrapper_id: int
    tool_name: str
    source_repo_url: str
    source_ref: str
    status: WrapperStatus
    simulator_id: int | None = None
    storage_uri: str | None = None
    error_message: str | None = None
    created_at: datetime
```

### New Service: `WrapperGenerationService`

New file: `sms_api/compose/wrapper_service.py`

```python
"""
WrapperGenerationService: invokes the pbg-expert skill via the Anthropic Agent SDK
to generate a pbg-<tool> wrapper repo, bundle it, and push it to FileService storage.
"""
import asyncio
import tarfile
import tempfile
from pathlib import Path

import anthropic

from sms_api.common.storage.file_service import FileService
from sms_api.compose.database_service import ComposeDatabaseService


SKILL_MD_PATH = Path(__file__).parent.parent.parent.parent / "pbg-superpowers" / "skills" / "pbg-expert" / "SKILL.md"
# NOTE: at deploy time, bundle SKILL.md into the Docker image at a known path,
# e.g. /app/skills/pbg-expert/SKILL.md, and read from there.


class WrapperGenerationService:
    def __init__(self, db: ComposeDatabaseService, file_service: FileService):
        self._db = db
        self._file_service = file_service
        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    async def generate_wrapper(
        self,
        wrapper_id: int,
        source_repo_url: str,
        tool_name: str,
        source_ref: str = "main",
        extra_instructions: str | None = None,
    ) -> None:
        """
        Background task: runs the pbg-expert agent, bundles output, stores tarball,
        then triggers container build.
        """
        try:
            with tempfile.TemporaryDirectory() as workdir:
                workspace = Path(workdir)
                await self._run_pbg_expert_agent(
                    workspace=workspace,
                    source_repo_url=source_repo_url,
                    tool_name=tool_name,
                    source_ref=source_ref,
                    extra_instructions=extra_instructions,
                )
                tarball_path = workspace / f"pbg-{tool_name}.tar.gz"
                self._bundle_wrapper(workspace / f"pbg-{tool_name}", tarball_path)
                storage_uri = await self._store_tarball(wrapper_id, tool_name, tarball_path)
                await self._db.get_wrapper_db().update_wrapper_status(
                    wrapper_id, status="ready", storage_uri=storage_uri
                )
            # Trigger container build (same pipeline as /core/v1/simulator/upload)
            simulator_id = await self._dispatch_container_build(wrapper_id, tool_name, storage_uri)
            await self._db.get_wrapper_db().update_wrapper_simulator_id(wrapper_id, simulator_id)
        except Exception as exc:
            await self._db.get_wrapper_db().update_wrapper_status(
                wrapper_id, status="failed", error_message=str(exc)
            )
            raise

    async def _run_pbg_expert_agent(
        self, workspace: Path, source_repo_url: str, tool_name: str,
        source_ref: str, extra_instructions: str | None
    ) -> None:
        """
        Invokes Claude with the pbg-expert SKILL.md as system prompt.
        Uses the claude-agent-sdk / computer-use tool pattern with a
        filesystem sandbox rooted at `workspace`.
        """
        skill_md = SKILL_MD_PATH.read_text()
        user_message = (
            f"{source_repo_url}"
            + (f" (branch: {source_ref})" if source_ref != "main" else "")
            + (f"\n\nAdditional context: {extra_instructions}" if extra_instructions else "")
        )
        # Set PBG_WORKSPACE so the agent creates the repo inside our temp dir
        env_override = f"PBG_WORKSPACE={workspace}"

        # Use claude-agent-sdk for agentic execution with tool use.
        # The agent is allowed: Bash (sandboxed), Read, Write, Edit, Glob, Grep, WebFetch.
        # Implementation detail: wire up claude_agent_sdk.Agent or use anthropic
        # Messages API with tools. The exact SDK call depends on the deployed
        # claude_agent_sdk version; see sms_api/skills/ for patterns.
        #
        # Pseudocode (replace with real SDK call):
        #   agent = Agent(system=skill_md, tools=[bash_tool, read_tool, write_tool, ...])
        #   agent.run(user_message, env={"PBG_WORKSPACE": str(workspace)})
        #
        # For now this is a design placeholder — the actual implementation
        # uses anthropic.Anthropic().beta.messages.create() with tool_choice and
        # a sandboxed subprocess executor.
        raise NotImplementedError("Agent SDK invocation — see implementation notes above")

    def _bundle_wrapper(self, repo_dir: Path, tarball_path: Path) -> None:
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(repo_dir, arcname=repo_dir.name)

    async def _store_tarball(self, wrapper_id: int, tool_name: str, tarball_path: Path) -> str:
        """Upload to GCS/S3/Qumulo via FileService. Returns the storage URI."""
        remote_key = f"pbg-wrappers/{wrapper_id}/pbg-{tool_name}.tar.gz"
        await self._file_service.upload(local_path=tarball_path, remote_key=remote_key)
        return remote_key  # or full URI depending on FileService impl

    async def _dispatch_container_build(self, wrapper_id: int, tool_name: str, storage_uri: str) -> int:
        """
        Pull tarball to HPC, generate a Singularity .def for the pbg-<tool> package,
        submit the build job, and return the compose simulator_id.

        Reuses the same SLURM job submission path as ComposeSimulationService.build_container().
        The .def file installs the pbg-<tool> package from the tarball into a base
        process-bigraph image so allocate_core() discovers it automatically at container startup.
        """
        raise NotImplementedError("Container build dispatch — mirrors existing compose build pipeline")
```

### New REST Endpoints

Add to `sms_api/api/routers/compose.py` (new section: `# Wrapper generation endpoints`):

```python
# ---------------------------------------------------------------------------
# PBG Wrapper generation endpoints
# ---------------------------------------------------------------------------

@router.post(
    path="/wrappers",
    operation_id="compose-create-wrapper",
    response_model=PbgWrapperRecord,
    tags=["Compose Wrappers"],
    summary="Generate a pbg-<tool> wrapper for an arbitrary simulator repo",
)
async def create_wrapper(
    request: PbgWrapperCreateRequest,
    background_tasks: BackgroundTasks,
) -> PbgWrapperRecord:
    """
    Submit a simulator's GitHub URL. The server runs the pbg-expert agent
    to generate a complete process-bigraph wrapper package, stores the output,
    and dispatches a container build. Returns immediately with a wrapper_id.

    Poll GET /compose/v1/wrappers/{wrapper_id}/status for progress.
    Once status == 'available', the new processes appear in GET /compose/v1/processes
    and can be referenced in POST /compose/v1/simulation/run documents.
    """
    tool_name = request.tool_name or _derive_tool_name(request.source_repo_url)
    wrapper = await _require_db().get_wrapper_db().insert_wrapper(
        tool_name=tool_name,
        source_repo_url=request.source_repo_url,
        source_ref=request.source_ref,
    )
    background_tasks.add_task(
        _require_wrapper_service().generate_wrapper,
        wrapper_id=wrapper.wrapper_id,
        source_repo_url=request.source_repo_url,
        tool_name=tool_name,
        source_ref=request.source_ref,
        extra_instructions=request.extra_instructions,
    )
    return wrapper


@router.get(
    path="/wrappers/{wrapper_id}/status",
    operation_id="compose-get-wrapper-status",
    response_model=PbgWrapperRecord,
    tags=["Compose Wrappers"],
    summary="Poll the status of a pbg-wrapper generation job",
)
async def get_wrapper_status(wrapper_id: int) -> PbgWrapperRecord:
    wrapper = await _require_db().get_wrapper_db().get_wrapper(wrapper_id)
    if wrapper is None:
        raise HTTPException(404, f"Wrapper {wrapper_id} not found")
    return wrapper


@router.get(
    path="/wrappers",
    operation_id="compose-list-wrappers",
    response_model=list[PbgWrapperRecord],
    tags=["Compose Wrappers"],
    summary="List all generated pbg-* wrappers",
)
async def list_wrappers(
    status: WrapperStatus | None = None,
) -> list[PbgWrapperRecord]:
    return await _require_db().get_wrapper_db().list_wrappers(status=status)


def _derive_tool_name(repo_url: str) -> str:
    """Extract a clean lowercase-hyphenated tool name from a GitHub URL."""
    name = repo_url.rstrip("/").split("/")[-1]
    name = name.removesuffix(".git")
    # remove leading pbg- if already prefixed to avoid pbg-pbg-foo
    name = name.removeprefix("pbg-")
    return name.lower().replace("_", "-")
```

### Storage Strategy

Reuse the existing `FileService` abstraction (`sms_api/common/storage/`):

| Deployment | Backend | Wrapper tarball path pattern |
|---|---|---|
| CCAM / RKE | Qumulo S3 | `pbg-wrappers/{wrapper_id}/pbg-{tool_name}.tar.gz` |
| Stanford | AWS S3 (GovCloud) | `pbg-wrappers/{wrapper_id}/pbg-{tool_name}.tar.gz` |

No new storage abstraction needed — `FileService.upload()` / `FileService.download()` handle the backend selection. The `storage_uri` column in `ORMPbgWrapper` stores the backend-relative key.

### Container Build Strategy

A generated `pbg-<tool>` wrapper is pip-installable (`pyproject.toml` with `hatchling`). The Singularity container build:

1. Starts from the existing base `process-bigraph` container image (the same one used for COPASI/Tellurium compose runs)
2. Copies the tarball onto the HPC filesystem (via `FileService.download()` → SCP)
3. Runs `pip install /path/to/pbg-<tool>/` inside the container
4. The installed package becomes auto-discoverable by `allocate_core()` at container startup

Singularity `.def` snippet:

```singularity
Bootstrap: localimage
From: /hpc/images/process-bigraph-base.sif

%files
    /tmp/pbg-{{ tool_name }}.tar.gz /opt/pbg-{{ tool_name }}.tar.gz

%post
    cd /tmp && tar -xzf /opt/pbg-{{ tool_name }}.tar.gz
    pip install /tmp/pbg-{{ tool_name }}/
    rm -rf /tmp/pbg-{{ tool_name }}*
```

This `.def` is Jinja-rendered server-side and submitted via the existing `SlurmService.submit_job()` path.

### Atlantis CLI Commands

New command group `atlantis compose wrapper`:

```
# Generate a wrapper
uv run atlantis compose wrapper create <github-url> [--tool-name <name>] [--ref <branch>] [--poll]

# Check status
uv run atlantis compose wrapper status <wrapper-id>

# List all wrappers
uv run atlantis compose wrapper list [--status available]
```

Full E2E example (mirrors the existing EUTE workflow):

```bash
# 1. Generate wrapper (returns wrapper_id immediately; agent runs in background)
uv run atlantis compose wrapper create https://github.com/vivarium-collective/mem3dg --tool-name mem3dg --poll

# 2. Once available, confirm the new processes registered
uv run atlantis compose processes list

# 3. Submit a compose simulation referencing the new wrapper process by address
uv run atlantis compose run --document my_membrane_sim.json

# 4. Poll simulation
uv run atlantis compose status <sim_id>

# 5. Download results
uv run atlantis compose results <sim_id> --dest ./debug
```

---

## Implementation Phases

### Phase 1 — Database & Models (no agent yet)
- [ ] Add `ORMPbgWrapper` table to `sms_api/compose/tables_orm.py`
- [ ] Add `WrapperDatabaseService` to `sms_api/compose/database_service.py`
- [ ] Add `PbgWrapperCreateRequest`, `PbgWrapperRecord`, `WrapperStatus` to `sms_api/compose/models.py`
- [ ] Add REST endpoints to `sms_api/api/routers/compose.py` (returning 501 stubs initially)
- [ ] Add `_require_wrapper_service()` lazy init to compose router
- [ ] Write pytest tests for DB insert/query

### Phase 2 — Storage & Bundling
- [ ] Add `WrapperGenerationService._bundle_wrapper()` and `._store_tarball()` (no agent yet)
- [ ] Wire `FileService` into `WrapperGenerationService`
- [ ] Add config keys: `pbg_wrappers_storage_prefix`, `anthropic_api_key` (or read from existing env)
- [ ] Add `SKILL_MD_PATH` resolution + test that it loads

### Phase 3 — Agent Integration
- [ ] Implement `_run_pbg_expert_agent()` using the Anthropic Agent SDK
- [ ] Test with `pbg-mem3dg` as the reference target (todo #52)
- [ ] Sandbox: agent must write only into the temp directory; no network pushes
- [ ] Add timeout guard (120s per phase, matching the skill's own rule)

### Phase 4 — Container Build
- [ ] Implement `_dispatch_container_build()` using the existing compose build pipeline
- [ ] Add Jinja template for the wrapper `.def` file
- [ ] Status transitions: `ready` → `building` → `available` | `failed`

### Phase 5 — CLI Commands
- [ ] Add `atlantis compose wrapper create/status/list` to `app/cli.py`
- [ ] Add same to TUI (`app/tui.py`) and GUI (`app/gui.py`) for EUTE parity

### Phase 6 — Tests
- [ ] Unit tests: `_derive_tool_name()`, DB service, model serialization
- [ ] Integration test: mock agent call, verify DB record + storage upload
- [ ] E2E test: `pbg-mem3dg` round-trip (requires ANTHROPIC_API_KEY + HPC access)

---

## Key Design Decisions

### Why Claude API, not a deterministic Python port

The pbg-expert skill's core value is Claude's ability to read arbitrary simulator source code, infer the correct port semantics (`float` delta vs `overwrite[T]` vs `map[string,float]`), and write idiomatic PBG wrapper code. That analysis step cannot be deterministically scripted — it requires LLM reasoning. The server calls the Anthropic API with the SKILL.md as a system prompt.

### Responsibility boundary for wrapper correctness

The user bears full responsibility for port compatibility. The API will:
- Generate a syntactically valid, installable `pbg-<tool>` package
- Run `pytest` inside the agent and fail the job if tests don't pass
- Store and build the container

The API will NOT:
- Guarantee that the new wrapper's ports are compatible with any existing registered process
- Auto-wire or auto-compose with existing processes

Users must inspect the generated wrapper's `inputs()` / `outputs()` schemas (visible via `GET /compose/v1/process/{process_name}/inputs/{process_id}` after registration) and design their composition documents accordingly.

### Process registration after build

Once the container is built and stored, `allocate_core()` inside that container auto-discovers all `pbg-<tool>` classes via `bigraph_schema.package.discover`. No additional registration endpoint call is needed — the existing `GET /compose/v1/processes` endpoint reflects whatever `allocate_core()` discovers in the running container, which will include the new wrapper.

### todo.md reference

This design covers **todo #52** (`pbg-mem3dg`). When implementing Phase 3, use `pbg-mem3dg` (`https://github.com/vivarium-collective/pbg-mem3dg.git`) as the first real-world test case for the agent integration since it is already a complete canonical wrapper with a known-good demo report.
