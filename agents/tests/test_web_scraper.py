"""Unit tests for agents/core/tools/web_scraper.py"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.core.tools.web_scraper import (
    current_date_context,
    discover_sources,
    fetch_page,
    register_prediction,
)


# ---------------------------------------------------------------------------
# Bug 1: Date anchoring
# ---------------------------------------------------------------------------

class TestCurrentDateContext:
    def test_contains_today(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ctx = current_date_context()
        assert today in ctx

    def test_not_empty(self):
        assert len(current_date_context()) > 20

    def test_instructs_to_use_date(self):
        ctx = current_date_context()
        assert "UTC" in ctx or "training" in ctx.lower()


# ---------------------------------------------------------------------------
# Bug 3: HTML content extraction
# ---------------------------------------------------------------------------

class TestFetchPage:
    def _mock_response(self, html: str, status: int = 200):
        resp = MagicMock()
        resp.status_code = status
        resp.text = html
        resp.raise_for_status.return_value = None
        if status >= 400:
            import requests
            resp.raise_for_status.side_effect = requests.HTTPError()
        return resp

    def test_extracts_article_content(self):
        html = """
        <html><body>
          <nav>Menu Nav Link</nav>
          <article>The real article text here.</article>
          <footer>Footer noise</footer>
        </body></html>
        """
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html)
            text = fetch_page("http://example.com")
        assert "real article text" in text
        assert "Menu Nav Link" not in text
        assert "Footer noise" not in text

    def test_extracts_main_when_no_article(self):
        html = """
        <html><body>
          <header>Site Header</header>
          <main>Main content lives here.</main>
        </body></html>
        """
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html)
            text = fetch_page("http://example.com")
        assert "Main content lives here" in text
        assert "Site Header" not in text

    def test_strips_script_and_style(self):
        html = """
        <html><body>
          <script>var x = 1;</script>
          <style>.cls { color: red; }</style>
          <article>Clean article body.</article>
        </body></html>
        """
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html)
            text = fetch_page("http://example.com")
        assert "var x" not in text
        assert ".cls" not in text
        assert "Clean article body" in text

    def test_returns_empty_on_network_error(self):
        import requests as req
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_get.side_effect = req.ConnectionError("refused")
            text = fetch_page("http://no-such-host.invalid/")
        assert text == ""

    def test_role_main_fallback(self):
        html = """
        <html><body>
          <div role="main">Role-main content.</div>
          <aside>Aside noise.</aside>
        </body></html>
        """
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html)
            text = fetch_page("http://example.com")
        assert "Role-main content" in text
        assert "Aside noise" not in text


# ---------------------------------------------------------------------------
# Bug 2: Schema-correct registration
# ---------------------------------------------------------------------------

_VALID_RECORD = {
    "claim": "The sun will rise tomorrow.",
    "probability": 0.9999,
    "confidence_basis": {"model": "gpt-4o-mini"},
    "producing_agent_id": "test_agent",
    "producing_prompt_version": "v1.0",
    "resolution_criterion": "Sunrise observed at lat/lon",
    "resolution_date": "2099-01-01T00:00:00+00:00",
    "ground_truth_source": "https://example.com/sunrise",
    "horizon_class": "short",
    "domain": "science",
}


class TestRegisterPrediction:
    def test_raises_on_missing_field(self):
        record = dict(_VALID_RECORD)
        del record["claim"]
        with pytest.raises(ValueError, match="claim"):
            register_prediction(record)

    def test_raises_without_database_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            register_prediction(_VALID_RECORD)

    def test_raises_on_db_error(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://bad:bad@localhost:9999/nodb")
        with pytest.raises(Exception):
            register_prediction(_VALID_RECORD)

    def test_never_swallows_db_error(self, monkeypatch):
        """DB errors must propagate, not be caught and silently dropped."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://bad:bad@localhost:9999/nodb")
        raised = False
        try:
            register_prediction(_VALID_RECORD)
        except Exception:
            raised = True
        assert raised, "register_prediction must not swallow DB errors"

    def test_serializes_jsonb_confidence_basis(self, monkeypatch):
        """confidence_basis dict must be serialized to JSON string for psycopg2."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        fake_conn.__enter__ = MagicMock(return_value=fake_conn)
        fake_conn.__exit__ = MagicMock(return_value=False)
        fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
        fake_cursor.__exit__ = MagicMock(return_value=False)
        fake_conn.cursor.return_value = fake_cursor

        with patch("agents.core.tools.web_scraper.psycopg2.connect", return_value=fake_conn):
            register_prediction(_VALID_RECORD)

        call_args = fake_cursor.execute.call_args
        params = call_args[0][1]
        assert isinstance(params["confidence_basis"], str)
        assert json.loads(params["confidence_basis"]) == {"model": "gpt-4o-mini"}


# ---------------------------------------------------------------------------
# New capability: discover_sources
# ---------------------------------------------------------------------------

class TestDiscoverSources:
    def _mock_client(self, content: str):
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))]
        )
        return client

    def test_returns_empty_without_client(self):
        assert discover_sources("AI trends") == []

    def test_extracts_urls_from_response(self):
        raw = "https://example.com/a\nhttps://example.org/b\n"
        client = self._mock_client(raw)
        urls = discover_sources("AI trends", llm_client=client)
        assert urls == ["https://example.com/a", "https://example.org/b"]

    def test_respects_max_sources(self):
        raw = "\n".join(f"https://example.com/{i}" for i in range(10))
        client = self._mock_client(raw)
        urls = discover_sources("AI trends", llm_client=client, max_sources=3)
        assert len(urls) == 3

    def test_prompt_includes_date_context(self):
        client = self._mock_client("")
        discover_sources("AI trends", llm_client=client)
        prompt = client.chat.completions.create.call_args[1]["messages"][0]["content"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in prompt

    def test_filters_non_urls(self):
        raw = "Here are some links:\nhttps://good.com/page\nnot a url\nhttps://also.good/x"
        client = self._mock_client(raw)
        urls = discover_sources("topic", llm_client=client)
        assert len(urls) == 2
        assert all(u.startswith("https://") for u in urls)

    def test_returns_empty_on_llm_error(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API error")
        assert discover_sources("topic", llm_client=client) == []
