"""Tests for WrapperGenerationService utilities and derive_tool_name helper (Phases 2, 3, 3b & 4)."""

from __future__ import annotations

import tarfile
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sms_api.compose.wrapper_service import WrapperGenerationService, derive_tool_name, get_skill_md_path

# ---------------------------------------------------------------------------
# derive_tool_name tests
# ---------------------------------------------------------------------------


class TestDeriveToolName:
    def test_simple_github_url(self) -> None:
        assert derive_tool_name("https://github.com/vivarium-collective/mem3dg") == "mem3dg"

    def test_strips_git_suffix(self) -> None:
        assert derive_tool_name("https://github.com/vivarium-collective/mem3dg.git") == "mem3dg"

    def test_strips_pbg_prefix(self) -> None:
        assert derive_tool_name("https://github.com/vivarium-collective/pbg-cobra") == "cobra"

    def test_strips_pbg_prefix_and_git_suffix(self) -> None:
        assert derive_tool_name("https://github.com/vivarium-collective/pbg-cobra.git") == "cobra"

    def test_lowercases(self) -> None:
        assert derive_tool_name("https://github.com/org/MyTool") == "mytool"

    def test_underscores_to_hyphens(self) -> None:
        assert derive_tool_name("https://github.com/org/my_tool") == "my-tool"

    def test_trailing_slash(self) -> None:
        assert derive_tool_name("https://github.com/org/mem3dg/") == "mem3dg"

    def test_does_not_double_strip_pbg(self) -> None:
        # pbg-pbg-foo → pbg-foo (only one leading "pbg-" removed)
        assert derive_tool_name("https://github.com/org/pbg-pbg-foo") == "pbg-foo"


# ---------------------------------------------------------------------------
# get_skill_md_path tests
# ---------------------------------------------------------------------------


class TestGetSkillMdPath:
    def test_returns_a_path(self) -> None:
        result = get_skill_md_path()
        assert isinstance(result, Path)

    def test_skill_md_exists_in_dev(self) -> None:
        """SKILL.md must exist in the sibling pbg-superpowers repo (dev environment)."""
        path = get_skill_md_path()
        assert path.exists(), (
            f"pbg-expert SKILL.md not found at {path}. Ensure ../pbg-superpowers is present as a sibling of sms-api."
        )

    def test_skill_md_is_readable(self) -> None:
        path = get_skill_md_path()
        if not path.exists():
            pytest.skip("pbg-superpowers sibling repo not present")
        content = path.read_text(encoding="utf-8")
        assert "pbg-expert" in content
        assert "process-bigraph" in content.lower()


# ---------------------------------------------------------------------------
# WrapperGenerationService.bundle_wrapper tests
# ---------------------------------------------------------------------------


