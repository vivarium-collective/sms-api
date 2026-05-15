"""Audit a pbg-* repo for compliance with the bigraph-schema discovery convention.

Mirrored from pbg_superpowers.package_audit (not installable as pip dep).
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib  # Python >= 3.11
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    status: str  # PASS, WARN, FAIL
    detail: str = ""


@dataclass
class AuditReport:
    target: str
    checks: list[CheckResult] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "", fix: str = "") -> None:
        self.checks.append(CheckResult(name, status, detail))
        if fix:
            self.fixes.append(fix)


def _has_dep(deps: list[str], pkg: str) -> bool:
    pat = re.compile(r"^\s*" + re.escape(pkg) + r"(\s*[<>=!~]|\s*\[|\s*$)")
    return any(pat.match(d) for d in deps)


def _check_pypi(name: str) -> tuple[str, str]:
    import json as _json
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=5) as resp:
            data = _json.loads(resp.read().decode())
        version = data.get("info", {}).get("version", "?")
        return "PASS", f"published on PyPI as {name} (latest: {version})"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "WARN", "NOT published on PyPI — recommend publishing"
        return "WARN", f"PyPI check failed: HTTP {e.code}"
    except Exception as e:
        return "WARN", f"PyPI check failed: {e}"


def audit_repo(repo_path: Path, run_install: bool = True) -> AuditReport:  # noqa: C901
    report = AuditReport(target=str(repo_path))

    pyproject_path = repo_path / "pyproject.toml"
    if not pyproject_path.exists():
        report.add("pyproject.toml", "FAIL", "missing", fix="Add a pyproject.toml with [project] table.")
        return report
    try:
        pyproject = tomllib.loads(pyproject_path.read_text())
    except Exception as e:
        report.add("pyproject.toml", "FAIL", f"parse error: {e}")
        return report

    project = pyproject.get("project") or {}
    deps = project.get("dependencies") or []

    if not project:
        report.add("[project] table", "FAIL", "missing", fix="Add [project] table with name, version, dependencies.")
        return report

    report.add("pyproject.toml", "PASS")

    if _has_dep(deps, "bigraph-schema"):
        report.add("bigraph-schema dep", "PASS")
    else:
        report.add(
            "bigraph-schema dep",
            "FAIL",
            "not declared — package will not be picked up by allocate_core() auto-discovery",
            fix='Add "bigraph-schema>=0.0.60" to [project].dependencies',
        )

    if _has_dep(deps, "process-bigraph") or _has_dep(deps, "process_bigraph"):
        report.add("process-bigraph dep", "PASS")
    else:
        report.add(
            "process-bigraph dep",
            "WARN",
            "not declared — needed if you use Process/Step base classes",
            fix='Add "process-bigraph>=0.0.66" to [project].dependencies',
        )

    rp = project.get("requires-python")
    if rp:
        report.add("requires-python", "PASS", f"declared: {rp}")
    else:
        report.add(
            "requires-python",
            "WARN",
            "not declared",
            fix='Add `requires-python = ">=3.10"` to [project]',
        )

    project_name = project.get("name")
    if project_name:
        status, detail = _check_pypi(project_name)
        report.add("published on PyPI", status, detail)

    package_dirs = []
    for child in repo_path.iterdir():
        if child.is_dir() and not child.name.startswith(".") and not child.name.startswith("_"):
            init = child / "__init__.py"
            if init.exists():
                package_dirs.append(child)
    found_subclasses = []
    for pkg_dir in package_dirs:
        for py in pkg_dir.rglob("*.py"):
            try:
                text = py.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for cls_m in re.finditer(r"class\s+(\w+)\s*\(\s*(?:[\w.]+\.)?(Process|Step)\s*\)", text):
                found_subclasses.append(f"{cls_m.group(1)} ({cls_m.group(2)})")
    if found_subclasses:
        report.add(
            "Process/Step subclasses",
            "PASS",
            f"found {len(found_subclasses)}: {', '.join(found_subclasses[:5])}",
        )
    else:
        report.add(
            "Process/Step subclasses",
            "WARN",
            "no class inheriting from process_bigraph.Process or Step found",
        )

    if run_install:
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "venv"
            r = subprocess.run(  # noqa: S603
                ["uv", "venv", str(venv), "--python", sys.executable],  # noqa: S607
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                report.add("pip install -e .", "WARN", "could not create ephemeral venv; skipped")
            else:
                try:
                    r = subprocess.run(  # noqa: S603
                        ["uv", "pip", "install", "--python", str(venv / "bin" / "python"), "-e", str(repo_path)],  # noqa: S607
                        capture_output=True, text=True, timeout=180,
                    )
                except subprocess.TimeoutExpired:
                    report.add("pip install -e .", "FAIL", "install timed out after 180s")
                else:
                    if r.returncode == 0:
                        report.add("pip install -e .", "PASS")
                    else:
                        excerpt = (r.stderr or r.stdout).strip()[-500:]
                        report.add("pip install -e .", "FAIL", f"install failed; tail: {excerpt}")

    return report


def render_report(report: AuditReport) -> str:
    lines = [f"=== Audit: {report.target} ===", ""]
    counts: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for c in report.checks:
        counts[c.status] = counts.get(c.status, 0) + 1
        detail = f"  — {c.detail}" if c.detail else ""
        lines.append(f"{c.name:35s} {c.status:5s}{detail}")
    lines.append("")
    lines.append("=== Summary ===")
    lines.append(f"PASS: {counts['PASS']}, WARN: {counts['WARN']}, FAIL: {counts['FAIL']}")
    if report.fixes:
        lines.append("")
        lines.append("Recommended fixes:")
        for fix in report.fixes:
            lines.append(f"  - {fix}")
    return "\n".join(lines)


def clone_repo(url: str, ref: str | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="pbg-audit-"))
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(tmp / "repo")])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)  # noqa: S603
    # these subprocess calls are fine — audit tool, not prod path
    if r.returncode != 0:
        raise RuntimeError(f"git clone failed: {r.stderr}")
    return tmp / "repo"
