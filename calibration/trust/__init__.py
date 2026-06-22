"""Trust measurement and calibration."""

from calibration.trust.trust_controller import TrustController, TrustScore

# Alias for backward compatibility
TrustCalculator = TrustController

__all__ = ["TrustController", "TrustCalculator", "TrustScore"]
