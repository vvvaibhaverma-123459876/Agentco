from scripts import verify_production_posture as posture


def test_secret_check_blocks_missing_without_value(monkeypatch):
    for name in posture.REQUIRED_SECRET_VARS:
        monkeypatch.delenv(name, raising=False)

    result = posture.main()
    report = posture.REPORT_PATH.read_text()

    assert result == 2
    assert "missing required production secret" in report
    assert "AGENTCO_API_KEY" in report


def test_secret_check_blocks_dev_defaults(monkeypatch):
    for name in posture.REQUIRED_SECRET_VARS:
        monkeypatch.setenv(name, "real-value-for-test")
    monkeypatch.setenv("AGENTCO_API_KEY", "dev-api-key")

    result = posture.main()
    report = posture.REPORT_PATH.read_text()

    assert result == 2
    assert "dev/default value is not allowed" in report
    assert "real-value-for-test" not in report
