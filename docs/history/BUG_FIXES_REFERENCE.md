# Bug Fixes Reference — Quick Lookup

## Bug 1: Date Anchoring Failure (LLM Training Data Date Confusion)

**What was broken:**
- Local LLMs generated queries about "December 2021" when actual date was June 2026
- Silent date drift → predictions searched against already-past events
- Example: "When will the 2021 election happen?" (already happened)

**Fix location:** `agents/core/tools/web_scraper.py:40-61`
```python
def current_date_context() -> str:
    """Explicit instruction block with real system date."""
    # Returns: "[SYSTEM DATE CONTEXT]\nThe real current date is: 2026-06-19 ..."
```

**How it's used:**
- Prepended to `find_resolvable_claims()` prompt → Line 199
- Prepended to `discover_sources()` prompt → Line 259

**Test proof:** `tests/integration/test_web_scraper_hardened.py::TestBugFix1DateAwareness::test_current_date_context_with_mocked_clock`
```python
# Mock clock to 2030-12-25
# Assert context contains "2030-12-25" and "Wednesday, December 25, 2030"
```

**To verify it works:**
```bash
pytest tests/integration/test_web_scraper_hardened.py::TestBugFix1DateAwareness -v
# All 3 tests must pass
```

---

## Bug 2: Schema Mismatch in Prediction Registration (Silent Failures)

**What was broken:**
- Used `agent_id` instead of `producing_agent_id`
- Omitted required columns: `confidence_basis`, `resolution_criterion`, `producing_prompt_version`
- Bare `except:` silently swallowed errors → ZERO registrations, but loop reported success
- No visibility into which predictions actually registered

**Fix location:** `agents/core/tools/web_scraper.py:325-380`
```python
_PREDICTION_LEDGER_SCHEMA = {
    "prediction_id": "UUID, PRIMARY KEY",
    "claim": "TEXT, NOT NULL",
    # ... all required columns documented
}

def _validate_prediction_ledger_columns(required_cols: list[str]) -> None:
    """Fail-fast: ensure all required columns present."""
    # Raises ValueError if any column missing

def register_prediction_safe(...) -> bool:
    """Insert with schema validation. Raises on any error (never silent)."""
```

**Test proof:** `tests/integration/test_web_scraper_hardened.py::TestBugFix2SchemaValidation`
```python
# test_schema_validation_detects_missing_columns: validates error on missing cols
# test_register_prediction_safe_insert_success: verifies insert works when correct
# test_register_prediction_safe_fails_without_swallowing: verifies errors raise (not silent)
```

**To verify it works:**
```bash
pytest tests/integration/test_web_scraper_hardened.py::TestBugFix2SchemaValidation -v
# All 3 tests must pass
```

**Integration:** `scripts/autonomous_prediction_loop.py` could migrate from `ledger.pre_register()` to `register_prediction_safe()` for schema enforcement (currently using existing ledger API).

---

## Bug 3: Regex-Based HTML Extraction Grabbing Nav/Footer Instead of Content

**What was broken:**
- Extracted "Home About Contact | Related Articles" instead of actual article text
- Pages marked "too short" even with substantial real content
- Example: Real article (~500 words) extracted as nav bar (~50 words) → skipped

**Fix location:** `agents/core/tools/web_scraper.py:96-140`
```python
def _extract_article_content(soup: BeautifulSoup) -> str:
    """Semantic content extraction with fallback chain."""
    # Chain: <article> → <main> → [role=main] → .article/.content/.story/.post → <body>
    # Junk stripping: script, style, nav, footer, header, aside, form, button, iframe, noscript
```

**Used by:** `fetch_page()` → Line 212 (replaces old regex approach)

**Test proof:** `tests/integration/test_web_scraper_hardened.py::TestBugFix3ContentExtraction`
```python
# 5 sub-tests proving:
# 1. Prefers <article> when present
# 2. Falls back to <main>
# 3. Falls back to [role=main]
# 4. Falls back to content-class patterns
# 5. Realistic fixture: nav/footer/ads stripped, article content extracted
```

**To verify it works:**
```bash
pytest tests/integration/test_web_scraper_hardened.py::TestBugFix3ContentExtraction -v
# All 5 tests must pass
```

