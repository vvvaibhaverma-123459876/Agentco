"""
Integration tests for hardened web scraper — testing all FIVE bug fixes.

TESTS:
  1. BUG 1 FIX: current_date_context() with mocked clock (ensure real date is used, not stale training date)
  2. BUG 2 FIX: Schema validation in register_prediction_safe (fail-loud on mismatches)
  3. BUG 3 FIX: Substance-based duplicate detection with numeric signatures
  4. BUG 4 FIX: BeautifulSoup content extraction + JS-shell detection
  5. BUG 5 FIX: Source reliability tracking (exclude after N failures)
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.core.tools.web_scraper import (
    current_date_context,
    find_resolvable_claims,
    fetch_page,
    discover_sources,
    register_prediction_safe,
    _extract_article_content,
    is_duplicate_claim,
    _is_js_shell_page,
    SourceReliabilityTracker,
)
from bs4 import BeautifulSoup


class TestBugFix1DateAwareness:
    """TEST BUG 1 FIX: Date anchoring failure — LLM must use real system date."""

    def test_current_date_context_contains_real_date(self):
        """current_date_context() returns the real system date, not a stale training date."""
        context = current_date_context()

        now = datetime.now(timezone.utc)
        today_iso = now.strftime("%Y-%m-%d")
        today_long = now.strftime("%A, %B %d, %Y")

        assert today_iso in context, f"Expected {today_iso} in context"
        assert today_long in context, f"Expected {today_long} in context"
        assert "Do NOT use your training data's sense of current date" in context

    def test_current_date_context_with_mocked_clock(self):
        """
        PROOF OF BUG 1 FIX: Mock system clock to far-future date,
        verify current_date_context() returns that date (not stale training date).
        """
        future_date = datetime(2030, 12, 25, 15, 30, 0, tzinfo=timezone.utc)

        with patch("agents.core.tools.web_scraper.datetime") as mock_dt:
            mock_dt.now.return_value = future_date
            mock_dt.timezone = timezone

            context = current_date_context()

            assert "2030-12-25" in context
            assert "Wednesday, December 25, 2030" in context

    def test_find_resolvable_claims_prepends_date_context(self):
        """Verify find_resolvable_claims uses current_date_context in its prompt."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "claims": [
                {
                    "claim": "Test claim",
                    "confidence": 0.85,
                    "resolution_url": "https://example.com",
                    "resolution_date": "2026-06-19",
                    "domain": "technology"
                }
            ]
        })))]
        mock_client.chat.completions.create.return_value = mock_response

        find_resolvable_claims("Test text", "https://example.com", llm_client=mock_client)

        called_prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "[SYSTEM DATE CONTEXT]" in called_prompt
        assert "Do NOT use your training data" in called_prompt


class TestBugFix2SchemaValidation:
    """TEST BUG 2 FIX: Schema mismatch in prediction registration — fail loud, validate schema."""

    def test_schema_validation_detects_missing_columns(self):
        """register_prediction_safe validates schema and raises on missing columns."""
        mock_db = Mock()

        with pytest.raises(ValueError, match="Missing required columns"):
            from agents.core.tools.web_scraper import _validate_prediction_ledger_columns
            _validate_prediction_ledger_columns(["nonexistent_column", "prediction_id"])

    def test_register_prediction_safe_insert_success(self):
        """Successful insert with correct schema returns True and doesn't swallow errors."""
        mock_db = Mock()
        mock_cursor = MagicMock()
        mock_db.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)
        mock_db.commit = Mock()

        result = register_prediction_safe(
            db=mock_db,
            prediction_id="test-id-123",
            claim="Test claim",
            probability=0.75,
            confidence_basis={"source": "test"},
            producing_agent_id="test-agent",
            producing_prompt_version="v1",
            resolution_criterion="Check if true",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=5),
            ground_truth_source="https://example.com",
            horizon_class="short",
            domain="technology",
            claim_type="news_fact",
        )

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_register_prediction_safe_fails_without_swallowing(self):
        """
        PROOF OF BUG 2 FIX: Failed insert raises (never silently swallowed).
        Unlike the old code with bare except: pass, errors now propagate.
        """
        mock_db = Mock()
        mock_cursor = MagicMock()
        mock_db.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)
        mock_cursor.execute.side_effect = Exception("CONSTRAINT VIOLATION: required column missing")

        with pytest.raises(Exception, match="CONSTRAINT VIOLATION"):
            register_prediction_safe(
                db=mock_db,
                prediction_id="test-id",
                claim="Test",
                probability=0.75,
                confidence_basis={},
                producing_agent_id="agent",
                producing_prompt_version="v1",
                resolution_criterion="Check",
                resolution_date=datetime.now(timezone.utc) + timedelta(days=1),
                ground_truth_source="https://example.com",
                horizon_class="short",
                domain="tech",
                claim_type="news_fact",
            )


