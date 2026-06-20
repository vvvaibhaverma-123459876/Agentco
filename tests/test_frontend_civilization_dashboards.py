from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_civilization_dashboard_routes_exist() -> None:
    routes = [
        "frontend/src/app/civilization/page.tsx",
        "frontend/src/app/civilization/institution/page.tsx",
        "frontend/src/app/civilization/reviews/page.tsx",
        "frontend/src/app/civilization/governance/page.tsx",
        "frontend/src/app/civilization/memory/page.tsx",
        "frontend/src/app/civilization/calibration/page.tsx",
    ]

    for route in routes:
        assert (ROOT / route).exists(), f"missing dashboard route: {route}"


def test_dashboard_labels_make_status_explicit() -> None:
    shell = (ROOT / "frontend/src/components/civilization/CivilizationPageShell.tsx").read_text()
    client = (ROOT / "frontend/src/lib/civilization-api.ts").read_text()

    for label in ["Shipped", "Partially Implemented", "Experimental", "Future"]:
        assert label in client

    assert "CapabilityLegend" in shell
    assert "must not be marketed as shipped" in client


def test_frontend_no_longer_markets_autonomous_company() -> None:
    frontend_text = "\n".join(
        path.read_text()
        for path in (ROOT / "frontend/src").rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}
    )

    banned = [
        "the autonomous AI company",
        "All 29 agents across 9 departments",
        "civilization OS already shipped",
    ]
    for phrase in banned:
        assert phrase not in frontend_text