**Real-world example from test:**
```python
# Input HTML:
# <article>
#   <nav>Home About Contact</nav>
#   <h1>Real Article</h1>
#   <p>Actual content here.</p>
#   <footer>Related articles</footer>
# </article>

# Output: "Real Article Actual content here." (nav/footer excluded)
```

---

## New Capability: LLM-Proposed Source Discovery

**What it does:**
- Queries LLM for 3-5 domain-specific sources relevant to topic
- Returns real URLs: official data sources, trade publications, specialized providers
- Date-aware (includes real system date context)
- Validates URLs are well-formed before use
- Runs BEFORE generic search (supplementary, not replacement)

**Location:** `agents/core/tools/web_scraper.py:226-287`
```python
def discover_sources(topic: str, existing_claims: list[str] | None = None, ...) -> list[dict]:
    """
    Discover domain-specific sources via LLM.
    Returns list of {url, source_name, reason}
    """
```

**Integration:** `scripts/autonomous_prediction_loop.py:121-142`
```python
# Source discovery phase:
# 1. Call discover_sources("technology news")
# 2. Validate URLs
# 3. Prepend discovered URLs to hardcoded SOURCES list
# 4. Fallback to SOURCES if discovery fails (non-blocking)
```

**Test proof:** `tests/integration/test_web_scraper_hardened.py::TestNewCapabilitySourceDiscovery`
```python
# 4 sub-tests proving:
# 1. Returns valid URLs
# 2. Skips invalid URLs (no http/https)
# 3. Prepends date context
# 4. Includes existing claims context
```

**To verify it works:**
```bash
pytest tests/integration/test_web_scraper_hardened.py::TestNewCapabilitySourceDiscovery -v
# All 4 tests must pass
```

---

## Full Test Suite

**Command:**
```bash
python -m pytest tests/integration/test_web_scraper_hardened.py -v
```

**Expected result:**
```
15 passed in 0.48s
```

**Breakdown:**
- Bug 1: 3 tests
- Bug 2: 3 tests
- Bug 3: 5 tests
- New capability: 4 tests

---

## How to Know If A Bug Recurs

### Bug 1 Recurrence Detector
- LLM generates queries with dates in training era (pre-2023)
- Solution date differs from actual system date
- **Guard:** Test will fail if date context not included

### Bug 2 Recurrence Detector
- Predictions "register" but don't appear in DB
- Bare `except:` swallows OperationalError or IntegrityError
- **Guard:** Any insert error will raise immediately (never silent)

### Bug 3 Recurrence Detector
- Extracted text is mostly nav/footer/boilerplate
- Real pages skipped as "too short" despite having content
- **Guard:** Test will fail if nav/footer text appears in extracted content

---

## Running the Full Suite

```bash
# From repo root:
cd /Users/Zet/Agentco

# Run all hardened tests:
python -m pytest tests/integration/test_web_scraper_hardened.py -v

# Run only one bug's tests:
python -m pytest tests/integration/test_web_scraper_hardened.py::TestBugFix1DateAwareness -v
python -m pytest tests/integration/test_web_scraper_hardened.py::TestBugFix2SchemaValidation -v
python -m pytest tests/integration/test_web_scraper_hardened.py::TestBugFix3ContentExtraction -v
python -m pytest tests/integration/test_web_scraper_hardened.py::TestNewCapabilitySourceDiscovery -v
```

---

## Files Modified

| File | Changes |
|------|---------|
| `agents/core/tools/web_scraper.py` | +200 lines: 4 new functions, 2 modified functions, schema constant |
| `scripts/autonomous_prediction_loop.py` | +30 lines: source discovery phase, date context in prompts |
| `tests/integration/test_web_scraper_hardened.py` | NEW: 400 lines, 15 comprehensive tests |
| `HARDENING_REPORT.md` | NEW: detailed documentation of all fixes |

---

## Limitations (Honest Assessment)

Sites that may still fail:
- **Paywalls** (Financial Times, Wall Street Journal) — requires login
- **Bot detection** — some sites block requests outright
- **JavaScript-rendered content** — BeautifulSoup can't execute JS
- **Consent banners** — may extract banner instead of article

These are intrinsic limitations of static HTML scraping, not regressions from the bug fixes.
