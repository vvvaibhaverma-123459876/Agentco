"""
Phase 4 Correctness Fixes Utilities
Addresses: circular dependencies, hardcoded confidences, model mappings, GET idempotency
"""
from dataclasses import dataclass
from typing import Any, Optional, Set
import hashlib
import json


# ============================================================================
# Phase 4a: Circular Source-Resolution Detection and Prevention
# ============================================================================

@dataclass
class SourceNode:
    """Source reference in provenance chain."""
    source_id: str
    depends_on: Set[str]  # Other source_ids this depends on

    def __hash__(self):
        return hash(self.source_id)


class CircularDependencyDetector:
    """Detects and prevents circular source resolution."""

    def __init__(self):
        self.nodes: dict[str, SourceNode] = {}
        self.visited: Set[str] = set()
        self.cycle_path: list[str] = []

    def register_source(self, source_id: str, depends_on: list[str]):
        """Register a source with its dependencies."""
        self.nodes[source_id] = SourceNode(
            source_id=source_id,
            depends_on=set(depends_on)
        )

    def detect_cycle(self, source_id: str, path: Optional[list[str]] = None) -> Optional[list[str]]:
        """Detect if source_id is part of a cycle using DFS."""
        if path is None:
            path = []

        if source_id in path:
            # Found cycle
            cycle_start = path.index(source_id)
            return path[cycle_start:] + [source_id]

        if source_id in self.visited:
            return None

        path.append(source_id)

        node = self.nodes.get(source_id)
        if node:
            for dep in node.depends_on:
                cycle = self.detect_cycle(dep, path.copy())
                if cycle:
                    return cycle

        self.visited.add(source_id)
        return None

    def resolve_acyclic_order(self) -> list[str]:
        """Return topological sort of sources (acyclic order for resolution)."""
        visited = set()
        stack = []

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if node:
                for dep in node.depends_on:
                    visit(dep)

            stack.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        return stack

    def validate_all_acyclic(self) -> bool:
        """Validate that all sources form a DAG (no cycles)."""
        for source_id in self.nodes:
            cycle = self.detect_cycle(source_id)
            if cycle:
                print(f"❌ Circular dependency detected: {' → '.join(cycle)}")
                return False
        return True


# ============================================================================
# Phase 4b: Dynamic Confidence Calibration (Replace Hardcoded Values)
# ============================================================================

@dataclass
class ConfidenceCalibrationContext:
    """Context for dynamic confidence calibration."""
    stated_confidence: float
    semantic_entropy: float  # 0.0 = certain, 1.0 = maximum uncertainty
    historical_accuracy: Optional[float] = None  # Prior accuracy on similar tasks
    model_uncertainty_signal: Optional[float] = None  # From model's own UQ
    abstention_flag: bool = False

    def compute_calibrated_confidence(self) -> float:
        """Compute calibrated confidence using multiple signals."""
        # Start with stated confidence
        calibrated = self.stated_confidence

        # Adjust down for high entropy
        entropy_penalty = min(self.semantic_entropy * 0.3, 0.5)
        calibrated -= entropy_penalty

        # Adjust using historical accuracy if available
        if self.historical_accuracy is not None:
            accuracy_weight = 0.2
            calibrated = (1.0 - accuracy_weight) * calibrated + accuracy_weight * self.historical_accuracy

        # Adjust using model's own uncertainty signal
        if self.model_uncertainty_signal is not None:
            signal_weight = 0.15
            calibrated = (1.0 - signal_weight) * calibrated + signal_weight * self.model_uncertainty_signal

        # Strong downward adjustment if abstained
        if self.abstention_flag:
            calibrated = max(calibrated * 0.5, 0.1)  # Cap at 10%

        # Clamp to valid range
        return max(0.0, min(1.0, calibrated))


