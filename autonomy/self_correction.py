"""
Meta-Autonomy Self-Correction Layer

True autonomy means:
1. Observe your own performance
2. Detect when you're failing
3. Diagnose the root cause
4. Fix the problem yourself
5. Verify the fix works
6. Remember what you learned

This enables REAL self-improvement, not just mechanical repetition.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI


class SystemObserver:
    """Observes system performance and detects anomalies."""

    def __init__(self):
        self.performance_history = []
        self.anomalies_detected = []
        self.patterns = defaultdict(list)

    def record_cycle(self, cycle_data: Dict):
        """Record one cycle of system performance."""
        self.performance_history.append({
            'timestamp': datetime.now().isoformat(),
            'data': cycle_data
        })

        # Analyze for patterns
        self._detect_patterns(cycle_data)

    def _detect_patterns(self, cycle_data: Dict):
        """Detect repeating failure patterns."""
        # Extract key metrics
        trust_score = cycle_data.get('trust_score', 0)
        calibration_confidence = cycle_data.get('calibration_confidence', 0)
        governance_decision = cycle_data.get('governance_decision', False)

        # Record patterns
        self.patterns['trust_scores'].append(trust_score)
        self.patterns['calibration_confidence'].append(calibration_confidence)
        self.patterns['governance_decisions'].append(governance_decision)

        # Detect anomalies
        if len(self.patterns['calibration_confidence']) >= 3:
            recent_cal = self.patterns['calibration_confidence'][-3:]
            if all(c == recent_cal[0] for c in recent_cal):  # All same value
                anomaly = {
                    'type': 'stuck_value',
                    'field': 'calibration_confidence',
                    'value': recent_cal[0],
                    'pattern_length': 3
                }
                if anomaly not in self.anomalies_detected:
                    self.anomalies_detected.append(anomaly)

    def get_diagnosis(self) -> Dict:
        """Diagnose what's wrong with the system."""
        diagnosis = {
            'health_status': 'HEALTHY',
            'issues': [],
            'root_causes': [],
            'severity': 0
        }

        # Check for stuck values
        if 'calibration_confidence' in self.patterns:
            cal_scores = self.patterns['calibration_confidence']
            if len(cal_scores) >= 3:
                recent = cal_scores[-3:]
                if all(c == 0.0 for c in recent):
                    diagnosis['issues'].append("Calibration always returning 0.0")
                    diagnosis['root_causes'].append("OpenAI response parsing broken - can't extract numbers from 'confidence' field")
                    diagnosis['severity'] += 50
                elif all(isinstance(c, int) and c in [0, 1] for c in recent):
                    diagnosis['issues'].append("Trust scores binary (0 or 1)")
                    diagnosis['root_causes'].append("OpenAI parsing creating binary values instead of 0-1 range")
                    diagnosis['severity'] += 30

        # Check governance decisions
        if 'governance_decisions' in self.patterns:
            decisions = self.patterns['governance_decisions']
            rejection_rate = (len([d for d in decisions if not d]) / len(decisions)) if decisions else 0
            if rejection_rate > 0.6:
                diagnosis['issues'].append(f"High rejection rate: {rejection_rate:.0%}")
                diagnosis['root_causes'].append("Low trust scores causing governance to reject proposals")
                diagnosis['severity'] += 40

        if diagnosis['severity'] > 50:
            diagnosis['health_status'] = 'CRITICAL'
        elif diagnosis['severity'] > 30:
            diagnosis['health_status'] = 'DEGRADED'

        return diagnosis


