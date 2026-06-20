"""
Test Phase 1 documentation for honesty and absence of overclaims.

Validates that learning layer documentation does not make forbidden claims.
"""

import re
from pathlib import Path

# Forbidden claim patterns (these should NOT appear in learning docs)
FORBIDDEN_CLAIMS = [
    # Claim: All ingested knowledge is trusted
    r"all\s+ingested\s+(?:knowledge|content|sources?|claims?)\s+(?:is|are|will be)\s+(?:trusted|verified|true|valid)",

    # Claim: Video lectures are authoritative by default
    r"(?:video\s+)?lectures?\s+(?:are\s+)?(?:authoritative|definitive|final|true)\s+by\s+default",
    r"(?:video\s+)?lectures?\s+(?:are\s+)?(?:automatically\s+)?(?:authoritative|verified|trusted|true)",

    # Claim: Papers are automatically true
    r"papers?\s+(?:are\s+)?(?:automatically\s+)?(?:true|fact|verified|trusted)",
    r"peer[\s-]?reviewed?\s+papers?\s+(?:are\s+)?(?:automatically\s+)?(?:true|fact|verified)",

    # Claim: Agentco can act freely without governance
    r"agentco\s+can\s+(?:act|spend|deploy|publish|promote|decide)\s+(?:freely|autonomously)\s+without\s+governance",
    r"(?:act|spend|deploy|publish|promote|decide)\s+(?:freely|autonomously)\s+without\s+(?:review|governance|approval|oversight)",

    # Claim: LLM summaries are sufficient evidence
    r"llm\s+(?:summaries?|outputs?|generations?)\s+(?:are\s+)?(?:sufficient|adequate)\s+(?:evidence|proof)",

    # Claim: Civilization will solve X (future work presented as shipped)
    r"civilization\s+(?:will|can|shall)\s+(?:solve|handle|manage)\s+(?:all|every|ethical|normative|philosophical)",

    # Claim: System prevents all attacks/failures
    r"(?:system|layer|engine)\s+(?:prevents|stops|eliminates)\s+(?:all|every)\s+(?:attacks?|failures?|errors?)",
    r"(?:impossible|never)\s+(?:to\s+)?(?:attack|fail|escape|bypass|exploit)",
]

# Pattern for "Known Limits" sections
KNOWN_LIMITS_PATTERN = r"#{1,4}\s+Known Limits"

# Files to check
LEARNING_DOCS = [
    "docs/MASTER_LEARNING_RESILIENCE_BASELINE.md",
    "docs/UNIVERSAL_LEARNING_LAYER.md",
    "docs/KNOWLEDGE_CLAIM_MODEL.md",
    "docs/SCIENTIFIC_EVIDENCE_ENGINE.md",
    "docs/AUTONOMOUS_LEARNING_GOVERNANCE.md",
    "docs/CROSS_DOMAIN_SYNTHESIS.md",
]


def check_doc_for_forbidden_claims(doc_path: str) -> tuple[bool, list]:
    """
    Check a document for forbidden claims.

    Returns: (is_clean: bool, violations: list[str])
    """
    path = Path(doc_path)
    if not path.exists():
        return False, [f"File not found: {doc_path}"]

    content = path.read_text()
    violations = []

    for pattern in FORBIDDEN_CLAIMS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            violations.append(f"Line {line_num}: {match.group()}")

    is_clean = len(violations) == 0
    return is_clean, violations


def check_doc_has_known_limits(doc_path: str) -> tuple[bool, str]:
    """
    Check that a document includes a Known Limits section.

    Returns: (has_known_limits: bool, message: str)
    """
    path = Path(doc_path)
    if not path.exists():
        return False, f"File not found: {doc_path}"

    content = path.read_text()
    if re.search(KNOWN_LIMITS_PATTERN, content, re.IGNORECASE):
        return True, f"✓ {path.name} has Known Limits section"
    else:
        return False, f"✗ {path.name} missing Known Limits section"