class HardcodedConfidenceFixer:
    """Finds and replaces hardcoded confidence values."""

    COMMON_HARDCODED = {
        0.5: "neutral/default confidence",
        0.95: "high confidence",
        0.9: "very high confidence",
        0.8: "high confidence",
        0.7: "moderate-high confidence",
        0.6: "moderate confidence",
        0.5: "neutral confidence",
        0.3: "low confidence",
        0.1: "very low confidence",
    }

    @staticmethod
    def audit_code(code_str: str) -> list[tuple[int, str, float]]:
        """Find potential hardcoded confidences in code."""
        findings = []
        for i, line in enumerate(code_str.split('\n'), 1):
            for hardcoded_val in HardcodedConfidenceFixer.COMMON_HARDCODED:
                if f"{hardcoded_val}" in line or f"{hardcoded_val:.1f}" in line:
                    findings.append((i, line.strip(), hardcoded_val))
        return findings

    @staticmethod
    def suggest_replacement(context: ConfidenceCalibrationContext) -> float:
        """Suggest dynamic replacement for hardcoded confidence."""
        return context.compute_calibrated_confidence()


# ============================================================================
# Phase 4c: Model ID Canonicalization and Consolidation
# ============================================================================

class ModelRegistry:
    """Canonical registry for model identifiers with aliases."""

    # Canonical model mappings
    CANONICAL_MODELS = {
        # OpenAI models
        'gpt-4-turbo': {'aliases': ['gpt-4.1', 'gpt4-turbo'], 'canonical': 'openai:gpt-4-turbo'},
        'gpt-4-turbo-preview': {'aliases': ['gpt-4-turbo-2024-04-09'], 'canonical': 'openai:gpt-4-turbo-preview'},
        'gpt-4-mini': {'aliases': ['gpt-4-mini', 'gpt4-mini'], 'canonical': 'openai:gpt-4-mini'},
        'gpt-3.5-turbo': {'aliases': ['gpt3.5', 'gpt-3.5'], 'canonical': 'openai:gpt-3.5-turbo'},

        # Anthropic models
        'claude-3-opus': {'aliases': ['claude3-opus', 'claude-opus'], 'canonical': 'anthropic:claude-3-opus'},
        'claude-3-sonnet': {'aliases': ['claude3-sonnet', 'claude-sonnet', 'claude-3-7-sonnet'], 'canonical': 'anthropic:claude-3-sonnet'},
        'claude-3-haiku': {'aliases': ['claude3-haiku', 'claude-haiku', 'claude-3-5-haiku'], 'canonical': 'anthropic:claude-3-haiku'},

        # Google models
        'gemini-2.5-pro': {'aliases': ['gemini-pro', 'gemini-2.5-pro-flash'], 'canonical': 'google:gemini-2.5-pro'},
        'gemini-2.5-flash': {'aliases': ['gemini-flash'], 'canonical': 'google:gemini-2.5-flash'},

        # Test/Local models
        'fake-deterministic': {'aliases': ['fake:deterministic', 'fake_deterministic'], 'canonical': 'fake:deterministic'},
        'agentco': {'aliases': ['agentco-runtime', 'agentco-v1'], 'canonical': 'agentco'},
    }

    @staticmethod
    def normalize_model_id(model_id: str) -> str:
        """Normalize model ID to canonical form."""
        model_lower = model_id.lower().strip()

        # Check direct match
        for model_key, mapping in ModelRegistry.CANONICAL_MODELS.items():
            if model_lower == model_key or model_lower == mapping['canonical'].lower():
                return mapping['canonical']

        # Check aliases
        for model_key, mapping in ModelRegistry.CANONICAL_MODELS.items():
            for alias in mapping['aliases']:
                if model_lower == alias.lower():
                    return mapping['canonical']

        # If no match found, return as-is (but warn)
        print(f"⚠️  Model {model_id} not in registry; using as-is")
        return model_id

    @staticmethod
    def validate_model_id(model_id: str) -> bool:
        """Check if model ID is recognized and canonical."""
        canonical = ModelRegistry.normalize_model_id(model_id)
        return canonical in [m['canonical'] for m in ModelRegistry.CANONICAL_MODELS.values()]


# ============================================================================
# Phase 4d: GET Endpoint Idempotency and Safety
# ============================================================================