class TestBugFix3ContentExtraction:
    """TEST BUG 3 FIX: Regex HTML extraction missing real content — use BeautifulSoup targeting."""

    def test_extract_article_content_prefers_article_tag(self):
        """_extract_article_content uses article tag when present."""
        html = """
        <html>
            <nav>Navigation text here</nav>
            <article>
                <h1>Real Article Title</h1>
                <p>This is the real article content that matters.</p>
            </article>
            <footer>Footer text</footer>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_article_content(soup)

        assert "Real Article Title" in content
        assert "real article content" in content
        assert "Navigation text" not in content
        assert "Footer text" not in content

    def test_extract_article_content_fallback_to_main(self):
        """_extract_article_content falls back to main tag when article is absent."""
        html = """
        <html>
            <nav>Nav</nav>
            <main>
                <p>Main content here is substantial and important.</p>
            </main>
            <footer>Footer</footer>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_article_content(soup)

        assert "Main content" in content
        assert "Nav" not in content
        assert "Footer" not in content

    def test_extract_article_content_fallback_to_role_main(self):
        """_extract_article_content falls back to [role=main] when article/main absent."""
        html = """
        <html>
            <div role="main">
                <article>Content with role main.</article>
            </div>
            <aside>Sidebar</aside>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_article_content(soup)

        assert "Content with role main" in content
        assert "Sidebar" not in content

    def test_extract_article_content_fallback_to_content_class(self):
        """_extract_article_content falls back to content-class patterns."""
        html = """
        <html>
            <header>Header</header>
            <div class="article-content">
                <p>This is article content via class.</p>
            </div>
            <footer>Footer</footer>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_article_content(soup)

        assert "article content via class" in content
        assert "Header" not in content
        assert "Footer" not in content

    def test_extract_article_strips_junk_tags(self):
        """
        PROOF OF BUG 3 FIX: Realistic fixture with nav, footer, ads in article wrapper.
        Verify junk tags are stripped before extraction.
        """
        html = """
        <html>
            <article>
                <nav>
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                </nav>
                <h1>Real Article</h1>
                <p>The actual substantive content you need.</p>
                <script>analytics_code();</script>
                <aside>Ad: Buy this!</aside>
                <footer>Related articles: click here</footer>
            </article>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_article_content(soup)

        assert "Real Article" in content
        assert "actual substantive content" in content
        assert "Home" not in content  # nav text stripped
        assert "About" not in content  # nav text stripped
        assert "analytics_code" not in content  # script stripped
        assert "Ad:" not in content  # aside stripped
        assert "Related articles" not in content  # footer stripped


class TestNewCapabilitySourceDiscovery:
    """TEST NEW CAPABILITY: discover_sources() returns model-proposed, validated sources."""

    def test_discover_sources_returns_valid_urls(self):
        """discover_sources returns a list of valid URL dicts."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "sources": [
                {
                    "url": "https://finance.official.gov",
                    "source_name": "Official Finance Bureau",
                    "reason": "Authoritative government data source"
                },
                {
                    "url": "https://industry-journal.org",
                    "source_name": "Industry Publication",
                    "reason": "Trade journal with expert coverage"
                }
            ]
        })))]
        mock_client.chat.completions.create.return_value = mock_response

        sources = discover_sources("financial markets", llm_client=mock_client)

        assert len(sources) == 2
        assert sources[0]["url"] == "https://finance.official.gov"
        assert sources[0]["source_name"] == "Official Finance Bureau"
        assert sources[1]["url"] == "https://industry-journal.org"

    def test_discover_sources_validates_urls(self):
        """discover_sources skips invalid URLs (missing http prefix)."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "sources": [
                {
                    "url": "https://valid.example.com",
                    "source_name": "Valid",
                    "reason": "Real source"
                },
                {
                    "url": "not-a-url",
                    "source_name": "Invalid",
                    "reason": "Missing protocol"
                }
            ]
        })))]
        mock_client.chat.completions.create.return_value = mock_response

        sources = discover_sources("topic", llm_client=mock_client)

        assert len(sources) == 1
        assert sources[0]["url"] == "https://valid.example.com"

    def test_discover_sources_includes_date_context(self):
        """discover_sources prepends current_date_context to its prompt."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({"sources": []})))]
        mock_client.chat.completions.create.return_value = mock_response

        discover_sources("topic", llm_client=mock_client)

        called_prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "[SYSTEM DATE CONTEXT]" in called_prompt

    def test_discover_sources_with_existing_claims(self):
        """discover_sources includes existing claims context to avoid duplication."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({"sources": []})))]
        mock_client.chat.completions.create.return_value = mock_response

        existing = ["claim 1", "claim 2"]
        discover_sources("topic", existing_claims=existing, llm_client=mock_client)

        called_prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "claim 1" in called_prompt
        assert "claim 2" in called_prompt


class TestBugFix3SubstanceDuplicateDetection:
    """TEST BUG 3 FIX: Duplicate detection by numeric signature, not just word overlap."""

    def test_different_numeric_values_not_duplicate(self):
        """
        PROOF OF BUG 3 FIX: "S&P 500 above 7,500" vs "above 7,600" are NOT duplicates
        despite sharing most words. Bug would flag as duplicate (false positive).
        """
        claim1 = "S&P 500 will close above 7,500 by end of June"
        claim2 = "S&P 500 will close above 7,600 by end of June"

        is_dup = is_duplicate_claim(claim1, claim2)
        assert is_dup is False, "Different price targets should NOT be duplicates"

    def test_same_numeric_and_words_is_duplicate(self):
        """Same numeric value and similar wording → duplicate."""
        claim1 = "S&P 500 will close above 7,500 by end of June"
        claim2 = "S&P 500 will close above 7,500 by June end"

        is_dup = is_duplicate_claim(claim1, claim2)
        assert is_dup is True, "Same price target should be duplicate"

    def test_no_numbers_high_word_overlap_is_duplicate(self):
        """Claims without numbers use high word-overlap threshold."""
        claim1 = "Federal Reserve will raise interest rates next month"
        claim2 = "Federal Reserve will raise interest rates next month"

        is_dup = is_duplicate_claim(claim1, claim2)
        assert is_dup is True

    def test_no_numbers_low_word_overlap_not_duplicate(self):
        """Claims without numbers but low overlap are not duplicates."""
        claim1 = "Federal Reserve will raise interest rates"
        claim2 = "European Central Bank will lower inflation target"

        is_dup = is_duplicate_claim(claim1, claim2)
        assert is_dup is False

    def test_percentage_values_compared(self):
        """Numeric signatures include percentages."""
        claim1 = "Unemployment will fall to 3.8%"
        claim2 = "Unemployment will fall to 4.2%"

        is_dup = is_duplicate_claim(claim1, claim2)
        assert is_dup is False, "Different percentages should not be duplicates"


class TestBugFix4JSShellDetectionAndContent:
    """TEST BUG 4 FIX: Detect JS-shell pages + extract real content."""

    def test_detects_oops_error_page(self):
        """JS-shell pages with 'oops something went wrong' are detected."""
        js_shell_text = """
        <nav>Home About Contact</nav>
        <div>Oops, something went wrong. Please try again later.</div>
        <footer>© 2024 Example.com</footer>
        """
        assert _is_js_shell_page(js_shell_text, "https://example.com") is True

    def test_detects_skip_to_nav_pattern(self):
        """Pages with multiple 'skip to' nav links detected as JS shells."""
        js_shell_text = """
        <a href="#content">Skip to main content</a>
        <nav>Menu items...</nav>
        <a href="#footer">Skip to footer</a>
        """
        assert _is_js_shell_page(js_shell_text, "https://example.com") is True

    def test_detects_short_nav_heavy_page(self):
        """Short pages heavily weighted toward nav keywords detected as shells."""
        js_shell_text = "Home About Contact Sign In"
        assert _is_js_shell_page(js_shell_text, "https://example.com") is True

    def test_real_article_not_detected_as_shell(self):
        """Real article content is not false-positively detected as JS shell."""
        real_article = """
        <article>
            <h1>Breaking News: Markets React to Economic Report</h1>
            <p>Federal Reserve officials announced today that interest rates will remain unchanged.</p>
            <p>The decision surprised some analysts who expected a rate cut.</p>
        </article>
        <footer>© 2024 News Site</footer>
        """
        assert _is_js_shell_page(real_article, "https://news.example.com") is False

    def test_fetch_page_detects_js_shell(self):
        """fetch_page() treats JS-shell as failed fetch (returns error key)."""
        with patch("agents.core.tools.web_scraper.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.content = b"""<nav>Skip to content</nav><div>Oops, something went wrong</div>"""
            mock_get.return_value = mock_response

            result = fetch_page("https://example.com/shell")

            assert "error" in result
            assert result["error"] == "js_shell_no_content"


class TestBugFix5SourceReliabilityTracking:
    """TEST BUG 5 FIX: Track source failures and exclude after N consecutive failures."""

    def test_tracker_records_success(self):
        """Tracker resets failure count on success."""
        tracker = SourceReliabilityTracker(failure_threshold=3)
        url = "https://problematic.source.com"

        tracker.record_failure(url)
        tracker.record_failure(url)
        assert not tracker.is_excluded(url)

        tracker.record_success(url)
        assert tracker.failure_counts[url] == 0

    def test_tracker_excludes_after_threshold(self):
        """
        PROOF OF BUG 5 FIX: Source excluded after 3 consecutive failures.
        Without this fix, the source would be retried infinitely.
        """
        tracker = SourceReliabilityTracker(failure_threshold=3)
        url = "https://marketwatch.blocked.com"

        assert not tracker.is_excluded(url)
        tracker.record_failure(url)
        assert not tracker.is_excluded(url)
        tracker.record_failure(url)
        assert not tracker.is_excluded(url)
        tracker.record_failure(url)
        assert tracker.is_excluded(url), "Should be excluded after 3rd failure"

    def test_tracker_separate_sources(self):
        """Tracker maintains separate counts for different sources."""
        tracker = SourceReliabilityTracker(failure_threshold=2)
        url1 = "https://source1.com"
        url2 = "https://source2.com"

        tracker.record_failure(url1)
        tracker.record_failure(url1)
        assert tracker.is_excluded(url1)

        tracker.record_failure(url2)
        assert not tracker.is_excluded(url2)

    def test_tracker_get_excluded_sources(self):
        """Tracker returns list of excluded sources."""
        tracker = SourceReliabilityTracker(failure_threshold=1)
        tracker.record_failure("https://bad1.com")
        tracker.record_failure("https://bad2.com")

        excluded = tracker.get_excluded_sources()
        assert len(excluded) == 2
        assert "https://bad1.com" in excluded
        assert "https://bad2.com" in excluded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