def test_phase1_docs_no_forbidden_claims():
    """Test that Phase 1 docs don't contain forbidden overclaims."""

    print("\n" + "="*70)
    print("PHASE 1 DOCUMENTATION HONESTY CHECK")
    print("="*70)

    all_clean = True

    for doc_path in LEARNING_DOCS:
        is_clean, violations = check_doc_for_forbidden_claims(doc_path)

        if is_clean:
            print(f"\n✅ {doc_path}: CLEAN")
        else:
            print(f"\n❌ {doc_path}: VIOLATIONS FOUND")
            all_clean = False
            for violation in violations:
                print(f"   {violation}")

    print("\n" + "="*70)
    print("KNOWN LIMITS CHECK")
    print("="*70)

    for doc_path in LEARNING_DOCS:
        has_limits, message = check_doc_has_known_limits(doc_path)
        print(f"\n{message}")
        if not has_limits:
            all_clean = False

    print("\n" + "="*70)
    if all_clean:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ SOME CHECKS FAILED")
    print("="*70 + "\n")

    assert all_clean, "Documentation contains forbidden claims or missing Known Limits"


def test_phase1_docs_all_exist():
    """Test that all Phase 1 doc files exist."""

    print("\nPhase 1 Documentation Files Check:")

    all_exist = True
    for doc_path in LEARNING_DOCS:
        path = Path(doc_path)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✓ {doc_path} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ {doc_path} NOT FOUND")
            all_exist = False

    assert all_exist, "Some Phase 1 documentation files are missing"


def test_knowledge_claim_model_doc_specifications():
    """Test that KNOWLEDGE_CLAIM_MODEL.md includes all required fields."""

    doc_path = "docs/KNOWLEDGE_CLAIM_MODEL.md"
    path = Path(doc_path)

    assert path.exists(), f"{doc_path} not found"

    content = path.read_text()

    # Check for required sections
    required_sections = [
        "claim_id",
        "source_id",
        "claim_text",
        "normalized_claim",
        "claim_type",
        "status",
        "evidence_type",
        "provenance_hash",
        "can_promote_to",
        "Blocked Transitions",
    ]

    for section in required_sections:
        assert section in content, f"Missing {section} in Knowledge Claim Model"

    print(f"\n✓ {doc_path} includes all required fields and methods")


def test_evidence_engine_hierarchy():
    """Test that SCIENTIFIC_EVIDENCE_ENGINE.md defines complete hierarchy."""

    doc_path = "docs/SCIENTIFIC_EVIDENCE_ENGINE.md"
    path = Path(doc_path)

    assert path.exists(), f"{doc_path} not found"

    content = path.read_text()

    # Check for evidence hierarchy
    hierarchy_terms = [
        "Formal Proof",
        "Raw Dataset",
        "Replicated Peer-Reviewed",
        "Meta-Analysis",
        "Textbook",
        "Single Peer-Reviewed",
        "Preprint",
        "Expert Lecture",
        "Blog Article",
        "Forum Claim",
        "LLM Summary",
    ]

    for term in hierarchy_terms:
        assert term in content, f"Missing {term} in evidence hierarchy"

    print(f"\n✓ {doc_path} defines complete evidence hierarchy")


def test_governance_learning_space_defined():
    """Test that AUTONOMOUS_LEARNING_GOVERNANCE defines learning vs consequence space."""

    doc_path = "docs/AUTONOMOUS_LEARNING_GOVERNANCE.md"
    path = Path(doc_path)

    assert path.exists(), f"{doc_path} not found"

    content = path.read_text()

    # Check for key sections
    required_keywords = [
        "Learning Space",
        "Consequence Space",
        "Learning is autonomous",
        "Consequences are governed",
        "Separation of Powers",
        "self-certification",
        "circular",
    ]

    for keyword in required_keywords:
        assert keyword in content, f"Missing '{keyword}' in governance doc"

    print(f"\n✓ {doc_path} properly defines learning vs consequence space")


if __name__ == "__main__":
    # Run all tests
    print("\nRunning Phase 1 Documentation Tests...")

    test_phase1_docs_all_exist()
    test_knowledge_claim_model_doc_specifications()
    test_evidence_engine_hierarchy()
    test_governance_learning_space_defined()
    test_phase1_docs_no_forbidden_claims()

    print("\n✅ All Phase 1 documentation tests passed!")
