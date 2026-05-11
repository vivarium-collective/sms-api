"""WrapperGenerationService: bundles and stores pbg-* wrapper repos.

Phase 2: config keys, bundling utilities, FileService storage, SKILL.md resolution.
Phase 3: agent integration (Anthropic API with pbg-expert SKILL.md as system prompt).
Phase 3b: deterministic scaffold path (no LLM required — uses explicit port/config definitions).
Phase 4: container build dispatch (reuse compose SLURM build pipeline).
"""

from __future__ import annotations

import asyncio
import logging
import tarfile
import tempfile
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sms_api.common.storage.file_paths import S3FilePath
from sms_api.compose.models import PbgConfigParam, PbgPortSchema, WrapperStatus

if TYPE_CHECKING:
    from sms_api.common.storage.file_service import FileService
    from sms_api.compose.database_service import ComposeDatabaseService
    from sms_api.compose.simulation_service import ComposeSimulationService

logger = logging.getLogger(__name__)

# Default SKILL.md location: sibling pbg-superpowers repo (dev environment).
# Override via compose_pbg_expert_skill_path setting (required at deploy time).
_DEFAULT_SKILL_MD_PATH = (
    Path(__file__).parent.parent.parent.parent / "pbg-superpowers" / "skills" / "pbg-expert" / "SKILL.md"
)

# Sandboxed tool definitions for the pbg-expert agentic loop.
_AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": (
            "Write text content to a file inside the workspace directory. "
            "Creates parent directories as needed. Path must be relative to the workspace root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path within the workspace"},
                "content": {"type": "string", "description": "File content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file's text content from the workspace directory. Path must be relative to the workspace root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path within the workspace"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_bash",
        "description": (
            "Run a shell command inside the workspace directory. "
            "Commands are sandboxed — the working directory is fixed to the workspace root. "
            "stdout and stderr are returned as a combined string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["command"],
        },
    },
]

_MAX_AGENT_ITERATIONS = 50
_BASH_TIMEOUT_SECONDS = 60


def get_skill_md_path() -> Path:
    """Return the absolute path to the pbg-expert SKILL.md.

    Resolution order:
    1. ``compose_pbg_expert_skill_path`` setting (allows prod override via env var).
    2. Sibling ``../pbg-superpowers/skills/pbg-expert/SKILL.md`` (dev default).
    """
    from sms_api.config import get_settings

    configured = get_settings().compose_pbg_expert_skill_path
    if configured:
        return Path(configured)
    return _DEFAULT_SKILL_MD_PATH


def derive_tool_name(repo_url: str) -> str:
    """Extract a clean lowercase-hyphenated tool name from a GitHub URL.

    Examples:
        https://github.com/vivarium-collective/mem3dg       → "mem3dg"
        https://github.com/vivarium-collective/pbg-cobra    → "cobra"
        https://github.com/vivarium-collective/mem3dg.git   → "mem3dg"
        https://github.com/org/My_Tool.git                 → "my-tool"
    """
    name = repo_url.rstrip("/").split("/")[-1]
    name = name.removesuffix(".git")
    name = name.removeprefix("pbg-")
    return name.lower().replace("_", "-")