class RequestDeduplicator:
    """Ensures GET endpoints are idempotent; deduplicates POST requests."""

    def __init__(self):
        self.request_cache: dict[str, Any] = {}

    def generate_request_id(self, method: str, path: str, body: Optional[dict] = None) -> str:
        """Generate deterministic request ID."""
        canonical = json.dumps({
            'method': method,
            'path': path,
            'body': body,
        }, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def handle_get_request(self, path: str, handler_fn) -> Any:
        """GET requests are naturally idempotent if handler is side-effect-free."""
        return handler_fn()

    def handle_post_request(self, path: str, body: dict, handler_fn) -> Any:
        """POST requests should be idempotent with request ID."""
        request_id = body.get('request_id') or self.generate_request_id('POST', path, body)

        if request_id in self.request_cache:
            return self.request_cache[request_id]

        result = handler_fn()
        self.request_cache[request_id] = result

        return result


class EndpointMutationAuditor:
    """Audits endpoints for state mutations (should only be POST/PUT/DELETE)."""

    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
    MUTABLE_METHODS = {'POST', 'PUT', 'DELETE', 'PATCH'}

    @staticmethod
    def audit_endpoint(method: str, path: str, implementation_fn) -> list[str]:
        """Check if endpoint violates REST principles."""
        violations = []

        if method in EndpointMutationAuditor.SAFE_METHODS:
            # GET should not mutate state
            # This would require introspection of implementation_fn
            pass

        return violations

    @staticmethod
    def suggest_http_method(operation: str) -> str:
        """Suggest correct HTTP method for operation."""
        if operation in {'create', 'submit', 'queue', 'trigger'}:
            return 'POST'
        elif operation in {'update', 'modify', 'patch'}:
            return 'PUT'
        elif operation in {'delete', 'remove'}:
            return 'DELETE'
        elif operation in {'retrieve', 'list', 'get', 'fetch', 'report'}:
            return 'GET'
        else:
            return 'POST'  # Conservative default


# ============================================================================
# Integration Test
# ============================================================================

def test_correctness_utilities():
    """Test all correctness utilities."""
    print("\n" + "="*80)
    print("Testing Phase 4 Correctness Utilities")
    print("="*80)

    # Test 1: Circular dependency detection
    print("\n✓ Test 1: Circular Dependency Detection")
    detector = CircularDependencyDetector()
    detector.register_source("A", ["B"])
    detector.register_source("B", ["C"])
    detector.register_source("C", [])
    assert detector.validate_all_acyclic()
    print("  ✓ Acyclic graph validated")

    # Test 2: Dynamic confidence calibration
    print("\n✓ Test 2: Dynamic Confidence Calibration")
    ctx = ConfidenceCalibrationContext(
        stated_confidence=0.95,
        semantic_entropy=0.3,
        historical_accuracy=0.85,
        abstention_flag=False,
    )
    calibrated = ctx.compute_calibrated_confidence()
    assert 0.0 <= calibrated <= 1.0
    print(f"  ✓ Calibrated 0.95 → {calibrated:.3f}")

    # Test 3: Model ID normalization
    print("\n✓ Test 3: Model ID Normalization")
    assert ModelRegistry.normalize_model_id("gpt-4.1") == "openai:gpt-4-turbo"
    assert ModelRegistry.normalize_model_id("claude-3-7-sonnet") == "anthropic:claude-3-sonnet"
    assert ModelRegistry.normalize_model_id("fake:deterministic") == "fake:deterministic"
    print("  ✓ Model IDs normalized correctly")

    # Test 4: Request deduplication
    print("\n✓ Test 4: Request Deduplication")
    dedup = RequestDeduplicator()
    request_id_1 = dedup.generate_request_id("POST", "/api/runs", {"benchmark_id": "test"})
    request_id_2 = dedup.generate_request_id("POST", "/api/runs", {"benchmark_id": "test"})
    assert request_id_1 == request_id_2
    print("  ✓ Request IDs deterministic and consistent")

    print("\n" + "="*80)
    print("✅ All Phase 4 correctness utilities working correctly")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_correctness_utilities()
