# Bigraph Loom — SMS-API Integration Report

> **Date:** 2026-05-10
> **Target repo:** `../bigraph-loom` (process-bigraph visual GUI)
> **Target sms-api version:** 0.9.3
> **Status:** Integration plan — NOT yet implemented

## Table of Contents

1. [Overview](#overview)
2. [Architecture Deep-Dive](#architecture-deep-dive)
3. [Integration Architecture](#integration-architecture)
4. ["Run" Button Workflow](#run-button-workflow)
5. [Animated Canvas Approaches](#animated-canvas-approaches)
6. [SSE Endpoint Design](#sse-endpoint-design)
7. [Implementation Phases](#implementation-phases)
8. [Key Design Decisions](#key-design-decisions)
9. [File-by-File Change Plan](#file-by-file-change-plan)
10. [Technical Risks](#technical-risks)
11. [UX Vision](#ux-vision)
12. [GAPS THAT NEED FILLING](#gaps-that-need-filling)

---

## Overview

**Bigraph Loom** is a visual GUI for designing and running process-bigraph simulations. It provides a React Flow canvas where users compose process-bigraph models visually — dragging process nodes onto a canvas, connecting them via ports, editing configuration inline — and then executing simulations.

This report analyzes the bigraph-loom repo (`../bigraph-loom/`) and defines the integration path into the sms-api compose subsystem. The integration target is a FastAPI sub-application mounted at `/compose/gui` on the **Academic API (sms-api-rke)** only — no GovCloud/Batch implementation.

### Key Numbers

| Metric | Value |
|--------|-------|
| Backend Python files | 7 (api.py, convert.py, models.py, store.py, io.py, config.py, __init__.py) |
| REST endpoints | 20 (all session-scoped via `bgloom_sid`) |
| Frontend TSX/CSS files | 15 (App.tsx, ProcessNode.tsx, side panels, etc.) |
| Node types | 2 (ProcessNode, DocumentationNode) |
| Layout engine | dagre (via @dagrejs/dagre) |
| State management | React useState/useCallback (no Redux) |
| Session storage | In-memory dict with TTL (no persistence) |
| .pbg examples | 4 (test_v1.pbg, bifurk_malaria.pbg, nfkb_egfr.pbg, zika_first.pbg) |
| Tests | 3 test files |

---

## Architecture Deep-Dive

### Backend (`bigraph_loom/`)

#### `api.py` — 20 Endpoints

All endpoints operate within a session identified by the `bgloom_sid` cookie. Sessions are created lazily on the first request.

**Session lifecycle endpoints:**
- `POST /api/session/new` — Create a new session, return `bgloom_sid`
- `GET /api/session/verify` — Validate session still alive

**Canvas/document endpoints:**
- `GET /api/document` — Get current document (bigraph JSON) for session
- `PUT /api/document` — Save/update document
- `POST /api/document/load-example/{name}` — Load a built-in .pbg example
- `POST /api/document/load-path` — Load .pbg from server-side file path
- `POST /api/document/load-url` — Fetch .pbg from URL

**Conversion endpoints (bigraph ↔ ReactFlow):**
- `GET /api/flow` — Get ReactFlow graph (nodes + edges) from current document
- `POST /api/flow` — Save ReactFlow graph back (round-trips through conversion)

**Process node endpoints:**
- `GET /api/process/{process_type}` — Get process schema/ports for a given type
- `GET /api/processes` — List all registered process types (from `allocate_core()`)
- `POST /api/process/schema` — Inline schema override for a process instance

**Simulation endpoints:**
- `POST /api/simulation/run` — Run simulation (in-process, blocking)
- `GET /api/simulation/status` — Get simulation status
- `GET /api/simulation/results` — Get simulation results (full JSON)
- `POST /api/simulation/reset` — Reset simulation state

**Layout endpoints:**
- `POST /api/layout/auto` — Auto-layout using dagre
- `POST /api/layout/serialize` — Export layout positions

**Metadata endpoints:**
- `GET /api/info` — Server info, available process types
- `GET /api/document/export` — Export as .pbg file

#### `convert.py` — Bigraph ↔ ReactFlow Engine

This is the core conversion logic:

```
bigraph JSON ──convert()──▶ ReactFlow nodes + edges
ReactFlow graph ──rebuild_document()──▶ bigraph JSON
```

The conversion maps:
- `bigraph.processes` → ReactFlow `ProcessNode` (custom node type)
- `bigraph.states` → ReactFlow nodes with specific state styling
- `bigraph.hints` → ReactFlow edges with source/target port matching
- Ports → ReactFlow handles (source/target per connection direction)

Port matching is heuristic-based: it matches process ports to state ports by name and direction. The `_iter_ports()` helper walks process schemas.

#### `store.py` — In-Memory Session Store

```python
sessions: dict[str, SessionData] = {}
TTL = 3600  # 1 hour
last_access: dict[str, float] = {}
```

Each `SessionData` contains:
- `document: dict` — The current bigraph JSON
- `simulation: Simulation | None` — In-progress simulation instance
- `results: dict | None` — Completed simulation results
- `created_at: float`

Sessions are cleaned up lazily (checked on each access). No background expiry thread.

#### `models.py` — Pydantic Models

Key models:
- `SessionInfo` — session_id, document_name, process_types available
- `FlowGraph` — nodes (list of FlowNode), edges (list of FlowEdge)
- `FlowNode` — id, type, position, data (label, process_type, config, ports)
- `FlowEdge` — id, source, target, source_handle, target_handle
- `SimulationStatus` — status (idle/running/done/error), progress, message
- `SimulationResults` — results dict, timestamps array, status

#### `io.py` — File I/O

- `load_pbg(path)` — Load .pbg file from disk
- `save_pbg(path, document)` — Save .pbg to disk
- `load_example(name)` — Load from bundled examples directory
- `fetch_pbg(url)` — Fetch .pbg from HTTP URL

#### `config.py` — Configuration

- `EXAMPLES_DIR` — Path to bundled .pbg examples
- `DEFAULT_DOCUMENT` — Default empty bigraph template
- `HOST`, `PORT` — Server host/port config

#### `__init__.py` — App Factory

Creates FastAPI app, mounts CORS middleware, registers all routes from `api.py` under the `api` prefix. This is the key entrypoint for integration — we wrap this into an APIRouter mounted under `/compose/gui`.

### Frontend (`frontend/src/`)

#### `App.tsx` — Main Canvas Orchestration

Uses `@xyflow/react` (React Flow v12). Key state:
- `nodes`, `edges` — React Flow graph state
- `selectedNode` — Currently selected node for editing
- `bgloom_sid` — Session cookie for API calls
- `processTypes` — Available process types from server
- `simStatus`, `simResults` — Simulation state

Side panels:
1. **Processes panel** — Lists available process types, drag-to-add
2. **Properties panel** — Edit selected node's config (inline JSON editor from `@uiw/react-codemirror`)
3. **Simulation panel** — Run/reset/status/results viewer
4. **Document panel** — Document metadata, import/export
5. **Layout panel** — Auto-layout, zoom controls

#### `nodes/ProcessNode.tsx`

Custom React Flow node component. Features:
- Colored header bar (process-type based coloring)
- Port handles on left (inputs) and right (outputs)
- Config badge showing port count
- Connection validation (type-matching ports)

#### `edges/CustomEdge.tsx`

Custom edge component with:
- Smooth step bezier curves
- Animated dash array (during simulation)
- Hover highlight

#### Side Panels

- `ProcessesPanel.tsx` — Process type list with drag-to-canvas
- `PropertiesPanel.tsx` — Config JSON editor for selected node
- `SimulationPanel.tsx` — Run button, progress bar, results tree viewer
- `LayoutPanel.tsx` — Auto-layout, zoom, fit-view controls
- `DocumentPanel.tsx` — Name, description, import/export buttons

### Examples (`bigraph-loom/examples/`)

Four example .pbg files:
- `test_v1.pbg` — Simple 2-process test
- `bifurk_malaria.pbg` — Malaria bifurcation model (complex)
- `nfkb_egfr.pbg` — NF-kB/EGFR signaling pathway
- `zika_first.pbg` — Zika virus model

---

## Integration Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────┐
│                  FastAPI Server                        │
│  ┌──────────────────────────────────────────────┐     │
│  │  sms_api/api/routers/                        │     │
│  │  ├── core.py      (/core/v1/*)              │     │
│  │  ├── compose.py   (/compose/v1/*)           │     │
│  │  │                                        │     │
│  │  └── NEW: compose_gui.py (/compose/gui/*)  │     │
│  │       wraps bigraph_loom.api as sub-app     │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │  sms_api/dependencies.py                    │     │
│  │  ├── allocate_core() ← shared singleton     │     │
│  │  └── ComposeSessionBridge (new)             │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │  sms_api/compose/                            │     │
│  │  ├── NEW: gui_session.py                    │     │
│  │  ├── NEW: gui_bridge.py                     │     │
│  │  ├── tables_orm.py   (+ GuiSessionORM)      │     │
│  │  └── database_service.py  (+ session ops)   │     │
│  └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### Sub-App Mounting

The bigraph-loom sub-app is NOT the standalone FastAPI app from `bigraph_loom/__init__.py`. Instead, we create a wrapper module `sms_api/compose/gui_bridge.py` that:

1. Creates a new `FastAPI` or `APIRouter` instance
2. Imports and registers all 20 endpoints from `bigraph_loom.api` with modified prefixes
3. Replaces the in-memory store with a DB-backed `SessionStore` that uses `GuiSessionORM`
4. Replaces the `allocate_core()` call with the shared singleton from `dependencies.py`
5. Wraps the simulation run endpoint to dispatch through `ComposeSimulationService` (SLURM) instead of running in-process

Route mapping:
| bigraph-loom route | Integrated route | Changes |
|---|---|---|
| `POST /api/session/new` | `POST /compose/gui/session/new` | +DB persistence |
| `GET /api/document` | `GET /compose/gui/document` | +DB load/save |
| `PUT /api/document` | `PUT /compose/gui/document` | +DB persistence |
| `POST /api/flow` | `POST /compose/gui/flow` | +DB round-trip |
| `POST /api/simulation/run` | `POST /compose/gui/simulation/run` | **SLURM dispatch** |
| `GET /api/simulation/status` | `GET /compose/gui/simulation/status` | **SSE streaming** |
| etc. | etc. | |

### Shared `allocate_core()` Instance

Currently, `sms_api/dependencies.py` has a `get_compose_core()` (or equivalent) that creates an `allocate_core()` instance. The bigraph-loom sub-app uses this same shared instance so that process types registered by SMS-API are available in the GUI canvas.

### ComposeSessionBridge

A new class that bridges the bigraph-loom session concept with the SMS-API compose workflow:

```python
class ComposeSessionBridge:
    """Bridges bigraph-loom sessions with compose simulation workflow."""

    async def create_session(self, user_id: str) -> str:
        """Create a new GUI session linked to a compose workflow."""

    async def session_to_simulation(self, session_id: str) -> int:
        """Convert a GUI session document into a compose simulation job.
        Returns a compose simulation ID that can be tracked via existing
        /compose/v1 endpoints."""

    async def get_session_status(self, session_id: str) -> dict:
        """Get composite status (GUI session + underlying simulation)."""

    async def cleanup_expired(self) -> int:
        """Remove sessions older than TTL from DB."""
```

---

## "Run" Button Workflow

When a user clicks "Run" in the bigraph-loom GUI canvas, here is the end-to-end sequence:

### Step-by-Step Sequence

```
User clicks [Run] in SimulationPanel
        │
        ▼
┌──────────────────────────────┐
│ 1. POST /compose/gui/        │
│    simulation/run            │
│    Request: {session_id}     │
│    Response: {job_id, status}│
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 2. gui_bridge.py collects:   │
│    - Current bigraph doc     │
│    - From session store      │
│    - Process configurations  │
│    - State initial values    │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 3. Composes job config:      │
│    - Writes .pbg to HPC dir  │
│    - Generates sbatch script │
│    - Jobs: [parca? sim]      │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 4. SUBMITS via SlurmService  │
│    - sbatch --> job_id       │
│    - Stores in GuiSessionORM │
│    - Returns {job_id}        │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 5. Frontend opens SSE conn:  │
│    GET /compose/gui/         │
│    simulation/{job_id}/      │
│    stream                    │
│                              │
│    Server streams events:    │
│    event: status             │
│    data: {"state":"RUNNING"} │
│    ---                       │
│    event: progress           │
│    data: {"pct":42}          │
│    ---                       │
│    event: snapshots          │
│    data: {path, value, ts}   │
│    ---                       │
│    event: complete           │
│    data: {result_summary}    │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 6. On complete, canvas:      │
│    - Shows checkmark on Run  │
│    - Enables "View Results"  │
│    - Updates edge animations │
│    - Process nodes show vals │
└──────────────────────────────┘
```

### Canvas Animation During Simulation

While the simulation runs (SSE streaming deltas):

1. **Edge glow pulses** — data flows along connected edges (green pulse for active connections)
2. **Process nodes show live values** — selected output ports display current values as badges
3. **State nodes update color** — color intensity maps to value magnitude
4. **Progress bar** — simulation panel shows elapsed time, estimated remaining
5. **Live log** — tail of simulation log in a collapsible panel

---

## Animated Canvas Approaches

Six creative approaches for making the canvas come alive during/after simulation:

### Approach 1: Pulse Glow Edges

**Mechanism:** CSS keyframe animation on SVG stroke-dashoffset. During simulation, each edge gets a CSS class `edge-active` that animates a gradient pulse from source to target.

```css
@keyframes edge-pulse {
  0% { stroke-dashoffset: 100; opacity: 0.3; }
  50% { opacity: 1.0; }
  100% { stroke-dashoffset: 0; opacity: 0.3; }
}
.edge-active {
  stroke: var(--color-accent);
  stroke-dasharray: 10 5;
  animation: edge-pulse 2s linear infinite;
}
```

**Data needed:** SSE event `{"type": "edge_activity", "edge_id": "e1", "active": true}`

### Approach 2: Dashed Edge Flow

**Mechanism:** Animated dash offset simulating data "flowing" through edges. Direction indicates data direction. Speed varies by data rate.

**Data needed:** SSE event `{"type": "edge_flow", "edge_id": "e1", "rate": 0.8}`

### Approach 3: Heat-Map Processes

**Mechanism:** Process node background color shifts through blue→green→yellow→red based on computational intensity (CPU time, iterations, etc.). Every process node becomes a "temperature gauge."

**Data needed:** SSE event `{"type": "process_heat", "node_id": "p1", "value": 0.65}`

### Approach 4: Time-Scrubber Playback

**Mechanism:** After simulation completes, a timeline scrubber at the bottom of the canvas allows replaying the simulation. The canvas state animates as the scrubber moves through time points. Snapshot interpolation when between discrete samples.

**Data needed:** Pre-computed `snapshots[]` array in simulation results, each with `{time, node_states: {node_id: value}}`

### Approach 5: Graph Evolution

**Mechanism:** Processes and states that were dynamically created/destroyed during simulation appear/disappear on the canvas with CSS transitions. New nodes fly in, removed nodes shrink and fade.

**Data needed:** SSE event `{"type": "node_added", "node": {...}}` or `{"type": "node_removed", "node_id": "..."}`
Note: This requires dynamic topology changes, which process-bigraph may not support natively.

### Approach 6: Mini Live Dashboard

**Mechanism:** A floating HUD overlay (top-right of canvas) showing:
- Mini sparkline chart of a selected variable
- Current simulation time
- Edges/second throughput
- Active process count
- Memory/resource usage

**Data needed:** SSE events with `type: "dashboard_update"` containing compact numeric payload.

---

## SSE Endpoint Design

### Single Streaming Endpoint

```
GET /compose/gui/simulation/{job_id}/stream
Headers:
  Accept: text/event-stream
Query params:
  session_id (optional) — for canvas animation context
  snapshot_interval (optional, default: 10) — timesteps between snapshots
```

### Event Types

```javascript
// Status transitions
event: status
data: {"state": "PENDING|RUNNING|COMPLETE|ERROR", "message": "..."}

// Progress (0–100)
event: progress
data: {"pct": 42, "elapsed_sec": 12.5, "remaining_sec": 18.3}

// Canvas delta — lightweight path/value pair
event: delta
data: {
  "path": "/processes/P1/emitter/current_value",
  "value": 0.847,
  "timestamp": 1.234,
  "type": "float"
}

// Edge activity indicator
event: edge_activity
data: {
  "edge_id": "P1_out→S1_in",
  "active": true,
  "intensity": 0.7
}

// Snapshot — full state at a point (less frequent)
event: snapshot
data: {
  "time": 5.0,
  "state": { ... partial or full state ... }
}

// Simulation complete
event: complete
data: {
  "job_id": "12345",
  "total_time": 10.0,
  "num_snapshots": 100,
  "result_summary": {
    "num_processes": 5,
    "num_states": 12,
    "final_values": { ... key values ... }
  }
}

// Error
event: error
data: {
  "code": "SIMULATION_FAILED",
  "message": "...",
  "details": {}
}

// Heartbeat (every 15s to keep connection alive)
event: heartbeat
data: {}
```

### Lightweight Delta Design

Instead of sending full state snapshots on every event (which would be large and slow), the SSE stream sends minimal `{path, value}` pairs. The frontend applies these as patches to a local state tree:

```typescript
// Frontend state tree
const stateTree = useRef<Record<string, any>>({});

// On delta event:
function applyDelta(path: string, value: any) {
  set(rootState, path, value);  // lodash set
  updateNodeDisplay(path, value);
}
```

### Snapshot Storage

Snapshots are stored at a configurable interval (default every 10–100 timesteps) to avoid DB bloat. The simulation service writes snapshots to a file or DB during execution:

```python
class SimulationSnapshot(Base):
    __tablename__ = "simulation_snapshots"
    id: int
    job_id: str
    timestep: int
    time: float
    snapshot_json: dict  # Compressed JSON
    created_at: datetime
```

---

## Implementation Phases

### Phase A: Embedding (Week 1)

**Goal:** Get bigraph-loom rendering as a sub-app under SMS-API.

- [ ] A1. Create `sms_api/compose/gui_bridge.py` wrapper module
- [ ] A2. Create `sms_api/compose/gui_session.py` DB-backed session store
- [ ] A3. Add `GuiSessionORM` table to `tables_orm.py`
- [ ] A4. Register bigraph-loom sub-app in `main.py` at `/compose/gui`
- [ ] A5. Wire shared `allocate_core()` to sub-app
- [ ] A6. Add `bigraph-loom` to project dependencies
- [ ] A7. Add Alembic migration for new tables
- [ ] A8. Test: GUI loads at `/compose/gui`, process types visible

**Estimated effort:** 3–4 days

### Phase B: Session Persistence (Week 1–2)

**Goal:** Replace in-memory store with DB-backed sessions.

- [ ] B1. Implement `GuiSessionDB` class with CRUD operations
- [ ] B2. Add session cleanup background task (expired sessions)
- [ ] B3. Implement `DocumentDB` for saving/loading bigraph JSON
- [ ] B4. Add `bgloom_sid` → compose session ID mapping
- [ ] B5. Write tests for session CRUD + expiry
- [ ] B6. Test: Canvas state survives page refresh

**Estimated effort:** 2–3 days

### Phase C: Simulation Dispatch (Week 2–3)

**Goal:** Replace in-process simulation with SLURM dispatch.

- [ ] C1. Implement `ComposeSessionBridge.session_to_simulation()`
- [ ] C2. Write .pbg to HPC filesystem (HPCFilePath patterns)
- [ ] C3. Generate sbatch script for process-bigraph simulation
- [ ] C4. Submit via SlurmService (ssh first arg pattern)
- [ ] C5. Implement job → session status mapping
- [ ] C6. Write tests for sbatch generation + submission
- [ ] C7. Test: Click Run in GUI → job appears in squeue

**Estimated effort:** 3–4 days

### Phase D: SSE Streaming (Week 3)

**Goal:** Stream simulation progress to GUI canvas.

- [ ] D1. Implement `GET /compose/gui/simulation/{job_id}/stream` endpoint
- [ ] D2. Implement job polling → SSE event loop
- [ ] D3. Design event payload format (status, progress, deltas, snapshots)
- [ ] D4. HPC: instrument simulation runner to write deltas to a file/pipe
- [ ] D5. SSE heartbeat every 15s
- [ ] D6. Frontend: EventSource connection + delta application
- [ ] D7. Handle SSE reconnect (last-event-id)
- [ ] D8. Write tests for SSE endpoint + event parsing
- [ ] D9. Test: Click Run → SSE stream visible in browser DevTools

**Estimated effort:** 4–5 days

### Phase E: Canvas Animations (Week 3–4)

**Goal:** Animate the React Flow canvas during and after simulation.

- [ ] E1. Implement Pulse Glow Edges (CSS keyframe)
- [ ] E2. Implement Dashed Edge Flow (animated dashoffset)
- [ ] E3. Implement Heat-Map Process Nodes (color interpolation)
- [ ] E4. Implement Time-Scrubber Playback (post-sim)
- [ ] E5. Implement Mini Live Dashboard (floating HUD)
- [ ] E6. Ensure animations are toggleable (performance option)
- [ ] E7. Test: Canvas animates during simulation run

**Estimated effort:** 3–4 days

### Phase F: CLI + TUI Integration (Week 4)

**Goal:** Expose GUI workflow via CLI and TUI clients.

- [ ] F1. Add CLI commands for GUI session management
- [ ] F2. Add `atlantis compose gui open` — launch browser to canvas
- [ ] F3. Add `atlantis compose gui status` — check session status
- [ ] F4. Add TUI screen for recent GUI sessions
- [ ] F5. Test: CLI commands work end-to-end

**Estimated effort:** 2 days

### Phase G: Polish + Docs (Week 4–5)

**Goal:** Production readiness.

- [ ] G1. Add comprehensive error handling in bridge layer
- [ ] G2. Performance testing with large models
- [ ] G3. Snapshot storage tuning (interval, compression)
- [ ] G4. Session cleanup + resource management
- [ ] G5. API documentation (OpenAPI + user docs)
- [ ] G6. CI: integration tests for GUI endpoints
- [ ] G7. `make spec` + `make api_client` + `make check` + `uv run pytest`

**Estimated effort:** 2–3 days

### Total Estimated Effort: 20–25 days

---

## Key Design Decisions

### D1: Sub-App vs. Separate Service

**Decision:** Mount as FastAPI sub-app under `/compose/gui`

**Rationale:** Single port, shared auth middleware, shared `allocate_core()` instance, simpler deployment (one pod instead of two). No need for service-to-service auth or internal DNS.

**Trade-off:** Tighter coupling. If bigraph-loom's dependencies conflict with SMS-API's, isolation is harder.

### D2: DB-Backed Sessions vs. In-Memory

**Decision:** Hybrid — in-memory cache with DB persistence layer

**Rationale:** SMS-API already has SQLAlchemy + asyncpg. DB persistence allows canvas state to survive pod restarts (important for long-running simulations). In-memory cache provides fast access for active sessions. Background task flushes to DB every 30s and cleans expired sessions.

### D3: SSE vs. WebSocket

**Decision:** SSE (Server-Sent Events)

**Rationale:** SSE works through ALBs without upgrade headers, simpler to implement, unidirectional (server→client) matches our use case perfectly. WebSocket adds complexity (connection management, reconnection logic, ALB timeout tuning) for no benefit here.

**Trade-off:** SSE is unidirectional only. If we ever need client→server streaming (e.g., sending canvas edits during sim), we'd need WebSocket. This seems unlikely for v1.

### D4: Delta Events vs. Full State

**Decision:** Lightweight `{path, value}` deltas with occasional full snapshots

**Rationale:** Full state snapshots every timestep would be huge (>1MB per snapshot for complex models). Deltas are typically <100 bytes. Client patches a local state tree. Full snapshots are saved at configurable intervals (every 10–100 timesteps) for post-hoc analysis.

### D5: Frontend Bundling

**Decision:** Serve pre-built bigraph-loom frontend from FastAPI static files

**Rationale:** Simplest deployment. The React app is built once (`npm run build`), the output goes into `sms_api/api/static/compose-gui/`, and FastAPI serves it at `/compose/gui/static/`. No separate frontend server, no CORS issues.

**Trade-off:** Frontend changes require a rebuild. For rapid iteration, we might want a dev proxy. Add Vite proxy config for `localhost:8888` during development.

### D6: Snapshot Sampling Strategy

**Decision:** Configurable interval, default every 10 timesteps

**Rationale:** Simulation timesteps can be as fast as 1ms. Storing every timestep would produce terabytes of data for long simulations. A default of every 10 timesteps gives a smooth playback experience while keeping storage manageable. Users can override via the API.

---

## File-by-File Change Plan

### New Files (9)

| # | File | Purpose |
|---|------|---------|
| NF1 | `sms_api/compose/gui_session.py` | DB-backed session store with CRUD, expiry, cache |
| NF2 | `sms_api/compose/gui_bridge.py` | Wrapper module: mounts bigraph-loom routes, replaces `allocate_core()`, adds SLURM dispatch |
| NF3 | `sms_api/compose/gui_dispatch.py` | Simulation dispatch logic: .pbg → HPC → SLURM |
| NF4 | `sms_api/compose/gui_sse.py` | SSE streaming endpoint implementation |
| NF5 | `sms_api/compose/models_gui.py` | Pydantic models for GUI-specific request/response |
| NF6 | `sms_api/api/static/compose-gui/index.html` | Pre-built bigraph-loom frontend (from `npm run build`) |
| NF7 | `sms_api/api/routers/compose_gui.py` | FastAPI router for `/compose/gui/*` (thin layer) |
| NF8 | `sms_api/api/routers/compose_gui_sse.py` | SSE streaming route (separated for clarity) |
| NF9 | `tests/compose/test_gui_session.py` | Tests for session CRUD, expiry, cache |

### Modified Files (16)

| # | File | Changes |
|---|------|---------|
| MF1 | `sms_api/compose/tables_orm.py` | Add `GuiSessionORM`, `GuiDocumentORM`, `SimulationSnapshotORM` tables |
| MF2 | `sms_api/compose/database_service.py` | Add GUI session query methods |
| MF3 | `sms_api/dependencies.py` | Add `ComposeSessionBridge` singleton, ensure shared `allocate_core()` |
| MF4 | `sms_api/api/main.py` | Register `compose_gui` sub-app at `/compose/gui` (conditional on SLURM backend, like compose) |
| MF5 | `sms_api/compose/handlers.py` | Add handler for GUI-triggered simulations |
| MF6 | `sms_api/compose/simulation_service.py` | Add GUI-specific simulation method (writes .pbg, calls SlurmService) |
| MF7 | `sms_api/compose/hpc_utils.py` | Add .pbg file handling to HPC file utilities |
| MF8 | `app/cli.py` | Add `compose gui` command group (open, status, list) |
| MF9 | `app/cli_theme.py` | Add GUI-related themed output (canvas URL display, session status cards) |
| MF10 | `app/tui.py` | Add GUI sessions screen |
| MF11 | `sms_api/config.py` | Add GUI-related settings (session TTL, snapshot interval, frontend path) |
| MF12 | `pyproject.toml` | Add `bigraph-loom` dependency (or vendor it) |
| MF13 | `tests/compose/conftest.py` | Add GUI fixtures (mock session, mock frontend) |
| MF14 | `tests/compose/test_gui_bridge.py` | Tests for bridge layer |
| MF15 | `tests/compose/test_gui_sse.py` | Tests for SSE streaming |
| MF16 | `alembic/versions/` | Migration for new GUI tables |

### Bigraph-loom Changes (6 files in `../bigraph-loom/`)

| # | File | Changes |
|---|------|---------|
| BL1 | `bigraph_loom/api.py` | Add `get_dependencies()` hook for injecting `allocate_core()` and session store |
| BL2 | `bigraph_loom/store.py` | Add `AbstractSessionStore` interface for DB-backed replacement |
| BL3 | `bigraph_loom/convert.py` | Minor: add `export_delta()` for partial state serialization |
| BL4 | `frontend/src/App.tsx` | Add EventSource SSE connection, delta application, canvas animation triggers |
| BL5 | `frontend/src/SimulationPanel.tsx` | Add SSE status display, animated progress, reconnect logic |
| BL6 | `frontend/src/styles/canvas-animations.css` | New: pulse glow, edge flow, heat-map CSS keyframes |

---

## Technical Risks

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| R1 | **package conflict** — `bigraph-loom` deps (process-bigraph >=1.0.0, bigraph-schema >=1.0.0) may conflict with SMS-API's existing process-bigraph pin | High | Medium | Pin compatible versions in pyproject.toml. Run `uv lock` after adding. |
| R2 | **SSE reliability** — ALB timeouts may close SSE connections (ALB idle timeout default 60s) | High | High | SSE heartbeat every 15s keeps connection alive. Document the heartbeat contract. |
| R3 | **Frontend build pipeline** — Embedding pre-built frontend adds build step to deploy workflow | Medium | High | Add `make compose-gui-build` command. Include in CI/CD. Template the HTML to inject API base URL. |
| R4 | **Session data loss** — Pod restart during simulation destroys in-memory session state | High | Medium | DB-backed sessions with 30s flush interval. Pod restart → session rehydrated from DB. |
| R5 | **Snapshot storage bloat** — Large simulations produce millions of snapshots | Medium | Medium | Configurable sampling interval. Automatic cleanup of old snapshots (retention policy). Optional snapshot compression. |
| R6 | **Canvas performance** — Complex bigraph with 100+ nodes causes React Flow performance issues | Medium | Low | React Flow virtualization handles large graphs well. Add node grouping/folding for very large models. |
| R7 | **SSH polling inside SSE** — Polling SLURM every N seconds inside an SSE handler blocks the event loop | High | High | Use `asyncio.create_task` with `asyncio.sleep` in a background coroutine. Push events through an `asyncio.Queue`. |
| R8 | **Cross-origin auth** — If GUI frontend is served from a different origin, CORS/auth must be configured | Medium | Medium | Same-origin by design (static files from FastAPI). If proxied, ensure CORS middleware allows it. |
| R9 | **bigraph-loom maintenance** — Upstream bigraph-loom changes may break integration | Medium | Low | Pin bigraph-loom version. Write integration tests that verify endpoint contracts. |
| R10 | **Alembic migration conflicts** — New tables may conflict with existing compose DB schema | Medium | Low | Use distinct table name prefixes (`gui_sessions`, `gui_documents`). Run `alembic check` before deploying. |

---

## UX Vision

### Mockup 1: Main Canvas View

```
┌─────────────────────────────────────────────────────────────────────┐
│ [logo] Compose GUI [session: abc123]        [user] [docs] [logout] │
├─────────┬───────────────────────────────────────────────────────────┤
│         │                                                           │
│ Panel   │   ┌───[Process: Transcription]───┐  ┌───[State: mRNA]──┐│
│  of     │   │ ● (in)                        │  │ ● val: 0.42     ││
│ Proc-   │   │                         ● (out)│  │                  ││
│ esses   │   │ config: {rate: 0.1}           │  └──────────────────┘│
│         │   └───────────────────────────────┘         ▲           │
│ ────────│         │ (edge with pulse glow)            │           │
│ [DNA    │         └────────────────────────────────────┘           │
│  Tran..]│                                                           │
│ [RNA    │   ┌───[Process: Translation]───┐  ┌───[State: Prot]───┐│
│  Poly..]│   │ ● (in)                        │ ● val: 0.12      ││
│ [Degra- │   │                         ● (out)│                   ││
│  dation]│   │ config: {rate: 0.05}          │                   ││
│         │   └───────────────────────────────┘                   ││
│         │                                                           │
│         │                               [Auto-layout] [Zoom: 80%] │
├─────────┴───────────────────────────────────────────────────────────┤
│ Simulation: [Run] [Reset]  ════════░░░░░░ 42% │ 00:12 / 00:30     │
│ [▸ Live Log: timestep 1247 / 3000]                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Mockup 2: Post-Simulation with Scrubber

```
┌─────────────────────────────────────────────────────────────────────┐
│ [logo] Compose GUI [session: abc123]        [user] [docs] [logout] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   (Canvas with time-dependent node colors, edge flow animations)    │
│                                                                     │
│   ┌───[Process: Transcription]───┐  ┌───[State: mRNA]──┐          │
│   │ ● (in)                        │  │ ● val: 0.87 ←───│          │
│   │                         ● (out)│  │   heat: ████░░  │          │
│   └───────────────────────────────┘  └──────────────────┘          │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ ════════════════════●═══════════════════════════════════════▶ t    │
│ t=0.0             t=5.2s          t=10.0s                  t=30.0s │
│                                                                     │
│ [▶ Play] [⏸ Pause] [⏹ Stop]  Speed: [1x ▼]                    │
│                                                                     │
│ Node: mRNA  ┌─────────────────────────────────────────────────┐    │
│ Value over  │ ╱╲    ╱╲    ╱╲                                  │    │
│ time:       │╱  ╲╱  ╲╱  ╲╱  ╲╱╲                              │    │
│             │               ╲╱  ╲╱╲                            │    │
│             │                     ╲╱╲                          │    │
│             └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Mockup 3: Mini Live Dashboard (Floating HUD)

```
┌──────────────────────────────────────────────────────┐
│ ┌────────────────────────────────────────────────────┐│
│ │             ╱╲         LIVE DASHBOARD       [×]   ││
│ │    mRNA    ╱  ╲       ───────────────────         ││
│ │  0.87  ───╱    ╲      Sim time: 12.4s             ││
│ │                    ╲   Throughput: 847 t/s         ││
│ │   Protein         ╲   Processes: 5 active          ││
│ │   0.42 ─────────────  Memory: 234 MB               ││
│ └────────────────────────────────────────────────────┘│
│                                                        │
│                    (canvas)                            │
└────────────────────────────────────────────────────────┘
```

---

## GAPS THAT NEED FILLING

This checklist covers gaps between the current state of `bigraph-loom` + `sms-api` and the integrated vision described above. Items marked **[CRITICAL]** are blockers; items marked **[NICE]** are desirable but deferrable.

### A. Core Integration Gaps — BLOCKERS

- [ ] A1. **[CRITICAL]** No `AbstractSessionStore` interface in bigraph-loom `store.py` — currently hardcoded to in-memory dict. Need interface to swap in DB-backed store.
- [ ] A2. **[CRITICAL]** No `get_dependencies()` hook in bigraph-loom `api.py` — `allocate_core()` is created inside each endpoint. Need to inject shared instance from SMS-API.
- [ ] A3. **[CRITICAL]** No sub-app mounting support — bigraph-loom creates its own `FastAPI()` app in `__init__.py`. Need `APIRouter` export or app factory that accepts an existing router.
- [ ] A4. **[CRITICAL]** Simulation `POST /api/simulation/run` blocks the event loop (in-process synchronous simulation). Need async wrapper + SLURM dispatch.
- [ ] A5. **[CRITICAL]** No existing `GuiSessionORM` or `GuiDocumentORM` tables in `sms_api/compose/tables_orm.py`.

### B. Session Management Gaps

- [ ] B1. No DB-backed session CRUD (create, read, update, delete).
- [ ] B2. No session expiry/cleanup background task.
- [ ] B3. No session → user ID mapping (all sessions are anonymous currently).
- [ ] B4. No `bgloom_sid` → compose simulation ID cross-reference.
- [ ] B5. No session restore after pod restart.
- [ ] B6. No session listing API (admin/users list active sessions).

### C. SSE Streaming Gaps

- [ ] C1. **[CRITICAL]** No SSE endpoint exists — `GET /api/simulation/status` is poll-based.
- [ ] C2. No event type definitions shared between backend and frontend.
- [ ] C3. No heartbeat mechanism to keep ALB connections alive.
- [ ] C4. No reconnection support (`Last-Event-ID` handling).
- [ ] C5. No `asyncio.Queue`-based push mechanism for simulation events.
- [ ] C6. No frontend `EventSource` implementation.
- [ ] C7. No delta payload format specification.
- [ ] C8. No snapshot sampling interval configuration.

### D. Simulation Dispatch Gaps

- [ ] D1. **[CRITICAL]** No .pbg → HPC filesystem write logic.
- [ ] D2. **[CRITICAL]** No sbatch script generation for process-bigraph simulations.
- [ ] D3. **[CRITICAL]** No SlurmService integration for GUI-triggered jobs.
- [ ] D4. No job → session status mapping (how does a SLURM job ID map back to a GUI session?).
- [ ] D5. No simulation output → canvas state conversion (SLURM output → ReactFlow updates).
- [ ] D6. No error handling for failed SLURM jobs in GUI context.
- [ ] D7. No HPC .pbg file path conventions (`HPCFilePath` patterns).

### E. Frontend Gaps

- [ ] E1. No SSE connection in `App.tsx` — currently uses fetch/poll.
- [ ] E2. No canvas animation during simulation (edges, nodes, HUD).
- [ ] E3. No `canvas-animations.css` with pulse glow, edge flow, heat-map keyframes.
- [ ] E4. No time-scrubber component for post-sim playback.
- [ ] E5. No mini live dashboard (floating HUD).
- [ ] E6. No build output in `sms_api/api/static/compose-gui/`.
- [ ] E7. No `make compose-gui-build` command.
- [ ] E8. No dark mode support in bigraph-loom frontend.
- [ ] E9. No loading/saving of canvas viewport (zoom, pan position) to session.
- [ ] E10. No undo/redo for canvas edits.
- [ ] E11. No keyboard shortcuts documentation.
- [ ] E12. No drag-and-drop from processes panel to canvas.
- [ ] E13. **[NICE]** No node grouping/folding for large models.

### F. CLI Integration Gaps

- [ ] F1. No `atlantis compose gui` command group.
- [ ] F2. No `atlantis compose gui open` — launch browser with session.
- [ ] F3. No `atlantis compose gui status` — check session/simulation status.
- [ ] F4. No `atlantis compose gui list` — list active sessions.
- [ ] F5. No `atlantis compose gui close` — close/clean up session.
- [ ] F6. No CLI-themed output for GUI-related commands (`cli_theme.py`).

### G. TUI Integration Gaps

- [ ] G1. No GUI sessions screen in Textual TUI.
- [ ] G2. No real-time session status display in TUI.
- [ ] G3. No link to GUI URL from TUI.

### H. Testing Gaps

- [ ] H1. No tests for `gui_session.py` (session CRUD, expiry, cache).
- [ ] H2. No tests for `gui_bridge.py` (route wrapping, dependency injection).
- [ ] H3. No tests for `gui_dispatch.py` (.pbg → HPC → SLURM).
- [ ] H4. No tests for `gui_sse.py` (SSE event generation, heartbeat, reconnect).
- [ ] H5. No integration tests for GUI-triggered SLURM jobs.
- [ ] H6. No frontend tests for SSE connection + delta application.
- [ ] H7. No fixtures for GUI sessions (`tests/compose/conftest.py`).
- [ ] H8. No snapshot serialization/deserialization tests.
- [ ] H9. No performance tests for large graph rendering.
- [ ] H10. No test for ALB timeout scenario (SSE heartbeat).

### I. Documentation Gaps

- [ ] I1. No API reference for `/compose/gui/*` endpoints in OpenAPI spec.
- [ ] I2. No user guide for the GUI canvas.
- [ ] I3. No developer guide for frontend customization.
- [ ] I4. No integration architecture diagram.
- [ ] I5. No animation approach documentation.
- [ ] I6. No SSE event type reference.
- [ ] I7. No session lifecycle documentation.
- [ ] I8. No snapshot storage documentation.
- [ ] I9. **THIS DOCUMENT** is the initial version — needs to be kept in sync.

### J. Security Gaps

- [ ] J1. No authentication/authorization for GUI endpoints.
- [ ] J2. No rate limiting on `/compose/gui/simulation/run`.
- [ ] J3. No input validation on .pbg document upload (could contain malicious config).
- [ ] J4. No session hijacking protection (`bgloom_sid` is a simple UUID).
- [ ] J5. No CORS restrictions on GUI endpoints.
- [ ] J6. **[NICE]** No audit logging for GUI actions (session create, run, document save).
- [ ] J7. No validation that uploaded .pbg files don't access unauthorized paths.

### K. Performance Gaps

- [ ] K1. No snapshot compression (JSON blobs can be large).
- [ ] K2. No pagination for snapshot retrieval (could be millions of snapshots).
- [ ] K3. No session count limits (a user could create unlimited sessions).
- [ ] K4. No cleanup of orphaned SLURM jobs when GUI session expires.
- [ ] K5. No frontend performance optimization for large graphs (>200 nodes).
- [ ] K6. **[NICE]** No WebWorker for delta application (UI thread could block).
- [ ] K7. No SSE backpressure handling (client too slow for deltas).

### L. Deployment Gaps

- [ ] L1. No frontend build step in CI/CD pipeline.
- [ ] L2. No frontend build output in Docker image.
- [ ] L3. No sub-app conditional registration (only on SLURM backend) — must mirror `compose.py` pattern.
- [ ] L4. No Alembic migration for new GUI tables.
- [ ] L5. No environment variables for GUI configuration (session TTL, snapshot interval).
- [ ] L6. No `kubectl rollout` test command for verifying GUI deployment.

### M. Monitoring & Operations Gaps

- [ ] M1. No metrics for active GUI sessions.
- [ ] M2. No metrics for GUI-triggered simulations.
- [ ] M3. No logging for GUI operations (session create, document save, run).
- [ ] M4. No health check for GUI sub-app.
- [ ] M5. No alerting for session cleanup failures.
- [ ] M6. No SSE connection count metric.
- [ ] M7. **[NICE]** No Grafana dashboard for GUI usage.

### N. Feature Gaps (Future)

- [ ] N1. **[NICE]** Collaborative editing (multiple users on same canvas).
- [ ] N2. **[NICE]** Version history for canvas documents.
- [ ] N3. **[NICE]** Export simulation video from time-scrubber playback.
- [ ] N4. **[NICE]** Compare mode (side-by-side simulation results).
- [ ] N5. **[NICE]** Template library (save/load process-bigraph subgraphs).
- [ ] N6. **[NICE]** Parameter sweep (run many simulations with varying params from GUI).
- [ ] N7. **[NICE]** 3D visualization integration for spatial simulations.
- [ ] N8. **[NICE]** AI-assisted model building (LLM suggests processes/connections).
- [ ] N9. **[NICE]** Mobile-responsive canvas (tablet input).
- [ ] N10. **[NICE]** Batch mode — queue multiple simulation runs from GUI.
- [ ] N11. **[NICE]** Integration with BioModels — load BioModel as canvas starting point.
- [ ] N12. **[NICE]** Shareable session URLs (public read-only view).
- [ ] N13. **[NICE]** Plugin system for custom node types.
- [ ] N14. **[NICE]** Real-time collaboration (WebSocket-based, multiuser).

---

## Total Gaps Count

| Category | Count | CRITICAL | NICE |
|----------|-------|----------|------|
| A — Core Integration | 5 | 5 | 0 |
| B — Session Management | 6 | 0 | 0 |
| C — SSE Streaming | 8 | 1 | 0 |
| D — Simulation Dispatch | 7 | 3 | 0 |
| E — Frontend | 13 | 0 | 1 |
| F — CLI Integration | 6 | 0 | 0 |
| G — TUI Integration | 3 | 0 | 0 |
| H — Testing | 10 | 0 | 0 |
| I — Documentation | 9 | 0 | 0 |
| J — Security | 7 | 0 | 1 |
| K — Performance | 7 | 0 | 1 |
| L — Deployment | 6 | 0 | 0 |
| M — Monitoring & Ops | 7 | 0 | 1 |
| N — Future Features | 14 | 0 | 14 |
| **Total** | **107** | **9** | **18** |

**9 CRITICAL gaps must be resolved before the integrated GUI can function at all.** The remaining 98 are important but can be addressed incrementally.