class WrapperGenerationService:
    """Orchestrates pbg-* wrapper generation, storage, and container build dispatch."""

    def __init__(
        self,
        db: ComposeDatabaseService,
        file_service: FileService | None,
        sim_service: ComposeSimulationService | None = None,
    ) -> None:
        self._db = db
        self._file_service = file_service
        self._sim_service = sim_service

    # ------------------------------------------------------------------
    # Storage utilities (Phase 2)
    # ------------------------------------------------------------------

    @staticmethod
    def bundle_wrapper(repo_dir: Path, tarball_path: Path) -> None:
        """Bundle a wrapper repo directory into a gzipped tarball.

        Args:
            repo_dir: Root of the generated ``pbg-<tool>/`` directory.
            tarball_path: Destination ``.tar.gz`` file path.
        """
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(repo_dir, arcname=repo_dir.name)

    async def store_tarball(self, wrapper_id: int, tool_name: str, tarball_path: Path) -> str:
        """Upload the wrapper tarball to storage and return the backend-relative key.

        Args:
            wrapper_id: DB primary key of the wrapper record (used in the storage path).
            tool_name: Clean tool name, e.g. ``"mem3dg"``.
            tarball_path: Local path to the ``.tar.gz`` file to upload.

        Returns:
            The S3 key (backend-relative path string), e.g.
            ``"pbg-wrappers/1/pbg-mem3dg.tar.gz"``.

        Raises:
            RuntimeError: If no FileService is configured.
        """
        from sms_api.config import get_settings

        if self._file_service is None:
            raise RuntimeError("FileService is not configured; cannot store wrapper tarball")

        prefix = get_settings().compose_pbg_wrappers_storage_prefix
        key = f"{prefix}/{wrapper_id}/pbg-{tool_name}.tar.gz"
        s3_path = S3FilePath(s3_path=Path(key))
        await self._file_service.upload_file(file_path=tarball_path, s3_path=s3_path)
        return key

    # ------------------------------------------------------------------
    # Sandboxed tool execution helpers (Phase 3)
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_sandbox_path(workspace: Path, rel_path: str) -> Path:
        """Resolve a relative path within the workspace, preventing traversal."""
        resolved = (workspace / rel_path).resolve()
        workspace_resolved = workspace.resolve()
        if not str(resolved).startswith(str(workspace_resolved)):
            raise ValueError(f"Path traversal attempt blocked: {rel_path!r}")
        return resolved

    @staticmethod
    async def _execute_tool(workspace: Path, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a sandboxed tool call and return its string result."""
        if tool_name == "write_file":
            path = WrapperGenerationService._resolve_sandbox_path(workspace, tool_input["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(tool_input["content"], encoding="utf-8")
            return f"wrote {len(tool_input['content'])} bytes to {tool_input['path']}"

        if tool_name == "read_file":
            path = WrapperGenerationService._resolve_sandbox_path(workspace, tool_input["path"])
            if not path.exists():
                return f"error: file not found: {tool_input['path']}"
            return path.read_text(encoding="utf-8")

        if tool_name == "run_bash":
            proc = await asyncio.create_subprocess_shell(
                tool_input["command"],
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_BASH_TIMEOUT_SECONDS)
            except TimeoutError:
                proc.kill()
                return f"error: command timed out after {_BASH_TIMEOUT_SECONDS}s"
            return stdout.decode("utf-8", errors="replace")

        return f"error: unknown tool {tool_name!r}"

    # ------------------------------------------------------------------
    # Agent integration (Phase 3)
    # ------------------------------------------------------------------

    async def _run_pbg_expert_agent(
        self,
        workspace: Path,
        source_repo_url: str,
        tool_name: str,
        source_ref: str,
        extra_instructions: str | None,
    ) -> None:
        """Invoke the pbg-expert skill via the Anthropic Messages API.

        Loads pbg-expert SKILL.md as the system prompt, sends the source repo URL
        as the user message, and executes sandboxed file-system tool calls that
        create ``pbg-<tool>/`` files inside ``workspace``.
        """
        import anthropic

        from sms_api.config import get_settings

        settings = get_settings()
        api_key = settings.compose_pbg_anthropic_api_key
        if not api_key:
            raise RuntimeError("COMPOSE_PBG_ANTHROPIC_API_KEY is not configured")

        skill_path = get_skill_md_path()
        if not skill_path.exists():
            raise RuntimeError(f"pbg-expert SKILL.md not found at {skill_path}")
        system_prompt = skill_path.read_text(encoding="utf-8")

        user_message = f"Tool name: {tool_name}\nSource repository: {source_repo_url}\nBranch/ref: {source_ref}"
        if extra_instructions:
            user_message += f"\n\nAdditional instructions:\n{extra_instructions}"

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        client = anthropic.AsyncAnthropic(api_key=api_key)

        for iteration in range(_MAX_AGENT_ITERATIONS):
            response = await client.messages.create(
                model="claude-opus-4-6",
                max_tokens=8096,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                tools=_AGENT_TOOLS,  # type: ignore[arg-type]
            )
            logger.debug(
                "Wrapper agent iteration %d: stop_reason=%s, content_blocks=%d",
                iteration,
                response.stop_reason,
                len(response.content),
            )

            # Append the assistant's response to the conversation.
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                logger.info("pbg-expert agent finished after %d iterations", iteration + 1)
                return

            if response.stop_reason != "tool_use":
                logger.warning("Unexpected stop_reason %r — treating as done", response.stop_reason)
                return

            # Execute all tool calls in this response.
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_str = await self._execute_tool(workspace, block.name, block.input)
                logger.debug("Tool %r → %d chars", block.name, len(result_str))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError(f"Agent loop exceeded {_MAX_AGENT_ITERATIONS} iterations without finishing")

    # ------------------------------------------------------------------
    # Container build dispatch (Phase 4)
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_wrapper_def(tool_name: str, hpc_tarball_path: str) -> str:
        """Return Singularity .def text for a pbg-<tool> wrapper container.

        The generated container:
        - Bootstraps from ``ghcr.io/astral-sh/uv:python3.12-bookworm`` (same base as existing compose containers)
        - Installs micromamba + process-bigraph + bigraph-schema
        - Copies the wrapper tarball (from ``hpc_tarball_path`` on the build host) and pip-installs it
        """
        _MICROMAMBA_ENV = "/micromamba_env/runtime_env"
        return (
            "Bootstrap: docker\n"
            "From: ghcr.io/astral-sh/uv:python3.12-bookworm\n"
            "\n"
            "%files\n"
            f"    {hpc_tarball_path} /tmp/pbg-{tool_name}.tar.gz\n"
            "\n"
            "%post\n"
            "    apt-get update -y && apt-get install -y git curl\n"
            "    mkdir -p /usr/local/bin\n"
            "    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest"
            " | tar -xvj bin/micromamba --strip-components=1 -C /usr/local/bin/\n"
            f"    micromamba create -p {_MICROMAMBA_ENV} python=3.12 -y\n"
            f"    micromamba run -p {_MICROMAMBA_ENV} pip install process-bigraph bigraph-schema\n"
            f"    cd /tmp && tar -xzf pbg-{tool_name}.tar.gz\n"
            f"    micromamba run -p {_MICROMAMBA_ENV} pip install /tmp/pbg-{tool_name}/\n"
            f"    rm -rf /tmp/pbg-{tool_name} /tmp/pbg-{tool_name}.tar.gz\n"
            "\n"
            "%environment\n"
            f"    export PATH={_MICROMAMBA_ENV}/bin:$PATH\n"
        )

    async def _dispatch_container_build(
        self,
        wrapper_id: int,
        tool_name: str,
        tarball_path: Path,
    ) -> int:
        """Upload the wrapper tarball to HPC, generate a Singularity .def, and submit a build job.

        Status transition: ``READY`` → ``BUILDING`` (stored on the wrapper record).

        Args:
            wrapper_id: DB primary key of the wrapper record.
            tool_name: Clean tool name, e.g. ``"mem3dg"``.
            tarball_path: Local path to the already-bundled ``.tar.gz`` file.

        Returns:
            The ``ComposeSimulatorVersion.database_id`` for the newly created simulator record.

        Raises:
            RuntimeError: If no simulation service or ``compose_image_base_path`` is configured.
        """
        import random
        import string

        from pbest.utils.input_types import ContainerizationFileRepr

        from sms_api.common.models import SSHTarget
        from sms_api.common.storage.file_paths import HPCFilePath
        from sms_api.compose.models import get_singularity_hash
        from sms_api.config import get_settings
        from sms_api.dependencies import get_ssh_session_service

        if self._sim_service is None:
            raise RuntimeError("ComposeSimulationService is not configured; cannot dispatch container build")

        settings = get_settings()
        if not settings.compose_image_base_path:
            raise RuntimeError("compose_image_base_path is not configured; cannot dispatch container build")

        # 1. Determine the HPC path for the tarball (shared filesystem, visible at build time).
        hpc_tarball_path = Path(settings.compose_image_base_path) / f"pbg-{tool_name}-{wrapper_id}.tar.gz"

        # 2. Generate Singularity .def (references the HPC tarball path in %files).
        def_text = self._generate_wrapper_def(tool_name, str(hpc_tarball_path))
        singularity_rep = ContainerizationFileRepr(representation=def_text)
        singularity_hash = get_singularity_hash(singularity_rep)

        # 3. Insert or reuse the simulator version record.
        simulator_db = self._db.get_simulator_db()
        simulator_version = await simulator_db.get_simulator_by_def_hash(singularity_hash)
        if simulator_version is None:
            simulator_version = await simulator_db.insert_simulator(singularity_rep)

        # 4. SCP the tarball to HPC so the SLURM build job can access it via %files.
        async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
            await ssh.run_command(f"mkdir -p {settings.compose_image_base_path}")
            await ssh.scp_upload(
                local_file=tarball_path,
                remote_path=HPCFilePath(remote_path=hpc_tarball_path),
            )

        # 5. Submit SLURM build job (also SCPs the .def and records ORMComposeHpcRun).
        random_str = "".join(random.choices(string.hexdigits, k=5))
        await self._sim_service.build_container(
            simulator_version=simulator_version,
            random_str=random_str,
            db_service=self._db,
        )

        # 6. Update wrapper: set simulator_id and transition status to BUILDING.
        await self._db.get_wrapper_db().update_wrapper_simulator_id(
            wrapper_id=wrapper_id,
            simulator_id=simulator_version.database_id,
        )
        logger.info(
            "Wrapper %d dispatched to build as simulator %d (hash=%s)",
            wrapper_id,
            simulator_version.database_id,
            singularity_hash[:8],
        )
        return simulator_version.database_id

    @staticmethod
    def _locate_repo_dir(workspace: Path) -> Path:
        """Return the first pbg-* (or any) subdirectory created by the agent.

        Raises:
            RuntimeError: If the agent produced no output directory.
        """
        candidates = [d for d in workspace.iterdir() if d.is_dir() and d.name.startswith("pbg-")]
        if not candidates:
            candidates = [d for d in workspace.iterdir() if d.is_dir()]
        if not candidates:
            raise RuntimeError("Agent produced no output directory in workspace")
        return candidates[0]

    # ------------------------------------------------------------------
    # Deterministic scaffold path (Phase 3b — no LLM required)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_tool_slug(tool_name: str) -> str:
        """Convert a hyphenated tool name to a Python-importable slug.

        Examples:
            "mem3dg"    → "mem3dg"
            "my-tool"   → "my_tool"
        """
        return tool_name.replace("-", "_")

    @staticmethod
    def _to_class_name(tool_name: str) -> str:
        """Convert a hyphenated tool name to a CamelCase class name.

        Examples:
            "mem3dg"    → "Mem3dg"
            "my-tool"   → "MyTool"
        """
        return "".join(part.capitalize() for part in tool_name.replace("-", "_").split("_"))

    @staticmethod
    def _render_ports_dict(ports: list[PbgPortSchema], indent: int = 8) -> str:
        """Render a list of PbgPortSchema entries as a Python dict literal body."""
        if not ports:
            return " " * indent + "# TODO: define ports\n"
        pad = " " * indent
        lines = [f'{pad}"{p.name}": "{p.schema_expr}",' for p in ports]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_config_schema(params: list[PbgConfigParam], indent: int = 8) -> str:
        """Render a list of PbgConfigParam entries as a Python dict literal body."""
        if not params:
            return " " * indent + "# TODO: define config\n"
        pad = " " * indent
        lines: list[str] = []
        for p in params:
            default_repr = repr(p.default) if p.default is not None else repr(0.0 if p.type == "float" else "")
            lines.append(f'{pad}"{p.name}": {{"_type": "{p.type}", "_default": {default_repr}}},')
        return "\n".join(lines) + "\n"

    def _scaffold_wrapper(
        self,
        workspace: Path,
        tool_name: str,
        source_repo_url: str,
        source_ref: str,
        process_type: str,
        input_ports: list[PbgPortSchema],
        output_ports: list[PbgPortSchema],
        config_params: list[PbgConfigParam],
    ) -> None:
        """Generate a complete pip-installable pbg-<tool> wrapper package deterministically.

        No LLM is required. Creates the full package structure inside
        ``workspace/pbg-<tool>/`` using string templates and the port/config
        definitions provided by the caller.

        Args:
            workspace: Temp directory to write the package into.
            tool_name: Clean hyphenated tool name (e.g. ``"mem3dg"``).
            source_repo_url: URL of the wrapped tool's source repo (informational).
            source_ref: Git ref of the source (informational).
            process_type: ``"Process"`` or ``"Step"``.
            input_ports: List of input port definitions.
            output_ports: List of output port definitions.
            config_params: List of config parameter definitions.
        """
        slug = self._to_tool_slug(tool_name)
        class_name = self._to_class_name(tool_name)
        base_class = "Process" if process_type == "Process" else "Step"
        pkg_dir = workspace / f"pbg-{tool_name}" / f"pbg_{slug}"
        repo_dir = workspace / f"pbg-{tool_name}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "tests").mkdir(exist_ok=True)

        # ---- pyproject.toml ----
        (repo_dir / "pyproject.toml").write_text(
            textwrap.dedent(f"""\
                [project]
                name = "pbg-{tool_name}"
                version = "0.1.0"
                requires-python = ">=3.11"
                dependencies = [
                    "bigraph-schema",
                    "process-bigraph",
                ]

                [build-system]
                requires = ["hatchling"]
                build-backend = "hatchling.build"

                [tool.hatch.build.targets.wheel]
                packages = ["pbg_{slug}"]

                [tool.pytest.ini_options]
                testpaths = ["tests"]
            """)
        )

        # ---- .gitignore ----
        (repo_dir / ".gitignore").write_text(
            textwrap.dedent("""\
                .venv/
                __pycache__/
                *.egg-info/
                dist/
                build/
                *.pyc
                .pytest_cache/
                output/
                .idea/
            """)
        )

        # ---- pbg_<slug>/__init__.py ----
        (pkg_dir / "__init__.py").write_text(
            textwrap.dedent(f"""\
                \"\"\"pbg-{tool_name}: process-bigraph wrapper for {class_name}.\"\"\"

                from .processes import {class_name}{base_class}

                __all__ = ["{class_name}{base_class}"]
            """)
        )

        # ---- pbg_<slug>/types.py ----
        (pkg_dir / "types.py").write_text(
            textwrap.dedent(f"""\
                \"\"\"Custom bigraph-schema types for pbg-{tool_name}. Empty by default.\"\"\"
            """)
        )

        # ---- pbg_<slug>/processes.py ----
        update_body = (
            "        # TODO: call the wrapped tool here\n        return {}"
            if base_class == "Step"
            else "        # TODO: call the wrapped tool for `interval` seconds and return deltas\n        return {}"
        )
        if base_class == "Step":
            update_sig = "    def update(self, state):"
        else:
            update_sig = "    def update(self, state, interval):"
        input_ports_body = self._render_ports_dict(input_ports, indent=8)
        output_ports_body = self._render_ports_dict(output_ports, indent=8)
        config_schema_body = self._render_config_schema(config_params, indent=8)

        (pkg_dir / "processes.py").write_text(
            textwrap.dedent(f"""\
                \"\"\"{class_name} process-bigraph wrapper.

                Source: {source_repo_url}  (ref: {source_ref})

                This file was generated by the sms-api deterministic scaffold.
                Fill in the `update()` method body to integrate the wrapped tool.
                \"\"\"

                from process_bigraph import {base_class}


                class {class_name}{base_class}({base_class}):
                    \"\"\"{"Time-stepped" if base_class == "Process" else "Stateless"} wrapper for {class_name}.\"\"\"

                    config_schema = {{
            """)
            + config_schema_body
            + textwrap.dedent("""\
                    }

                    def inputs(self):
                        return {
            """)
            + input_ports_body
            + textwrap.dedent("""\
                        }

                    def outputs(self):
                        return {
            """)
            + output_ports_body
            + textwrap.dedent("""\
                        }

                    def initial_state(self):
                        return {}

            """)
            + update_sig
            + "\n"
            + update_body
            + "\n"
        )

        # ---- pbg_<slug>/composites.py ----
        (pkg_dir / "composites.py").write_text(
            textwrap.dedent(f"""\
                \"\"\"Composite factory functions for pbg-{tool_name}.\"\"\"
                from process_bigraph import Composite, allocate_core

                from pbg_{slug} import {class_name}{base_class}


                def make_{slug}_composite(config=None, duration=100.0):
                    core = allocate_core()
                    core.register_link("{class_name}{base_class}", {class_name}{base_class})

                    document = {{
                        "process": {{
                            "_type": "{"process" if base_class == "Process" else "step"}",
                            "address": "local:{class_name}{base_class}",
                            "config": config or {{}},
                            {"'interval': 1.0," if base_class == "Process" else ""}
                            "inputs": {{}},   # TODO: wire to stores
                            "outputs": {{}},  # TODO: wire to stores
                        }},
                        "stores": {{}},
                    }}

                    return Composite({{"state": document}}, core=core)
            """)
        )

        # ---- tests/__init__.py ----
        (repo_dir / "tests" / "__init__.py").write_text("")

        # ---- tests/test_processes.py ----
        (repo_dir / "tests" / "test_processes.py").write_text(
            textwrap.dedent(f"""\
                \"\"\"Tests for pbg-{tool_name} processes.\"\"\"
                from process_bigraph import allocate_core

                from pbg_{slug} import {class_name}{base_class}


                def _make_proc():
                    core = allocate_core()
                    core.register_link("{class_name}{base_class}", {class_name}{base_class})
                    return {class_name}{base_class}(config={{}}, core=core)


                def test_{slug}_instantiation():
                    proc = _make_proc()
                    assert proc is not None


                def test_{slug}_inputs():
                    proc = _make_proc()
                    assert isinstance(proc.inputs(), dict)


                def test_{slug}_outputs():
                    proc = _make_proc()
                    assert isinstance(proc.outputs(), dict)
            """)
        )

        # ---- README.md ----
        _inp_lines = (
            "".join(
                f"- `{p.name}`: `{p.schema_expr}`{f' — {p.description}' if p.description else ''}\n"
                for p in input_ports
            )
            or "- *(none defined yet)*"
        )
        _out_lines = (
            "".join(
                f"- `{p.name}`: `{p.schema_expr}`{f' — {p.description}' if p.description else ''}\n"
                for p in output_ports
            )
            or "- *(none defined yet)*"
        )
        _cfg_lines = (
            "".join(
                f"- `{p.name}` (`{p.type}`, default `{p.default}`){f': {p.description}' if p.description else ''}\n"
                for p in config_params
            )
            or "- *(none defined yet)*"
        )
        (repo_dir / "README.md").write_text(
            textwrap.dedent(f"""\
                # pbg-{tool_name}

                Process-bigraph wrapper for **{class_name}**.

                - Source: [{source_repo_url}]({source_repo_url}) (ref: `{source_ref}`)
                - Process type: `{base_class}`

                ## Installation

                ```bash
                pip install -e .
                ```

                Once installed via `pip install -e .`, processes register automatically
                via `bigraph_schema.package.discover` — no manual `register_link()` calls needed.

                ## Quick Start

                ```python
                from process_bigraph import allocate_core
                from pbg_{slug} import {class_name}{base_class}

                core = allocate_core()
                proc = {class_name}{base_class}(config={{}}, core=core)
                result = proc.{
                "update(proc.initial_state(), interval=1.0)"
                if base_class == "Process"
                else "update(proc.initial_state())"
            }
                print(result)
                ```

                ## Ports

                ### Inputs
                {_inp_lines}
                ### Outputs
                {_out_lines}
                ## Config Parameters
                {_cfg_lines}

                ## Notes

                This wrapper was scaffolded automatically by the sms-api. The `update()` method
                body is a stub — fill it in to integrate the wrapped tool's simulation step.
            """)
        )

        logger.info(
            "Scaffolded wrapper for tool '%s' at %s (%d input ports, %d output ports, %d config params)",
            tool_name,
            repo_dir,
            len(input_ports),
            len(output_ports),
            len(config_params),
        )

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def generate_wrapper(
        self,
        wrapper_id: int,
        source_repo_url: str,
        tool_name: str,
        source_ref: str = "main",
        extra_instructions: str | None = None,
        process_type: str = "Process",
        input_ports: list[PbgPortSchema] | None = None,
        output_ports: list[PbgPortSchema] | None = None,
        config_params: list[PbgConfigParam] | None = None,
        use_agent: bool = True,
    ) -> None:
        """Full wrapper generation pipeline (background task).

        Two code paths:
        - **Agent path** (default): calls the Claude API pbg-expert agent to analyse the source
          repo and generate the wrapper files. Requires ``COMPOSE_PBG_ANTHROPIC_API_KEY``.
        - **Scaffold path**: deterministically generates a complete, pip-installable wrapper
          package from the ``input_ports``/``output_ports``/``config_params`` provided in the
          request. No API key or LLM required.

        ``use_agent=False`` OR a missing API key forces the scaffold path.
        """
        from sms_api.config import get_settings

        _use_agent = use_agent and bool(get_settings().compose_pbg_anthropic_api_key)

        wrapper_db = self._db.get_wrapper_db()
        try:
            with tempfile.TemporaryDirectory() as _tmpdir:
                workspace = Path(_tmpdir)

                if _use_agent:
                    # Agent path — writes pbg-<tool>/ into workspace.
                    await self._run_pbg_expert_agent(
                        workspace=workspace,
                        source_repo_url=source_repo_url,
                        tool_name=tool_name,
                        source_ref=source_ref,
                        extra_instructions=extra_instructions,
                    )
                else:
                    # Scaffold path — no LLM required.
                    self._scaffold_wrapper(
                        workspace=workspace,
                        tool_name=tool_name,
                        source_repo_url=source_repo_url,
                        source_ref=source_ref,
                        process_type=process_type,
                        input_ports=input_ports or [],
                        output_ports=output_ports or [],
                        config_params=config_params or [],
                    )

                # 2. Locate generated repo dir (first pbg-* subdirectory).
                repo_dir = self._locate_repo_dir(workspace)

                # 3. Bundle into tarball.
                await wrapper_db.update_wrapper_status(wrapper_id=wrapper_id, status=WrapperStatus.STORING)
                tarball_path = workspace / f"pbg-{tool_name}.tar.gz"
                self.bundle_wrapper(repo_dir, tarball_path)

                # 4. Upload to storage.
                storage_uri = await self.store_tarball(wrapper_id, tool_name, tarball_path)
                await wrapper_db.update_wrapper_status(
                    wrapper_id=wrapper_id,
                    status=WrapperStatus.READY,
                    storage_uri=storage_uri,
                )
                logger.info("Wrapper %d ready at %s", wrapper_id, storage_uri)

                # 5. Dispatch container build while tarball is still on disk.
                if self._sim_service is not None:
                    await self._dispatch_container_build(wrapper_id, tool_name, tarball_path)
                else:
                    logger.info("Wrapper %d: skipping container build (no sim service configured)", wrapper_id)

        except Exception as exc:
            await wrapper_db.update_wrapper_status(
                wrapper_id=wrapper_id,
                status=WrapperStatus.FAILED,
                error_message=str(exc),
            )
            logger.exception("Wrapper generation failed for wrapper %d", wrapper_id)
            raise
