from agents.autonomy.fetcher import FetcherAgent
from agents.autonomy.researcher import ResearcherAgent


def budget():
    return {"tokens": 10000, "iterations": 10, "seconds": 60}


def test_researcher_web_search_persists_real_results(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(
        agent,
        "real_web_search",
        lambda query: {
            "status": "search_completed",
            "query": query,
            "results": [
                {"url": "https://example.org/a", "title": "A", "snippet": "Real snippet A"},
                {"url": "https://example.org/b", "title": "B", "snippet": "Real snippet B"},
            ],
        },
    )
    persisted = []
    monkeypatch.setattr(
        agent,
        "persist_evidence",
        lambda **kwargs: persisted.append(kwargs) or f"evidence-{len(persisted)}",
    )

    result = agent.handle_action({"actionType": "WEB_SEARCH", "args": {"query": "agent calibration"}})

    assert result["observations"]["status"] == "search_completed"
    assert result["observations"]["resultsFound"] == 2
    assert result["artifacts"] == ["evidence-1", "evidence-2"]
    assert persisted[0]["source_type"] == "web_search"
    assert persisted[0]["url"] == "https://example.org/a"


def test_researcher_web_search_fails_closed_without_fake_artifacts(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(
        agent,
        "real_web_search",
        lambda query: {"status": "failed", "reason": "provider unavailable", "query": query, "results": []},
    )

    result = agent.handle_action({"actionType": "WEB_SEARCH", "args": {"query": "agent calibration"}})

    assert result["observations"]["status"] == "failed"
    assert result["artifacts"] == []
    assert "provider unavailable" in result["errors"][0]


def test_researcher_web_search_fails_closed_when_persistence_fails(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(
        agent,
        "real_web_search",
        lambda query: {
            "status": "search_completed",
            "query": query,
            "results": [{"url": "https://example.org/a", "title": "A", "snippet": "Real snippet A"}],
        },
    )
    monkeypatch.setattr(
        agent,
        "persist_evidence",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )

    result = agent.handle_action({"actionType": "WEB_SEARCH", "args": {"query": "agent calibration"}})

    assert result["observations"]["status"] == "failed"
    assert result["artifacts"] == []
    assert "Evidence persistence failed" in result["errors"][0]


def test_researcher_extracts_from_persisted_evidence_text(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(
        agent,
        "load_evidence_text",
        lambda source_id: {
            "id": source_id,
            "url": "https://example.org/source",
            "title": "Source",
            "snippet": "Snippet",
            "content_text": "First meaningful evidence sentence about calibration. Second meaningful evidence sentence about governance.",
        },
    )
    monkeypatch.setattr(agent, "persist_evidence", lambda **kwargs: "extracted-evidence-1")

    result = agent.handle_action({"actionType": "EXTRACT_EVIDENCE", "args": {"sourceId": "source-1"}})

    assert result["observations"]["status"] == "extraction_completed"
    assert result["observations"]["pointsExtracted"] == 2
    assert result["artifacts"] == ["extracted-evidence-1"]


def test_researcher_extract_evidence_fails_closed_when_source_missing(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(agent, "load_evidence_text", lambda source_id: None)

    result = agent.handle_action({"actionType": "EXTRACT_EVIDENCE", "args": {"sourceId": "missing-source"}})

    assert result["observations"]["status"] == "blocked"
    assert result["artifacts"] == []
    assert "not found" in result["errors"][0]


def test_researcher_generate_claim_persists_supported_claim(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    persisted = {}

    def persist_claim(**kwargs):
        persisted.update(kwargs)
        return "claim-1"

    monkeypatch.setattr(agent, "persist_claim", persist_claim)

    result = agent.handle_action(
        {
            "actionType": "GENERATE_CLAIM",
            "args": {
                "claimText": "Evidence-governed agents need cited claims.",
                "supportSourceIds": ["ev1"],
                "confidence": 0.8,
            },
        }
    )

    assert result["observations"]["status"] == "claim_generated"
    assert result["observations"]["claimId"] == "claim-1"
    assert result["artifacts"] == ["claim-1"]
    assert persisted["support_source_ids"] == ["ev1"]


def test_researcher_generate_claim_fails_closed_when_persistence_fails(monkeypatch):
    agent = ResearcherAgent("researcher-test", "researcher", budget())
    monkeypatch.setattr(
        agent,
        "persist_claim",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )

    result = agent.handle_action(
        {
            "actionType": "GENERATE_CLAIM",
            "args": {"claimText": "A supported claim.", "supportSourceIds": ["ev1"]},
        }
    )

    assert result["observations"]["status"] == "failed"
    assert result["artifacts"] == []
    assert "Claim persistence failed" in result["errors"][0]


def test_fetcher_fetch_page_persists_real_fetch(monkeypatch):
    agent = FetcherAgent("fetcher-test", "fetcher", budget())
    monkeypatch.setattr(
        agent,
        "real_fetch_page",
        lambda url: {
            "status": "fetch_completed",
            "url": url,
            "title": "Fetched page",
            "content": "Fetched real content",
            "content_type": "text/html",
            "content_length": 20,
        },
    )
    monkeypatch.setattr(agent, "persist_evidence", lambda **kwargs: "fetch-evidence-1")

    result = agent.handle_action({"actionType": "FETCH_PAGE", "args": {"url": "https://example.org"}})

    assert result["observations"]["status"] == "fetch_completed"
    assert result["observations"]["artifactId"] == "fetch-evidence-1"
    assert result["artifacts"] == ["fetch-evidence-1"]


def test_fetcher_fetch_page_fails_closed(monkeypatch):
    agent = FetcherAgent("fetcher-test", "fetcher", budget())
    monkeypatch.setattr(
        agent,
        "real_fetch_page",
        lambda url: {"status": "blocked", "reason": "Access to private/internal networks is not allowed", "url": url},
    )

    result = agent.handle_action({"actionType": "FETCH_PAGE", "args": {"url": "http://127.0.0.1"}})

    assert result["observations"]["status"] == "blocked"
    assert result["artifacts"] == []
    assert "private/internal" in result["errors"][0]


def test_persist_claim_rejects_missing_sources_without_stub_id():
    agent = ResearcherAgent("researcher-test", "researcher", budget())

    try:
        agent.persist_claim("Unsupported claim", [])
    except RuntimeError as exc:
        assert "support_source_ids" in str(exc)
    else:
        raise AssertionError("persist_claim returned an ID for an unsupported claim")
