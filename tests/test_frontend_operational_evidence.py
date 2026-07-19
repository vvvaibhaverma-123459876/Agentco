from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_performance_page_does_not_ship_static_green_metrics():
    source = (ROOT / "frontend" / "src" / "app" / "performance" / "page.tsx").read_text()

    forbidden_claims = [
        "Avg Task Latency', value: '< 30s'",
        "Agent Error Rate', value: '< 1%'",
        "Audit Coverage', value: '100%'",
        "Override Queue SLA', value: '< 4h avg'",
        "Confidence Calibration Error', value: '< 0.1'",
        "Missed Escalation Rate', value: '0%'",
        "Within threshold",
    ]
    for claim in forbidden_claims:
        assert claim not in source

    assert "api.audit.list" in source
    assert "api.audit.verifyIntegrity" in source
    assert "api.validation.reports" in source
    assert "Missing records are shown as unverified" in source


def test_incidents_page_does_not_claim_no_active_incidents_without_backend_evidence():
    source = (ROOT / "frontend" / "src" / "app" / "incidents" / "page.tsx").read_text()

    assert "No active incidents" not in source
    assert "api.audit.list" in source
    assert "not proof that no active incidents exist" in source
    assert "incidentEntries" in source