class TestBundleWrapper:
    def test_creates_valid_tarball(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            repo_dir = Path(workdir) / "pbg-mem3dg"
            repo_dir.mkdir()
            (repo_dir / "pyproject.toml").write_text('[project]\nname = "pbg-mem3dg"\n')
            (repo_dir / "pbg_mem3dg").mkdir()
            (repo_dir / "pbg_mem3dg" / "__init__.py").write_text("")

            tarball = Path(workdir) / "pbg-mem3dg.tar.gz"
            WrapperGenerationService.bundle_wrapper(repo_dir, tarball)

            assert tarball.exists()
            assert tarball.stat().st_size > 0
            assert tarfile.is_tarfile(tarball)

    def test_tarball_contains_repo_files(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            repo_dir = Path(workdir) / "pbg-cobra"
            repo_dir.mkdir()
            (repo_dir / "README.md").write_text("# pbg-cobra")
            (repo_dir / "pbg_cobra").mkdir()
            (repo_dir / "pbg_cobra" / "processes.py").write_text("# processes")

            tarball = Path(workdir) / "pbg-cobra.tar.gz"
            WrapperGenerationService.bundle_wrapper(repo_dir, tarball)

            with tarfile.open(tarball, "r:gz") as tar:
                names = tar.getnames()

            assert any("README.md" in n for n in names)
            assert any("processes.py" in n for n in names)

    def test_tarball_arcname_is_repo_dir_name(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            repo_dir = Path(workdir) / "pbg-tellurium"
            repo_dir.mkdir()
            (repo_dir / "file.txt").write_text("content")

            tarball = Path(workdir) / "out.tar.gz"
            WrapperGenerationService.bundle_wrapper(repo_dir, tarball)

            with tarfile.open(tarball, "r:gz") as tar:
                names = tar.getnames()

            # All paths inside the tarball should start with the repo dir name
            assert all(n.startswith("pbg-tellurium") for n in names)

    def test_empty_repo_dir_produces_tarball(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            repo_dir = Path(workdir) / "pbg-empty"
            repo_dir.mkdir()

            tarball = Path(workdir) / "pbg-empty.tar.gz"
            WrapperGenerationService.bundle_wrapper(repo_dir, tarball)

            assert tarball.exists()
            assert tarfile.is_tarfile(tarball)


# ---------------------------------------------------------------------------
# _execute_tool sandboxed helper tests (Phase 3)
# ---------------------------------------------------------------------------


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_write_file_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            result = await WrapperGenerationService._execute_tool(
                workspace, "write_file", {"path": "hello.py", "content": "print('hi')"}
            )
            assert "wrote" in result
            assert (workspace / "hello.py").read_text() == "print('hi')"

    @pytest.mark.asyncio
    async def test_write_file_creates_nested_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            await WrapperGenerationService._execute_tool(
                workspace, "write_file", {"path": "pbg_tool/processes.py", "content": "# processes"}
            )
            assert (workspace / "pbg_tool" / "processes.py").exists()

    @pytest.mark.asyncio
    async def test_read_file_returns_content(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            (workspace / "README.md").write_text("# hello", encoding="utf-8")
            result = await WrapperGenerationService._execute_tool(workspace, "read_file", {"path": "README.md"})
            assert result == "# hello"

    @pytest.mark.asyncio
    async def test_read_file_missing_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            result = await WrapperGenerationService._execute_tool(
                Path(workdir), "read_file", {"path": "nonexistent.txt"}
            )
            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_run_bash_echo(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            result = await WrapperGenerationService._execute_tool(Path(workdir), "run_bash", {"command": "echo hello"})
            assert "hello" in result

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            result = await WrapperGenerationService._execute_tool(Path(workdir), "nonexistent_tool", {})
            assert "unknown tool" in result

    def test_resolve_sandbox_path_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            with pytest.raises(ValueError, match="traversal"):
                WrapperGenerationService._resolve_sandbox_path(workspace, "../../etc/passwd")


# ---------------------------------------------------------------------------
# _run_pbg_expert_agent agentic loop tests (Phase 3) — Anthropic SDK mocked
# ---------------------------------------------------------------------------


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(name: str, tool_input: dict[str, Any], tool_id: str = "tu_1") -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = tool_input
    block.id = tool_id
    return block


def _end_turn_response(text: str = "Done.") -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [_make_text_block(text)]
    return resp


def _tool_use_response(blocks: list[MagicMock]) -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = blocks
    return resp


def _make_service() -> WrapperGenerationService:
    db_mock = MagicMock()
    return WrapperGenerationService(db=db_mock, file_service=None)


class TestRunPbgExpertAgent:
    """Tests for WrapperGenerationService._run_pbg_expert_agent."""

    @pytest.mark.asyncio
    async def test_raises_without_api_key(self) -> None:
        svc = _make_service()
        with (
            tempfile.TemporaryDirectory() as workdir,
            patch("sms_api.compose.wrapper_service.get_skill_md_path") as mock_path,
            patch("sms_api.config.get_settings") as mock_settings,
        ):
            mock_path.return_value = Path(workdir) / "SKILL.md"
            Path(workdir, "SKILL.md").write_text("# skill", encoding="utf-8")
            mock_settings.return_value.compose_pbg_anthropic_api_key = ""
            with pytest.raises(RuntimeError, match="COMPOSE_PBG_ANTHROPIC_API_KEY"):
                await svc._run_pbg_expert_agent(
                    workspace=Path(workdir),
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="main",
                    extra_instructions=None,
                )

    @pytest.mark.asyncio
    async def test_raises_when_skill_md_missing(self) -> None:
        svc = _make_service()
        with (
            tempfile.TemporaryDirectory() as workdir,
            patch("sms_api.compose.wrapper_service.get_skill_md_path") as mock_path,
            patch("sms_api.config.get_settings") as mock_settings,
        ):
            mock_path.return_value = Path(workdir) / "NONEXISTENT.md"
            mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-test"
            with pytest.raises(RuntimeError, match="SKILL.md not found"):
                await svc._run_pbg_expert_agent(
                    workspace=Path(workdir),
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="main",
                    extra_instructions=None,
                )

    @pytest.mark.asyncio
    async def test_end_turn_on_first_response(self) -> None:
        """Agent finishes immediately on first end_turn response."""
        svc = _make_service()
        with tempfile.TemporaryDirectory() as workdir:
            skill_path = Path(workdir) / "SKILL.md"
            skill_path.write_text("# pbg-expert skill", encoding="utf-8")

            messages_create = AsyncMock(return_value=_end_turn_response("All done."))
            mock_client = MagicMock()
            mock_client.messages.create = messages_create

            with (
                patch("sms_api.compose.wrapper_service.get_skill_md_path", return_value=skill_path),
                patch("sms_api.config.get_settings") as mock_settings,
                patch("anthropic.AsyncAnthropic", return_value=mock_client),
            ):
                mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-test"
                await svc._run_pbg_expert_agent(
                    workspace=Path(workdir),
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="main",
                    extra_instructions=None,
                )

            messages_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_call_then_end_turn(self) -> None:
        """Agent executes one write_file call then finishes on second turn."""
        svc = _make_service()
        with tempfile.TemporaryDirectory() as workdir:
            skill_path = Path(workdir) / "SKILL.md"
            skill_path.write_text("# pbg-expert skill", encoding="utf-8")
            workspace = Path(workdir)

            write_block = _make_tool_use_block(
                "write_file", {"path": "pbg-tool/hello.py", "content": "# hello"}, "tu_write"
            )
            tool_use_resp = _tool_use_response([write_block])
            end_resp = _end_turn_response("Done.")

            messages_create = AsyncMock(side_effect=[tool_use_resp, end_resp])
            mock_client = MagicMock()
            mock_client.messages.create = messages_create

            with (
                patch("sms_api.compose.wrapper_service.get_skill_md_path", return_value=skill_path),
                patch("sms_api.config.get_settings") as mock_settings,
                patch("anthropic.AsyncAnthropic", return_value=mock_client),
            ):
                mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-test"
                await svc._run_pbg_expert_agent(
                    workspace=workspace,
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="main",
                    extra_instructions=None,
                )

            assert messages_create.call_count == 2
            assert (workspace / "pbg-tool" / "hello.py").exists()

    @pytest.mark.asyncio
    async def test_extra_instructions_included_in_user_message(self) -> None:
        svc = _make_service()
        with tempfile.TemporaryDirectory() as workdir:
            skill_path = Path(workdir) / "SKILL.md"
            skill_path.write_text("# pbg-expert skill", encoding="utf-8")

            messages_create = AsyncMock(return_value=_end_turn_response())
            mock_client = MagicMock()
            mock_client.messages.create = messages_create

            with (
                patch("sms_api.compose.wrapper_service.get_skill_md_path", return_value=skill_path),
                patch("sms_api.config.get_settings") as mock_settings,
                patch("anthropic.AsyncAnthropic", return_value=mock_client),
            ):
                mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-test"
                await svc._run_pbg_expert_agent(
                    workspace=Path(workdir),
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="dev",
                    extra_instructions="Focus on tellurium compatibility.",
                )

            call_kwargs = messages_create.call_args
            first_user_message = call_kwargs.kwargs["messages"][0]["content"]
            assert "Focus on tellurium compatibility." in first_user_message
            assert "dev" in first_user_message

    @pytest.mark.asyncio
    async def test_unexpected_stop_reason_terminates_loop(self) -> None:
        svc = _make_service()
        with tempfile.TemporaryDirectory() as workdir:
            skill_path = Path(workdir) / "SKILL.md"
            skill_path.write_text("# skill", encoding="utf-8")

            resp = MagicMock()
            resp.stop_reason = "max_tokens"
            resp.content = [_make_text_block("partial...")]

            messages_create = AsyncMock(return_value=resp)
            mock_client = MagicMock()
            mock_client.messages.create = messages_create

            with (
                patch("sms_api.compose.wrapper_service.get_skill_md_path", return_value=skill_path),
                patch("sms_api.config.get_settings") as mock_settings,
                patch("anthropic.AsyncAnthropic", return_value=mock_client),
            ):
                mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-test"
                # Should return without raising even on unexpected stop_reason.
                await svc._run_pbg_expert_agent(
                    workspace=Path(workdir),
                    source_repo_url="https://github.com/org/repo",
                    tool_name="tool",
                    source_ref="main",
                    extra_instructions=None,
                )

            messages_create.assert_called_once()


# ---------------------------------------------------------------------------
# _generate_wrapper_def tests (Phase 4)
# ---------------------------------------------------------------------------


class TestGenerateWrapperDef:
    def test_contains_bootstrap_docker(self) -> None:
        result = WrapperGenerationService._generate_wrapper_def("mem3dg", "/hpc/images/pbg-mem3dg-1.tar.gz")
        assert "Bootstrap: docker" in result

    def test_files_section_references_hpc_path(self) -> None:
        hpc_path = "/hpc/images/pbg-mem3dg-1.tar.gz"
        result = WrapperGenerationService._generate_wrapper_def("mem3dg", hpc_path)
        assert hpc_path in result
        assert "%files" in result

    def test_post_section_installs_process_bigraph(self) -> None:
        result = WrapperGenerationService._generate_wrapper_def("mem3dg", "/hpc/pbg-mem3dg-1.tar.gz")
        assert "process-bigraph" in result
        assert "bigraph-schema" in result

    def test_post_section_installs_wrapper_package(self) -> None:
        result = WrapperGenerationService._generate_wrapper_def("cobra", "/hpc/pbg-cobra-2.tar.gz")
        assert "pbg-cobra" in result
        assert "pip install" in result

    def test_environment_section_sets_path(self) -> None:
        result = WrapperGenerationService._generate_wrapper_def("mem3dg", "/hpc/pbg-mem3dg-1.tar.gz")
        assert "%environment" in result
        assert "PATH" in result

    def test_tool_name_used_in_tarball_ref(self) -> None:
        result = WrapperGenerationService._generate_wrapper_def("tellurium", "/hpc/pbg-tellurium-3.tar.gz")
        assert "pbg-tellurium" in result


# ---------------------------------------------------------------------------
# get_wrapper_by_simulator_id DB tests (Phase 4) — SQLite in-memory
# ---------------------------------------------------------------------------


async def _make_wrapper_executor() -> tuple[Any, Any]:
    """Helper: create a SQLite in-memory WrapperORMExecutor (only ORMPbgWrapper table)."""
    from typing import cast

    from sqlalchemy import Table
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from sms_api.compose.database_service import WrapperORMExecutor
    from sms_api.compose.tables_orm import ComposeBase, ORMPbgWrapper

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    tables: list[Table] = [cast(Table, ORMPbgWrapper.__table__)]
    async with engine.begin() as conn:
        await conn.run_sync(ComposeBase.metadata.create_all, tables=tables)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return WrapperORMExecutor(session_maker), engine


@pytest.mark.asyncio
async def test_get_wrapper_by_simulator_id_returns_none_when_missing() -> None:
    executor, engine = await _make_wrapper_executor()
    result = await executor.get_wrapper_by_simulator_id(999)
    assert result is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_wrapper_by_simulator_id_found() -> None:
    from sms_api.compose.models import WrapperStatus

    executor, engine = await _make_wrapper_executor()

    record = await executor.insert_wrapper(
        tool_name="mem3dg",
        source_repo_url="https://github.com/vivarium-collective/mem3dg",
        source_ref="main",
    )
    # Simulate dispatcher: set simulator_id = 42 → status BUILDING
    await executor.update_wrapper_simulator_id(wrapper_id=record.wrapper_id, simulator_id=42)

    found = await executor.get_wrapper_by_simulator_id(42)
    assert found is not None
    assert found.wrapper_id == record.wrapper_id
    assert found.status == WrapperStatus.BUILDING
    assert found.simulator_id == 42
    await engine.dispose()


# ---------------------------------------------------------------------------
# ComposeJobMonitor._handle_wrapper_build_complete (Phase 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_wrapper_build_complete_transitions_to_available() -> None:
    """When a build job completes, the linked wrapper transitions BUILDING → AVAILABLE."""
    from sms_api.compose.job_monitor import ComposeJobMonitor
    from sms_api.compose.models import WrapperStatus

    wrapper_record = MagicMock()
    wrapper_record.wrapper_id = 7
    wrapper_record.status = WrapperStatus.BUILDING

    wrapper_db = AsyncMock()
    wrapper_db.get_wrapper_by_simulator_id = AsyncMock(return_value=wrapper_record)
    wrapper_db.update_wrapper_status = AsyncMock()

    db_mock = MagicMock()
    db_mock.get_wrapper_db = MagicMock(return_value=wrapper_db)

    monitor = ComposeJobMonitor(nats_client=None, database_service=db_mock)
    await monitor._handle_wrapper_build_complete(simulator_id=42)

    wrapper_db.get_wrapper_by_simulator_id.assert_awaited_once_with(42)
    wrapper_db.update_wrapper_status.assert_awaited_once_with(
        wrapper_id=7,
        status=WrapperStatus.AVAILABLE,
    )


@pytest.mark.asyncio
async def test_handle_wrapper_build_complete_noop_when_not_found() -> None:
    """No update is made if no wrapper is linked to the simulator."""
    from sms_api.compose.job_monitor import ComposeJobMonitor

    wrapper_db = AsyncMock()
    wrapper_db.get_wrapper_by_simulator_id = AsyncMock(return_value=None)
    wrapper_db.update_wrapper_status = AsyncMock()

    db_mock = MagicMock()
    db_mock.get_wrapper_db = MagicMock(return_value=wrapper_db)

    monitor = ComposeJobMonitor(nats_client=None, database_service=db_mock)
    await monitor._handle_wrapper_build_complete(simulator_id=99)

    wrapper_db.update_wrapper_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_wrapper_build_complete_noop_when_not_building() -> None:
    """No update is made if the wrapper is already in a terminal state."""
    from sms_api.compose.job_monitor import ComposeJobMonitor
    from sms_api.compose.models import WrapperStatus

    wrapper_record = MagicMock()
    wrapper_record.wrapper_id = 5
    wrapper_record.status = WrapperStatus.AVAILABLE  # already done

    wrapper_db = AsyncMock()
    wrapper_db.get_wrapper_by_simulator_id = AsyncMock(return_value=wrapper_record)
    wrapper_db.update_wrapper_status = AsyncMock()

    db_mock = MagicMock()
    db_mock.get_wrapper_db = MagicMock(return_value=wrapper_db)

    monitor = ComposeJobMonitor(nats_client=None, database_service=db_mock)
    await monitor._handle_wrapper_build_complete(simulator_id=5)

    wrapper_db.update_wrapper_status.assert_not_awaited()


# ---------------------------------------------------------------------------
# _to_tool_slug / _to_class_name helpers (Phase 3b)
# ---------------------------------------------------------------------------


class TestScaffoldHelpers:
    def test_to_tool_slug_simple(self) -> None:
        assert WrapperGenerationService._to_tool_slug("mem3dg") == "mem3dg"

    def test_to_tool_slug_hyphen(self) -> None:
        assert WrapperGenerationService._to_tool_slug("my-tool") == "my_tool"

    def test_to_tool_slug_multi_hyphen(self) -> None:
        assert WrapperGenerationService._to_tool_slug("my-cool-tool") == "my_cool_tool"

    def test_to_class_name_simple(self) -> None:
        assert WrapperGenerationService._to_class_name("mem3dg") == "Mem3dg"

    def test_to_class_name_hyphen(self) -> None:
        assert WrapperGenerationService._to_class_name("my-tool") == "MyTool"

    def test_to_class_name_multi_hyphen(self) -> None:
        assert WrapperGenerationService._to_class_name("my-cool-tool") == "MyCoolTool"

    def test_render_ports_dict_empty(self) -> None:
        result = WrapperGenerationService._render_ports_dict([])
        assert "TODO" in result

    def test_render_ports_dict_single(self) -> None:
        from sms_api.compose.models import PbgPortSchema

        ports = [PbgPortSchema(name="substrate", schema_expr="float")]
        result = WrapperGenerationService._render_ports_dict(ports)
        assert '"substrate": "float"' in result

    def test_render_ports_dict_multiple(self) -> None:
        from sms_api.compose.models import PbgPortSchema

        ports = [
            PbgPortSchema(name="a", schema_expr="float"),
            PbgPortSchema(name="b", schema_expr="map[string,float]"),
        ]
        result = WrapperGenerationService._render_ports_dict(ports)
        assert '"a": "float"' in result
        assert '"b": "map[string,float]"' in result

    def test_render_config_schema_empty(self) -> None:
        result = WrapperGenerationService._render_config_schema([])
        assert "TODO" in result

    def test_render_config_schema_float_param(self) -> None:
        from sms_api.compose.models import PbgConfigParam

        params = [PbgConfigParam(name="rate", type="float", default=0.1)]
        result = WrapperGenerationService._render_config_schema(params)
        assert '"rate"' in result
        assert '"float"' in result
        assert "0.1" in result


# ---------------------------------------------------------------------------
# _scaffold_wrapper — generated file content (Phase 3b)
# ---------------------------------------------------------------------------


class TestScaffoldWrapper:
    def _make_svc(self) -> WrapperGenerationService:
        return WrapperGenerationService(db=MagicMock(), file_service=None)

    def test_creates_pyproject_toml(self) -> None:
        from sms_api.compose.models import PbgPortSchema

        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="mem3dg",
                source_repo_url="https://github.com/vivarium-collective/mem3dg",
                source_ref="main",
                process_type="Process",
                input_ports=[PbgPortSchema(name="substrate", schema_expr="float")],
                output_ports=[PbgPortSchema(name="product", schema_expr="float")],
                config_params=[],
            )
            pyproject = workspace / "pbg-mem3dg" / "pyproject.toml"
            assert pyproject.exists()
            content = pyproject.read_text()
            assert 'name = "pbg-mem3dg"' in content
            assert "process-bigraph" in content

    def test_creates_processes_py_with_ports(self) -> None:
        from sms_api.compose.models import PbgPortSchema

        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="cobra",
                source_repo_url="https://github.com/org/cobra",
                source_ref="main",
                process_type="Process",
                input_ports=[PbgPortSchema(name="concentrations", schema_expr="map[string,float]")],
                output_ports=[PbgPortSchema(name="fluxes", schema_expr="map[string,float]")],
                config_params=[],
            )
            processes_py = workspace / "pbg-cobra" / "pbg_cobra" / "processes.py"
            assert processes_py.exists()
            content = processes_py.read_text()
            assert "CobraProcess" in content
            assert '"concentrations": "map[string,float]"' in content
            assert '"fluxes": "map[string,float]"' in content

    def test_creates_step_type(self) -> None:
        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="my-tool",
                source_repo_url="https://github.com/org/my-tool",
                source_ref="main",
                process_type="Step",
                input_ports=[],
                output_ports=[],
                config_params=[],
            )
            processes_py = workspace / "pbg-my-tool" / "pbg_my_tool" / "processes.py"
            content = processes_py.read_text()
            assert "MyToolStep(Step)" in content
            assert "from process_bigraph import Step" in content

    def test_creates_init_py_with_exports(self) -> None:
        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="tellurium",
                source_repo_url="https://github.com/org/tellurium",
                source_ref="main",
                process_type="Process",
                input_ports=[],
                output_ports=[],
                config_params=[],
            )
            init_py = workspace / "pbg-tellurium" / "pbg_tellurium" / "__init__.py"
            content = init_py.read_text()
            assert "TelluriumProcess" in content
            assert "__all__" in content

    def test_creates_tests_directory(self) -> None:
        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="mem3dg",
                source_repo_url="https://github.com/org/mem3dg",
                source_ref="main",
                process_type="Process",
                input_ports=[],
                output_ports=[],
                config_params=[],
            )
            test_file = workspace / "pbg-mem3dg" / "tests" / "test_processes.py"
            assert test_file.exists()
            content = test_file.read_text()
            assert "Mem3dgProcess" in content
            assert "def test_mem3dg_instantiation" in content

    def test_creates_readme(self) -> None:
        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="cobra",
                source_repo_url="https://github.com/org/cobra",
                source_ref="v1.0",
                process_type="Process",
                input_ports=[],
                output_ports=[],
                config_params=[],
            )
            readme = workspace / "pbg-cobra" / "README.md"
            assert readme.exists()
            content = readme.read_text(encoding="utf-8")
            assert "pbg-cobra" in content
            assert "v1.0" in content

    def test_config_params_rendered_in_processes_py(self) -> None:
        from sms_api.compose.models import PbgConfigParam

        svc = self._make_svc()
        with tempfile.TemporaryDirectory() as workdir:
            workspace = Path(workdir)
            svc._scaffold_wrapper(
                workspace=workspace,
                tool_name="mem3dg",
                source_repo_url="https://github.com/org/mem3dg",
                source_ref="main",
                process_type="Process",
                input_ports=[],
                output_ports=[],
                config_params=[PbgConfigParam(name="rate", type="float", default=0.5)],
            )
            processes_py = workspace / "pbg-mem3dg" / "pbg_mem3dg" / "processes.py"
            content = processes_py.read_text()
            assert '"rate"' in content
            assert "0.5" in content


