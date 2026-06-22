from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_operator_console_surfaces_validation_and_governance():
    sidebar = (ROOT / "frontend/src/components/Sidebar.tsx").read_text()
    validation = (ROOT / "frontend/src/app/validation/page.tsx").read_text()
    governance = (ROOT / "frontend/src/app/governance/page.tsx").read_text()
    routes = (ROOT / "backend/src/routes/governance.routes.ts").read_text()

    assert "/validation" in sidebar
    assert "/governance" in sidebar
    assert "EXTERNAL-VALIDATED" in validation
    assert "why_allowed" in routes
    assert "Action Attestations" in governance
