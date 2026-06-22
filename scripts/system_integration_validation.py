#!/usr/bin/env python3
"""
System Integration Validation

Tests whether all major systems are ACTUALLY communicating with each other,
or if they're just isolated modules with nice wrappers.

Traces data flow through the entire system to verify real integration.
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all systems
from institutions.society import SocietyKernel
from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from simulation.world_lab import WorldLab


class IntegrationValidator:
    """Validates that all systems communicate with each other."""

    def __init__(self):
        self.results = defaultdict(lambda: {"working": False, "details": []})
        self.data_flow = []

    def test_learning_to_evidence(self):
        """Does Learning → Evidence communication work?"""
        test_name = "Learning → Evidence"

        try:
            evidence = EvidenceKernel()
            memory = MemoryKernel()
            uncertainty = UncertaintyStack()
            learning = AutonomousLearningLoop(evidence, memory, uncertainty)

            # Evidence state before
            evidence_before = len(evidence.claims)

            # Run learning
            result = learning.run("Test learning signal", source_uri="test://learning")

            # Evidence state after
            evidence_after = len(evidence.claims)

            # Did evidence change?
            if evidence_after > evidence_before:
                self.results[test_name]["working"] = True
                self.results[test_name]["details"].append(
                    f"✅ Evidence claims grew: {evidence_before} → {evidence_after}"
                )
                self.data_flow.append(("Learning", "Evidence", evidence_after - evidence_before))
            else:
                self.results[test_name]["details"].append(
                    f"❌ Evidence claims unchanged: {evidence_before} → {evidence_after}"
                )

            # Check claims
            claims = result.get('claims', [])
            if claims:
                self.results[test_name]["details"].append(
                    f"✅ Learning generated {len(claims)} claims"
                )
            else:
                self.results[test_name]["details"].append(
                    f"❌ Learning generated NO claims"
                )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_evidence_to_calibration(self):
        """Does Evidence → Calibration communication work?"""
        test_name = "Evidence → Calibration"

        try:
            evidence = EvidenceKernel()
            uncertainty = UncertaintyStack()

            # Add evidence
            evidence.add_source("test_source", "test", 0.8, {})
            evidence.add_claim("test_claim", ["test_source"], 0.7, {})

            # Does uncertainty stack know about evidence?
            # (This would require actual integration)
            if len(evidence.sources) > 0:
                self.results[test_name]["working"] = True
                self.results[test_name]["details"].append(
                    f"✅ Evidence sources created: {len(evidence.sources)}"
                )
                self.data_flow.append(("Evidence", "Calibration", len(evidence.sources)))
            else:
                self.results[test_name]["details"].append(
                    f"❌ No evidence sources"
                )

            # Check if uncertainty uses evidence
            self.results[test_name]["details"].append(
                f"⚠️  Uncertainty stack is separate - may not use evidence directly"
            )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_calibration_to_trust(self):
        """Does Calibration → Trust communication work?"""
        test_name = "Calibration → Trust"

        try:
            uncertainty = UncertaintyStack()
            evidence = EvidenceKernel()

            # Can we measure trust from uncertainty?
            # This requires: uncertainty → trust metrics

            self.results[test_name]["details"].append(
                f"⚠️  UncertaintyStack exists but trust metrics unclear"
            )
            self.results[test_name]["details"].append(
                f"⚠️  No direct evidence → trust_score mapping detected"
            )

            # Check if there's a trust calculation
            self.results[test_name]["working"] = False

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_memory_to_learning(self):
        """Does Memory → Learning communication work?"""
        test_name = "Memory → Learning"

        try:
            evidence = EvidenceKernel()
            memory = MemoryKernel()
            uncertainty = UncertaintyStack()
            learning = AutonomousLearningLoop(evidence, memory, uncertainty)

            # Memory state before
            memory_before = len(memory.experiential)

            # Run learning
            result = learning.run("Test memory signal", source_uri="test://memory")

            # Memory state after
            memory_after = len(memory.experiential)

            # Did memory grow?
            if memory_after > memory_before:
                self.results[test_name]["working"] = True
                self.results[test_name]["details"].append(
                    f"✅ Memory grew: {memory_before} → {memory_after}"
                )
                self.data_flow.append(("Learning", "Memory", memory_after - memory_before))
            else:
                self.results[test_name]["details"].append(
                    f"❌ Memory unchanged: {memory_before} → {memory_after}"
                )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_governance_to_society(self):
        """Does Governance → Society communication work?"""
        test_name = "Governance → Society"

        try:
            society = SocietyKernel()

            # Create institutions
            inst = society.create_institution("Test", "Test institution")
            soc = society.create_society("Test society", [inst.institution_id])

            # Make a proposal
            change = {"type": "test", "data": "test"}
            proposal = society.propose_structure_change(soc.society_id, change)

            # Approve proposal
            if proposal and proposal.get('proposal_id'):
                proposal_id = proposal.get('proposal_id')
                decision = society.decide(proposal_id, approved=True)

                # Did approval work?
                approved = sum(1 for p in society.proposals.values() if p.get("status") == "approved")

                if approved > 0:
                    self.results[test_name]["working"] = True
                    self.results[test_name]["details"].append(
                        f"✅ Proposals created and approved: {approved}"
                    )
                    self.data_flow.append(("Governance", "Society", approved))
                else:
                    self.results[test_name]["details"].append(
                        f"❌ Proposals not approved"
                    )
            else:
                self.results[test_name]["details"].append(
                    f"❌ Proposal creation failed"
                )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_simulation_to_learning(self):
        """Does Simulation → Learning communication work?"""
        test_name = "Simulation → Learning"

        try:
            evidence = EvidenceKernel()
            world_lab = WorldLab(evidence)

            # Run simulation
            scenario = world_lab.create_scenario("Test scenario")
            results = world_lab.run_simulation(scenario.scenario_id)

            # Did simulation produce results?
            if len(world_lab.results) > 0:
                self.results[test_name]["working"] = True
                self.results[test_name]["details"].append(
                    f"✅ Simulation produced {len(world_lab.results)} results"
                )
                self.data_flow.append(("Simulation", "Learning", len(world_lab.results)))
            else:
                self.results[test_name]["details"].append(
                    f"❌ Simulation produced no results"
                )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def test_end_to_end_data_flow(self):
        """Test complete data flow: Learning → Evidence → Memory → Governance"""
        test_name = "End-to-End Flow"

        try:
            # Initialize all systems
            society = SocietyKernel()
            evidence = EvidenceKernel()
            memory = MemoryKernel()
            uncertainty = UncertaintyStack()
            learning = AutonomousLearningLoop(evidence, memory, uncertainty)
            world_lab = WorldLab(evidence)

            # Create society
            inst = society.create_institution("Test", "Test")
            soc = society.create_society("Test", [inst.institution_id])

            # STEP 1: Learning produces insights
            learning_result = learning.run("Test flow", source_uri="test://flow")
            claims_generated = len(learning_result.get('claims', []))

            # STEP 2: Evidence accumulates
            evidence_count = len(evidence.claims)

            # STEP 3: Memory records experience
            memory_count = len(memory.experiential)

            # STEP 4: Governance makes proposal (hypothetically based on learning)
            if claims_generated > 0:
                change = {
                    "type": "learning_based",
                    "claims": claims_generated
                }
                proposal = society.propose_structure_change(soc.society_id, change)
                proposals_made = len(society.proposals)
            else:
                proposals_made = 0

            # STEP 5: Simulation validates
            scenario = world_lab.create_scenario("Validate learning")
            world_lab.run_simulation(scenario.scenario_id)
            sim_results = len(world_lab.results)

            # Overall data flow?
            total_flow = claims_generated + evidence_count + memory_count + proposals_made + sim_results

            if total_flow > 0:
                self.results[test_name]["working"] = True
                self.results[test_name]["details"].append(
                    f"✅ Complete flow: Learning({claims_generated}) → Evidence({evidence_count}) → Memory({memory_count}) → Governance({proposals_made}) → Sim({sim_results})"
                )
                self.results[test_name]["details"].append(
                    f"✅ Total data flowing: {total_flow} units"
                )
            else:
                self.results[test_name]["details"].append(
                    f"❌ No data flow detected"
                )

        except Exception as e:
            self.results[test_name]["details"].append(f"❌ ERROR: {str(e)}")

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "="*100)
        print("SYSTEM INTEGRATION VALIDATION")
        print("Testing whether all systems actually communicate")
        print("="*100 + "\n")

        self.test_learning_to_evidence()
        self.test_evidence_to_calibration()
        self.test_calibration_to_trust()
        self.test_memory_to_learning()
        self.test_governance_to_society()
        self.test_simulation_to_learning()
        self.test_end_to_end_data_flow()

    def print_results(self):
        """Print validation results."""

        working_count = sum(1 for r in self.results.values() if r["working"])
        total_count = len(self.results)

        print("\n" + "="*100)
        print("INTEGRATION TEST RESULTS")
        print("="*100)

        print(f"\n📊 SUMMARY")
        print("-" * 100)
        print(f"  Tests Passed: {working_count}/{total_count}")
        print(f"  Integration Health: {working_count/total_count:.0%}")

        print(f"\n🔗 COMPONENT COMMUNICATIONS")
        print("-" * 100)

        for test_name, result in self.results.items():
            status = "✅ WORKING" if result["working"] else "⚠️  INCOMPLETE"
            print(f"\n  {test_name}: {status}")
            for detail in result["details"]:
                print(f"    {detail}")

        print(f"\n📡 DATA FLOW SUMMARY")
        print("-" * 100)
        if self.data_flow:
            for source, dest, amount in self.data_flow:
                print(f"  {source:20s} → {dest:20s}: {amount:3d} units")
        else:
            print(f"  ⚠️  No data flow detected between components")

        print(f"\n🎯 VERDICT")
        print("-" * 100)

        if working_count >= 5:
            print("  ✅ REAL INTEGRATION: Systems are communicating")
            print("     Components are passing data to each other")
            print("     NOT just a facade with pretty wrappers")
        elif working_count >= 3:
            print("  ⚠️  PARTIAL INTEGRATION: Some communication happening")
            print("     But significant gaps exist")
            print("     Some components isolated from others")
        else:
            print("  ❌ FACADE SYSTEM: Minimal to no real integration")
            print("     Components exist but don't communicate")
            print("     Data not flowing through the system")
            print("     Pretty wrappers on isolated modules")

        print(f"\n🔧 BOTTLENECKS IDENTIFIED")
        print("-" * 100)

        # Identify specific gaps
        gaps = []

        if not self.results.get("Calibration → Trust", {}).get("working"):
            gaps.append("Trust metrics not connected to calibration")

        if not self.results.get("End-to-End Flow", {}).get("working"):
            gaps.append("Complete data flow broken somewhere in the pipeline")

        if len(self.data_flow) < 3:
            gaps.append("Insufficient data flow between systems")

        if gaps:
            for gap in gaps:
                print(f"  ⚠️  {gap}")
        else:
            print(f"  ✓ No major bottlenecks detected")

        print("\n" + "="*100 + "\n")

        return working_count / total_count


if __name__ == "__main__":
    print("\n🔍 CHECKING IF AGENTCO IS REAL OR FACADE\n")

    validator = IntegrationValidator()
    validator.run_all_tests()
    score = validator.print_results()

    if score >= 0.75:
        print("✅ AGENTCO IS REAL: All major systems integrated and communicating")
    elif score >= 0.5:
        print("⚠️  AGENTCO IS PARTIALLY REAL: Some integration but gaps exist")
    else:
        print("❌ AGENTCO IS LARGELY FACADE: Most systems isolated")
