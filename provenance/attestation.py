from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def _canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def _sha256(data: object) -> str:
    return hashlib.sha256(_canonical(data)).hexdigest()


@dataclass
class ActionAttestation:
    action_id: str
    principal_id: str
    tool_id: str
    policy_id: str | None
    input_hash: str
    output_hash: str
    evidence_refs: list[str]
    trusted_confidence: float
    risk_level: str
    tee_quote: str
    transparency_ref: str
    created_at: str
    signature_ed25519: str

    def signed_payload(self) -> dict:
        return {
            "action_id": self.action_id,
            "principal_id": self.principal_id,
            "tool_id": self.tool_id,
            "policy_id": self.policy_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "evidence_refs": self.evidence_refs,
            "trusted_confidence": self.trusted_confidence,
            "risk_level": self.risk_level,
            "tee_quote": self.tee_quote,
            "transparency_ref": self.transparency_ref,
            "created_at": self.created_at,
        }


@dataclass
class TransparencyLog:
    entries: dict[str, str] = field(default_factory=dict)

    def include(self, payload_hash: str) -> str:
        ref = f"local-log:{len(self.entries) + 1}:{payload_hash[:16]}"
        self.entries[ref] = payload_hash
        return ref

    def contains(self, ref: str, payload_hash: str) -> bool:
        return self.entries.get(ref) == payload_hash


class AttestationVerifier:
    def __init__(self, private_key: Ed25519PrivateKey | None = None, transparency: TransparencyLog | None = None):
        self.private_key = private_key or Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.transparency = transparency or TransparencyLog()

    @property
    def public_key_b64(self) -> str:
        raw = self.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw).decode()

    def attest(
        self,
        *,
        principal_id: str,
        tool_id: str,
        input_payload: object,
        output_payload: object,
        trusted_confidence: float,
        risk_level: str,
        policy_id: str | None = None,
        evidence_refs: list[str] | None = None,
        tee_quote: str = "local-measured-environment",
    ) -> ActionAttestation:
        payload_base = {
            "action_id": str(uuid.uuid4()),
            "principal_id": principal_id,
            "tool_id": tool_id,
            "policy_id": policy_id,
            "input_hash": _sha256(input_payload),
            "output_hash": _sha256(output_payload),
            "evidence_refs": evidence_refs or [],
            "trusted_confidence": trusted_confidence,
            "risk_level": risk_level,
            "tee_quote": tee_quote,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        transparency_ref = self.transparency.include(_sha256(payload_base))
        payload = {**payload_base, "transparency_ref": transparency_ref}
        signature = self.private_key.sign(_canonical(payload)).hex()
        return ActionAttestation(signature_ed25519=signature, **payload)

    def verify(self, attestation: ActionAttestation, public_key_b64: str | None = None) -> bool:
        if not attestation.tee_quote:
            return False
        payload = attestation.signed_payload()
        if not self.transparency.contains(attestation.transparency_ref, _sha256({k: v for k, v in payload.items() if k != "transparency_ref"})):
            return False
        try:
            raw = base64.b64decode(public_key_b64) if public_key_b64 else self.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
            Ed25519PublicKey.from_public_bytes(raw).verify(
                bytes.fromhex(attestation.signature_ed25519),
                _canonical(payload),
            )
            return True
        except Exception:
            return False