# ---------------------------------------------------------------------------
# generate_wrapper — scaffold path selected when no API key (Phase 3b)
# ---------------------------------------------------------------------------


class TestGenerateWrapperScaffoldPath:
    @pytest.mark.asyncio
    async def test_scaffold_path_when_use_agent_false(self) -> None:
        """generate_wrapper uses scaffold when use_agent=False regardless of API key."""
        from sms_api.compose.models import PbgPortSchema

        db_mock = MagicMock()
        wrapper_db = AsyncMock()
        wrapper_db.update_wrapper_status = AsyncMock()
        db_mock.get_wrapper_db = MagicMock(return_value=wrapper_db)

        file_mock = AsyncMock()
        file_mock.upload_file = AsyncMock(return_value=None)

        svc = WrapperGenerationService(db=db_mock, file_service=file_mock, sim_service=None)

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value.compose_pbg_anthropic_api_key = "sk-has-key"
            mock_settings.return_value.compose_pbg_wrappers_storage_prefix = "pbg-wrappers"
            await svc.generate_wrapper(
                wrapper_id=1,
                source_repo_url="https://github.com/org/mem3dg",
                tool_name="mem3dg",
                source_ref="main",
                use_agent=False,
                input_ports=[PbgPortSchema(name="substrate", schema_expr="float")],
                output_ports=[PbgPortSchema(name="product", schema_expr="float")],
                config_params=[],
            )

        # Should have called update_wrapper_status (at least STORING + READY)
        assert wrapper_db.update_wrapper_status.await_count >= 1
        # upload_file should have been called (tarball stored)
        file_mock.upload_file.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_scaffold_path_when_no_api_key(self) -> None:
        """generate_wrapper falls back to scaffold when no API key configured."""
        db_mock = MagicMock()
        wrapper_db = AsyncMock()
        wrapper_db.update_wrapper_status = AsyncMock()
        db_mock.get_wrapper_db = MagicMock(return_value=wrapper_db)

        file_mock = AsyncMock()
        file_mock.upload_file = AsyncMock(return_value=None)

        svc = WrapperGenerationService(db=db_mock, file_service=file_mock, sim_service=None)

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value.compose_pbg_anthropic_api_key = ""  # no key
            mock_settings.return_value.compose_pbg_wrappers_storage_prefix = "pbg-wrappers"
            await svc.generate_wrapper(
                wrapper_id=2,
                source_repo_url="https://github.com/org/cobra",
                tool_name="cobra",
                source_ref="main",
                use_agent=True,  # desired, but no key → falls back
            )

        # Scaffold path ran successfully (STORING + READY transitions)
        assert wrapper_db.update_wrapper_status.await_count >= 1
