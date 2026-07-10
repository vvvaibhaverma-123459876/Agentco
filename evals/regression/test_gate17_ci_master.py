from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_runs_declared_release_gate():
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "Release Credibility Gate" in ci
    assert "make release-gate" in ci
    assert "release-gate:" in makefile
    release_gate = makefile.split("release-gate:")[1].split("docker-production-smoke:")[0]
    assert "status-check" in release_gate
    assert "$(PYTHON) -m pytest -q" in release_gate
    assert "npm test -- --runInBand" in release_gate
    assert "route-auth-contract.test.ts" in release_gate
    assert "audit-chain-cross-writer.test.ts" in release_gate
    assert "git status --porcelain" in release_gate
