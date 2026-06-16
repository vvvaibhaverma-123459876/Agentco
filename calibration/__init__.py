"""
AgentCo V2 Calibration Engine — Layer 0.

Eight components:
1. Prediction Ledger (immutable, append-only)
2. Resolution Service
3. Scoring Module (Brier, log, ECE, reliability diagrams)
4. Trust Controller + mechanical downgrade propagation
5. Reality/Simulation Firewall + promotion gate
6. Surprise Register
7. Decay Tracker
8. Self-Audit Module + human spot-audit interface
"""
from .ledger.prediction_ledger import PredictionLedger, PredictionRegistration, PredictionRecord
from .resolution.resolution_service import ResolutionService
from .scoring.scoring_module import ScoringModule, CalibrationReport
from .trust.trust_controller import TrustController, TrustScore
from .firewall.firewall import RealitySimulationFirewall, Belief
from .surprise.surprise_register import SurpriseRegister, SurpriseEvent
from .decay.decay_tracker import DecayTracker
from .self_audit.self_audit import SelfAuditModule, SelfAuditReport


def create_calibration_engine(db=None):
    """
    Instantiate the full Calibration Engine — all eight components wired together.
    This is the single entry point for the rest of the system.
    """
    ledger = PredictionLedger(db=db)
    scoring = ScoringModule()
    trust = TrustController()
    surprise = SurpriseRegister()
    firewall = RealitySimulationFirewall(ledger=ledger, db=db)
    decay = DecayTracker(firewall=firewall)
    resolution = ResolutionService(
        ledger=ledger,
        scoring=scoring,
        surprise_register=surprise,
        trust_controller=trust,
    )
    self_audit = SelfAuditModule(
        ledger=ledger,
        trust_controller=trust,
        surprise_register=surprise,
    )

    return {
        "ledger": ledger,
        "resolution": resolution,
        "scoring": scoring,
        "trust": trust,
        "firewall": firewall,
        "surprise": surprise,
        "decay": decay,
        "self_audit": self_audit,
    }


__all__ = [
    "PredictionLedger", "PredictionRegistration", "PredictionRecord",
    "ResolutionService", "ScoringModule", "CalibrationReport",
    "TrustController", "TrustScore", "RealitySimulationFirewall", "Belief",
    "SurpriseRegister", "SurpriseEvent", "DecayTracker",
    "SelfAuditModule", "SelfAuditReport", "create_calibration_engine",
]
