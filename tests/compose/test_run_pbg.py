import json
from pathlib import Path
from typing import Any

import pytest

from sms_api.compose import run_pbg


def test_run_writes_final_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeComposite:
        def __init__(self, doc: Any) -> None:
            self.doc = doc
            self.n = 0

        def run(self, n: int) -> None:
            self.n = n

        def serialize_state(self) -> dict[str, int]:
            return {"ran": self.n}

    # run() does `from process_bigraph import Composite`, so patch it there.
    import process_bigraph

    monkeypatch.setattr(process_bigraph, "Composite", FakeComposite)

    pbg = tmp_path / "m.pbg"
    pbg.write_text(json.dumps({"state": {}, "composition": {}}))
    out = run_pbg.run(str(pbg), steps=5, results_dir=tmp_path / "output")

    assert out.name == "final_state.json"
    assert json.loads(out.read_text())["ran"] == 5
