from pathlib import Path


README = Path(__file__).resolve().parents[1] / "README.md"


def _section(text: str, heading: str) -> str:
    marker = f"# {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    next_start = text.find("\n# ", start + len(marker))
    return text[start:] if next_start == -1 else text[start:next_start]


def test_readme_does_not_claim_shipped_full_civilization() -> None:
    text = README.read_text(encoding="utf-8")
    current = text.split("# Historical / Aspirational Architecture Notes", 1)[0]
    forbidden = [
        "full civilization layer",
        "civilization os already shipped",
        "fully autonomous, AI-operated company",
        "29 AI employees",
    ]
    lowered = current.lower()
    for phrase in forbidden:
        assert phrase.lower() not in lowered


def test_historical_architecture_notes_are_clearly_marked() -> None:
    text = README.read_text(encoding="utf-8")
    historical = _section(text, "Historical / Aspirational Architecture Notes")
    assert historical
    assert "not current shipped-product claims" in historical
    assert "historical or aspirational" in historical.lower()
