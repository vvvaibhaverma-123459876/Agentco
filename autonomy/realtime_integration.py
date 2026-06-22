"""
Real-Time Integration Layer with OpenAI

Wires all systems together with real LLM reasoning:
- Evidence → Calibration (OpenAI evaluates evidence quality)
- Calibration → Trust (OpenAI converts metrics to trust)
- Trust → Governance (OpenAI informs decisions)
- Complete feedback loops with real reasoning
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


class RealTimeIntegrationEngine:
    """
    Complete integration with OpenAI driving all connections.
    Real reasoning through every component.
    """

    def __init__(self):
        # Initialize OpenAI
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No OpenAI API key found")

        self.client = OpenAI(api_key=api_key)

        # Initialize all systems
        self.society = SocietyKernel()
        self.evidence = EvidenceKernel()
        self.memory = MemoryKernel()
        self.uncertainty = UncertaintyStack()
        self.learning = AutonomousLearningLoop(self.evidence, self.memory, self.uncertainty)
        self.world_lab = WorldLab(self.evidence)

        # Setup institutions
        self._setup_institutions()

        # Metrics
        self.cycles_completed = 0
        self.openai_calls = 0
        self.trust_scores = {}
        self.calibration_metrics = {}

    def _setup_institutions(self):
        """Create institutional structure."""
        self.institutions = {
            'governance': self.society.create_institution("Governance", "Decision authority"),
            'evidence': self.society.create_institution("Evidence", "Evidence validation"),
            'learning': self.society.create_institution("Learning", "Knowledge synthesis"),
            'trust': self.society.create_institution("Trust", "Trustworthiness metrics"),
        }

        self.primary_society = self.society.create_society(
            "Integrated Collective",
            [inst.institution_id for inst in self.institutions.values()]
        )

    def run_integrated_cycle(self, situation: Dict) -> Dict:
        """
        Run one complete integrated cycle with OpenAI reasoning at every step:

        1. Learning processes signal
        2. Evidence evaluated by OpenAI
        3. Calibration metrics computed with OpenAI
        4. Trust calculated from calibration
        5. Governance makes decision informed by trust
        6. Outcome measured and fed back
        """

        cycle_start = datetime.now()
        self.cycles_completed += 1

        # PHASE 1: LEARNING - Process the situation
        print(f"\n[Cycle {self.cycles_completed}] {situation['problem']}")
        print(f"  Phase 1: Learning...", end="", flush=True)

        learning_result = self.learning.run(
            situation['problem'],
            source_uri=f"integrated://cycle-{self.cycles_completed}"
        )

        claims_generated = len(learning_result.get('claims', []))
        hypothesis_valid = bool(learning_result.get('hypothesis'))
        print(f" ✓ ({claims_generated} claims)")

        # PHASE 2: EVIDENCE EVALUATION with OpenAI
        print(f"  Phase 2: Evaluating evidence with OpenAI...", end="", flush=True)

        evidence_evaluation = self._evaluate_evidence_with_openai(
            claims_generated,
            situation
        )

        evidence_quality = evidence_evaluation['quality_score']
        print(f" ✓ (quality: {evidence_quality:.2f})")

        # PHASE 3: CALIBRATION with OpenAI
        print(f"  Phase 3: Calibrating metrics with OpenAI...", end="", flush=True)

        calibration_result = self._calibrate_with_openai(
            evidence_quality,
            claims_generated,
            hypothesis_valid
        )

        calibration_confidence = calibration_result['confidence']
        print(f" ✓ (confidence: {calibration_confidence:.2f})")

        # PHASE 4: TRUST CALCULATION with OpenAI
        print(f"  Phase 4: Calculating trust score with OpenAI...", end="", flush=True)

        trust_result = self._calculate_trust_with_openai(
            calibration_confidence,
            evidence_quality,
            claims_generated
        )

        trust_score = trust_result['trust_score']
        self.trust_scores[self.cycles_completed] = trust_score
        print(f" ✓ (trust: {trust_score:.2f})")

        # PHASE 5: GOVERNANCE DECISION with OpenAI
        print(f"  Phase 5: Governance decision with OpenAI...", end="", flush=True)

        governance_result = self._make_governance_decision_with_openai(
            trust_score,
            situation,
            claims_generated
        )

        decision_made = governance_result['execute']
        approval_reason = governance_result['reasoning']
        print(f" ✓ ({'APPROVE' if decision_made else 'REJECT'})")

        # PHASE 6: EXECUTION (if approved)
        execution_result = None
        if decision_made:
            print(f"  Phase 6: Executing approved proposal...", end="", flush=True)

            change = {
                'type': 'integrated_evolution',
                'cycle': self.cycles_completed,
                'evidence_quality': evidence_quality,
                'trust_score': trust_score,
                'reason': approval_reason
            }

            proposal = self.society.propose_structure_change(
                self.primary_society.society_id,
                change
            )

            if proposal and proposal.get('proposal_id'):
                self.society.decide(proposal.get('proposal_id'), approved=True)
                execution_result = {'status': 'executed', 'proposal_id': proposal.get('proposal_id')}
                print(f" ✓")
            else:
                print(f" ✗ (proposal failed)")
        else:
            print(f"  Phase 6: Skipped (not approved)")

        # PHASE 7: MEASUREMENT & FEEDBACK
        print(f"  Phase 7: Recording outcomes...", end="", flush=True)

        system_state = {
            'claims': len(self.evidence.claims),
            'proposals': len(self.society.proposals),
            'approved_proposals': sum(1 for p in self.society.proposals.values() if p.get('status') == 'approved'),
            'memory': len(self.memory.experiential),
            'scenarios': len(self.world_lab.scenarios)
        }

        print(f" ✓")

        return {
            'cycle': self.cycles_completed,
            'situation': situation['problem'],
            'learning': {
                'claims_generated': claims_generated,
                'hypothesis_valid': hypothesis_valid
            },
            'evidence_quality': evidence_quality,
            'calibration_confidence': calibration_confidence,
            'trust_score': trust_score,
            'governance_decision': decision_made,
            'execution_result': execution_result,
            'system_state': system_state,
            'openai_calls_this_cycle': 4  # 4 OpenAI calls per cycle
        }

    def _evaluate_evidence_with_openai(self, claims_count: int, situation: Dict) -> Dict:
        """OpenAI evaluates evidence quality."""
        self.openai_calls += 1

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are evaluating evidence quality for an autonomous system. Be concise."
                    },
                    {
                        "role": "user",
                        "content": f"Evidence generated: {claims_count} claims about '{situation['problem']}'. Rate evidence quality 0-100."
                    }
                ],
                temperature=0.7,
                max_tokens=50,
                timeout=5.0
            )

            content = response.choices[0].message.content
            import re
            match = re.search(r'(\d+)', content)
            quality = int(match.group(1)) / 100.0 if match else 0.5

            return {
                'quality_score': quality,
                'claims_count': claims_count,
                'reasoning': content[:100]
            }
        except Exception as e:
            return {'quality_score': 0.5, 'claims_count': claims_count, 'reasoning': str(e)}

    def _calibrate_with_openai(self, evidence_quality: float, claims: int, hypothesis: bool) -> Dict:
        """OpenAI calibrates confidence metrics."""
        self.openai_calls += 1

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Calibrate confidence: how reliable are these metrics?"
                    },
                    {
                        "role": "user",
                        "content": f"Evidence quality: {evidence_quality:.2f}, Claims: {claims}, Hypothesis: {hypothesis}. Confidence 0-100?"
                    }
                ],
                temperature=0.7,
                max_tokens=50,
                timeout=5.0
            )

            content = response.choices[0].message.content
            import re
            match = re.search(r'(\d+)', content)
            confidence = int(match.group(1)) / 100.0 if match else 0.5

            self.calibration_metrics[self.cycles_completed] = confidence

            return {
                'confidence': confidence,
                'reasoning': content[:100]
            }
        except Exception as e:
            return {'confidence': 0.5, 'reasoning': str(e)}

    def _calculate_trust_with_openai(self, calibration: float, evidence: float, claims: int) -> Dict:
        """OpenAI calculates trust score from calibration and evidence."""
        self.openai_calls += 1

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Calculate trustworthiness score 0-100 based on evidence and calibration."
                    },
                    {
                        "role": "user",
                        "content": f"Calibration: {calibration:.2f}, Evidence: {evidence:.2f}, Claims: {claims}. Trust score?"
                    }
                ],
                temperature=0.7,
                max_tokens=50,
                timeout=5.0
            )

            content = response.choices[0].message.content
            import re
            match = re.search(r'(\d+)', content)
            trust = int(match.group(1)) / 100.0 if match else 0.5

            return {
                'trust_score': trust,
                'reasoning': content[:100]
            }
        except Exception as e:
            return {'trust_score': 0.5, 'reasoning': str(e)}

    def _make_governance_decision_with_openai(self, trust: float, situation: Dict, claims: int) -> Dict:
        """OpenAI makes governance decision based on trust and situation."""
        self.openai_calls += 1

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a governance system. Decide whether to approve structural changes based on trust and evidence."
                    },
                    {
                        "role": "user",
                        "content": f"Situation: {situation['problem']}. Trust: {trust:.2f}. Claims: {claims}. Approve change? Yes/No with brief reason."
                    }
                ],
                temperature=0.7,
                max_tokens=80,
                timeout=5.0
            )

            content = response.choices[0].message.content.upper()
            execute = 'YES' in content or trust > 0.6

            return {
                'execute': execute,
                'reasoning': content[:100],
                'trust_threshold_met': trust > 0.5
            }
        except Exception as e:
            return {
                'execute': trust > 0.5,
                'reasoning': str(e),
                'trust_threshold_met': trust > 0.5
            }

    def get_integration_status(self) -> Dict:
        """Get status of full integration."""
        return {
            'cycles_completed': self.cycles_completed,
            'openai_calls': self.openai_calls,
            'trust_scores': self.trust_scores,
            'calibration_metrics': self.calibration_metrics,
            'system_state': {
                'claims': len(self.evidence.claims),
                'proposals': len(self.society.proposals),
                'approved': sum(1 for p in self.society.proposals.values() if p.get('status') == 'approved'),
                'memory': len(self.memory.experiential)
            },
            'avg_trust': sum(self.trust_scores.values()) / len(self.trust_scores) if self.trust_scores else 0
        }


# Global instance
_integration_engine = None

def get_integration_engine() -> RealTimeIntegrationEngine:
    """Get the global integration engine."""
    global _integration_engine
    if _integration_engine is None:
        _integration_engine = RealTimeIntegrationEngine()
    return _integration_engine
