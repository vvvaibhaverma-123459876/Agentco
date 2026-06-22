from __future__ import annotations

import uuid
from dataclasses import dataclass

from calibration.evidence import EvidenceKernel


@dataclass
class Scenario:
    scenario_id: str
    description: str


class WorldLab:
    def __init__(self, evidence: EvidenceKernel | None = None):
        self.evidence = evidence or EvidenceKernel()
        self.scenarios: dict[str, Scenario] = {}
        self.results: dict[str, dict] = {}

    def create_scenario(self, description: str) -> Scenario:
        scenario = Scenario(str(uuid.uuid4()), description)
        self.scenarios[scenario.scenario_id] = scenario
        return scenario

    def run_simulation(self, scenario_id: str) -> dict:
        result = {
            "result_id": str(uuid.uuid4()),
            "scenario_id": scenario_id,
            "evidence_quality": "simulated",
            "insight": f"Simulated insight for {scenario_id}",
        }
        self.results[result["result_id"]] = result
        return result

    def convert_to_hypothesis(self, result_id: str):
        result = self.results[result_id]
        return self.evidence.create_claim(
            result["insight"],
            source_uri=f"simulation://{result_id}",
            source_type="simulation",
        )
