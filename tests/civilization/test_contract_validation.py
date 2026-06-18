"""
Phase 4 — Contract validation tests.
Validates that: missing contract file, self-cert reviewer, empty lists, missing
reputation_metric all raise ContractValidationError.
"""
import pytest
from civilization.services.institution_service import (
    ContractValidationError,
    _validate_contract,
    load_contract,
)

VALID = {
    "institution_name": "TestInst",
    "accepted_inputs": ["a"],
    "produced_outputs": ["b"],
    "verification_required": True,
    "required_external_reviewer": "OtherInst",
    "failure_conditions": ["f1"],
    "escalation_target": "governance",
    "reputation_metric": "overall_log_score",
}


def test_valid_contract_passes():
    _validate_contract(VALID)  # no raise


def test_missing_contract_file_raises():
    with pytest.raises(ContractValidationError, match="No contract file"):
        load_contract("NonExistentInstitution12345")


def test_self_cert_reviewer_raises():
    bad = {**VALID, "required_external_reviewer": "TestInst"}
    with pytest.raises(ContractValidationError, match="self-cert ban"):
        _validate_contract(bad)


def test_empty_accepted_inputs_raises():
    with pytest.raises(ContractValidationError, match="accepted_inputs"):
        _validate_contract({**VALID, "accepted_inputs": []})


def test_empty_produced_outputs_raises():
    with pytest.raises(ContractValidationError, match="produced_outputs"):
        _validate_contract({**VALID, "produced_outputs": []})


def test_empty_failure_conditions_raises():
    with pytest.raises(ContractValidationError, match="failure_conditions"):
        _validate_contract({**VALID, "failure_conditions": []})


def test_missing_reputation_metric_raises():
    bad = {k: v for k, v in VALID.items() if k != "reputation_metric"}
    with pytest.raises(ContractValidationError, match="reputation_metric"):
        _validate_contract(bad)


def test_real_engineering_contract_loads():
    c = load_contract("Engineering")
    assert c["institution_name"] == "Engineering"
    assert c["required_external_reviewer"] != "Engineering"


def test_real_security_contract_loads():
    c = load_contract("Security")
    assert c["institution_name"] == "Security"
    assert c["required_external_reviewer"] != "Security"
