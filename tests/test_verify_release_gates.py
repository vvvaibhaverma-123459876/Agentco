from scripts.verify_release_gates import route_reachability


def test_route_reachability_reports_partial_scope():
    report = route_reachability()

    assert report["scope"] == "backend_http_route_clusters"
    assert report["passed"] is True
    assert report["status"] == "partial"
    assert report["missing_from_server"] == []
    assert report["missing_runtime_endpoints"] == []
    assert report["route_registrations"]
    assert all(item["imported"] for item in report["route_registrations"].values())
    assert all(item["registered"] for item in report["route_registrations"].values())
    assert "not prove full L14 coordinator reachability" in report["honesty_note"]
