import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from sms_api.compose import run_pbg


class FakeCore:
    def __init__(self) -> None:
        self.links: dict[str, Any] = {}

    def register_link(self, key: str, link: Any) -> None:
        self.links[key] = link


def test_run_writes_final_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeComposite:
        def __init__(self, doc: Any, core: Any = None) -> None:
            self.doc = doc
            self.core = core
            self.n = 0

        def run(self, n: int) -> None:
            self.n = n

        def serialize_state(self) -> dict[str, int]:
            return {"ran": self.n}

    # run() does `from process_bigraph import Composite, register_types` and
    # `from bigraph_schema import allocate_core`. Inject fake modules so the
    # runner is testable without the (container-only) process-bigraph/pbg-emitters
    # install.
    fake_pbg_mod = types.ModuleType("process_bigraph")
    fake_pbg_mod.Composite = FakeComposite  # type: ignore[attr-defined]
    fake_pbg_mod.register_types = lambda core: core  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "process_bigraph", fake_pbg_mod)

    fake_schema_mod = types.ModuleType("bigraph_schema")
    fake_schema_mod.allocate_core = FakeCore  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bigraph_schema", fake_schema_mod)

    pbg = tmp_path / "m.pbg"
    pbg.write_text(json.dumps({"state": {}, "composition": {}}))
    out = run_pbg.run(str(pbg), steps=5, results_dir=tmp_path / "output")

    assert out.name == "final_state.json"
    assert json.loads(out.read_text())["ran"] == 5
