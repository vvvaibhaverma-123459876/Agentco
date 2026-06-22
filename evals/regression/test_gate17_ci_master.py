from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_runs_declared_master_gate():
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "Refoundation Master Gate" in ci
    assert "make master-gate" in ci
    assert "validation:" in makefile
    assert "master-gate:" in makefile
    assert "smoke" in makefile.split("master-gate:")[1].split("\n")[0]
    assert "validation" in makefile.split("master-gate:")[1].split("\n")[0]
