import pytest

from memory_kernel import MemoryKernel


def test_memory_requires_provenance_and_separates_operational_memory():
    kernel = MemoryKernel()
    with pytest.raises(ValueError):
        kernel.write_experience("agent-a", "episodic", {"lesson": "x"}, "")

    event = kernel.write_experience("agent-a", "prediction_lesson", {"lesson": "check source"}, "attestation:1")
    op = kernel.upsert_operational("routing.preference", {"agent": "agent-a"})

    assert event.content_hash
    assert event.provenance_ref == "attestation:1"
    assert op.value["agent"] == "agent-a"
    assert kernel.retrieve("source") == [event]


def test_lesson_retrieval_can_change_later_context():
    kernel = MemoryKernel()
    kernel.write_experience("agent-a", "failure", {"lesson": "abstain on missing provenance"}, "audit:1")
    context = kernel.retrieve("provenance")
    assert "abstain" in context[0].content["lesson"]