class SelfCorrectionEngine:
    """Fixes detected problems automatically."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
        self.observer = SystemObserver()
        self.corrections_attempted = []
        self.corrections_successful = []

    def observe_and_diagnose(self, cycle_data: Dict) -> Dict:
        """Observe cycle and diagnose issues."""
        self.observer.record_cycle(cycle_data)
        return self.observer.get_diagnosis()

    def propose_fix(self, diagnosis: Dict) -> Dict:
        """Use OpenAI to propose a fix."""
        if not diagnosis['root_causes']:
            return {'fix': None, 'reasoning': 'No issues detected'}

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a system self-correction engine. Propose specific code fixes for autonomous systems."
                    },
                    {
                        "role": "user",
                        "content": f"System issues: {diagnosis['issues']}\nRoot causes: {diagnosis['root_causes']}\n\nPropose a specific fix (be concrete, not vague)."
                    }
                ],
                temperature=0.7,
                max_tokens=200,
                timeout=5.0
            )

            fix_proposal = response.choices[0].message.content

            return {
                'fix': fix_proposal,
                'reasoning': 'OpenAI proposed this fix based on diagnosis',
                'severity': diagnosis['severity']
            }
        except Exception as e:
            return {
                'fix': None,
                'reasoning': f"Error getting fix proposal: {str(e)}",
                'severity': diagnosis['severity']
            }

    def apply_fix(self, fix: Dict) -> Dict:
        """Apply the proposed fix."""
        if not fix['fix']:
            return {'applied': False, 'result': 'No fix to apply'}

        self.corrections_attempted.append({
            'fix': fix['fix'],
            'timestamp': datetime.now().isoformat(),
            'status': 'applied'
        })

        # In a real system, would dynamically update code
        # For now, return the fix as guidance
        return {
            'applied': True,
            'fix_applied': fix['fix'],
            'result': 'Fix registered for next cycle',
            'guidance': fix['fix']
        }

    def verify_fix_effectiveness(self, before_diagnosis: Dict, after_diagnosis: Dict) -> Dict:
        """Check if the fix actually improved things."""
        improvement = {
            'severity_before': before_diagnosis.get('severity', 0),
            'severity_after': after_diagnosis.get('severity', 0),
            'improved': after_diagnosis.get('severity', 0) < before_diagnosis.get('severity', 0),
            'issues_resolved': len(before_diagnosis.get('issues', [])) - len(after_diagnosis.get('issues', []))
        }

        if improvement['improved']:
            self.corrections_successful.append(improvement)
            improvement['status'] = 'SUCCESS - Fix improved system'
        else:
            improvement['status'] = 'FAILED - Fix did not help'

        return improvement

    def self_correct_cycle(self, cycle_data: Dict, previous_diagnosis: Dict = None) -> Dict:
        """
        Complete self-correction cycle:
        1. Observe performance
        2. Diagnose issues
        3. Compare to previous (detect if still broken)
        4. Propose fix
        5. Apply fix
        6. Return guidance for next cycle
        """

        # STEP 1: Observe and diagnose current cycle
        current_diagnosis = self.observe_and_diagnose(cycle_data)

        # STEP 2: If we already diagnosed this before, check if we're repeating
        if previous_diagnosis:
            if current_diagnosis['health_status'] == previous_diagnosis.get('health_status'):
                current_diagnosis['stuck'] = True
                current_diagnosis['issue'] = "Same problem as last cycle - diagnosis not fixed yet"

        # STEP 3: If there's a problem, propose and apply fix
        correction_action = None
        if current_diagnosis['health_status'] != 'HEALTHY':
            fix_proposal = self.propose_fix(current_diagnosis)
            correction_action = self.apply_fix(fix_proposal)

        return {
            'cycle_diagnosis': current_diagnosis,
            'previous_diagnosis': previous_diagnosis,
            'correction_action': correction_action,
            'health_status': current_diagnosis['health_status'],
            'guidance_for_next_cycle': correction_action.get('guidance') if correction_action else None
        }


# Global instance
_self_correction_engine = None


def get_self_correction_engine() -> SelfCorrectionEngine:
    """Get the global self-correction engine."""
    global _self_correction_engine
    if _self_correction_engine is None:
        _self_correction_engine = SelfCorrectionEngine()
    return _self_correction_engine
