"""
AUTONOMOUS LEARNING SIMULATOR (5 MINUTES)

Let Agentco run freely and observe:
1. What it learns
2. How institutions evolve
3. Emergent behaviors
4. System health changes
5. Knowledge graph expansion

No human intervention - pure autonomous operation.
"""

import time
from dataclasses import dataclass
from typing import List
import random


@dataclass
class SystemSnapshot:
    timestamp: float
    total_knowledge_nodes: int
    mastered_nodes: int
    institutions_active: int
    expertise_average: float
    learning_events: int
    interconnections: int
    system_health: float
    emergent_behaviors: List[str]


class AutonomousLearningSimulator:
    """Simulate Agentco running autonomously"""

    def __init__(self):
        self.snapshots: List[SystemSnapshot] = []
        self.start_time = time.time()
        self.running_time = 0

        # Initial state
        self.knowledge_nodes = 100  # Start with some baseline
        self.mastered_nodes = 50
        self.institutions = 5
        self.expertise_avg = 0.50
        self.learning_events = 0
        self.interconnections = 150
        self.system_health = 0.85
        self.emergent_behaviors = []

    def simulate_learning_event(self) -> dict:
        """Simulate a single learning event"""
        event_type = random.choice(
            [
                "ingestion",
                "verification",
                "interconnection",
                "specialization",
                "synthesis",
                "feedback",
            ]
        )

        delta = {}

        if event_type == "ingestion":
            # New knowledge acquired
            new_nodes = random.randint(3, 8)
            self.knowledge_nodes += new_nodes
            delta["nodes"] = new_nodes
            delta["type"] = "Knowledge ingestion"
            self.learning_events += 1

        elif event_type == "verification":
            # Knowledge verified through testing
            verified = random.randint(1, 5)
            self.mastered_nodes += verified
            self.expertise_avg = min(1.0, self.expertise_avg + 0.02)
            delta["mastered"] = verified
            delta["type"] = "Knowledge verification"
            self.learning_events += 1

        elif event_type == "interconnection":
            # Creating connections between knowledge areas
            new_connections = random.randint(5, 15)
            self.interconnections += new_connections
            delta["connections"] = new_connections
            delta["type"] = "Interconnection creation"
            self.learning_events += 1

            # Check for emergent behavior
            if self.interconnections > 500 and "High graph density" not in self.emergent_behaviors:
                self.emergent_behaviors.append("High graph density (500+ connections)")

        elif event_type == "specialization":
            # Institution developing specialty
            self.expertise_avg = min(1.0, self.expertise_avg + 0.01)
            delta["type"] = "Specialization emergence"
            self.learning_events += 1

            if self.expertise_avg > 0.75 and "Deep specialization" not in self.emergent_behaviors:
                self.emergent_behaviors.append("Deep specialization detected (75%+ expertise)")

        elif event_type == "synthesis":
            # Cross-disciplinary knowledge synthesis
            self.expertise_avg = min(1.0, self.expertise_avg + 0.015)
            delta["type"] = "Cross-disciplinary synthesis"
            self.learning_events += 1

            if len(self.emergent_behaviors) < 5 and random.random() > 0.7:
                self.emergent_behaviors.append(f"Synthesis pattern {len(self.emergent_behaviors) + 1}")

        elif event_type == "feedback":
            # Learning from feedback
            improvement = random.uniform(0.01, 0.03)
            self.expertise_avg = min(1.0, self.expertise_avg + improvement)
            self.system_health = min(1.0, self.system_health + 0.01)
            delta["type"] = "Feedback integration"
            delta["improvement"] = improvement
            self.learning_events += 1

        # Simulate potential degradation (rare)
        if random.random() < 0.05:  # 5% chance of minor issue
            self.system_health = max(0.7, self.system_health - 0.02)

        return delta

    def run_autonomous_loop(self, duration_seconds: int = 300):
        """Run autonomous learning for specified duration"""
        print("\n" + "=" * 80)
        print("🤖 AGENTCO AUTONOMOUS LEARNING SIMULATOR (5 MINUTES)")
        print("=" * 80)

        print(f"\n⏱️ STARTING AUTONOMOUS RUN\n")

        # Take initial snapshot
        self._snapshot("START")

        start = time.time()
        iteration = 0

        while time.time() - start < duration_seconds:
            # Execute learning event
            event = self.simulate_learning_event()

            # Every 30 seconds (6 iterations at ~5s per), take a snapshot
            iteration += 1
            if iteration % 6 == 0:
                self._snapshot(f"30s checkpoint ({iteration // 6})")

            # Small delay to avoid tight loop
            time.sleep(0.01)

        self.running_time = time.time() - start

        # Final snapshot
        self._snapshot("END")

        print("\n✅ Autonomous run complete\n")

    def _snapshot(self, label: str):
        """Take a system snapshot"""
        snapshot = SystemSnapshot(
            timestamp=time.time() - self.start_time,
            total_knowledge_nodes=self.knowledge_nodes,
            mastered_nodes=self.mastered_nodes,
            institutions_active=self.institutions,
            expertise_average=self.expertise_avg,
            learning_events=self.learning_events,
            interconnections=self.interconnections,
            system_health=self.system_health,
            emergent_behaviors=self.emergent_behaviors.copy(),
        )

        self.snapshots.append(snapshot)

        # Print status
        print(f"[{label:20s}] @ {snapshot.timestamp:6.1f}s")
        print(
            f"  Knowledge: {snapshot.total_knowledge_nodes:3d} nodes, {snapshot.mastered_nodes:3d} mastered ({snapshot.mastered_nodes/snapshot.total_knowledge_nodes*100:5.1f}%)"
        )
        print(f"  Expertise: {snapshot.expertise_average:5.2f} | Health: {snapshot.system_health:5.2f}")
        print(f"  Learning events: {snapshot.learning_events:3d} | Connections: {snapshot.interconnections:4d}")

        if snapshot.emergent_behaviors:
            print(f"  🔮 Emergent behaviors: {len(snapshot.emergent_behaviors)}")
            for behavior in snapshot.emergent_behaviors[-2:]:
                print(f"     → {behavior}")

        print()

    def analyze_evolution(self):
        """Analyze system evolution"""
        print("\n" + "=" * 80)
        print("📊 SYSTEM EVOLUTION ANALYSIS")
        print("=" * 80)

        if len(self.snapshots) < 2:
            print("Not enough snapshots for analysis")
            return

        start = self.snapshots[0]
        end = self.snapshots[-1]

        print("\n📈 METRICS PROGRESSION\n")

        metrics = [
            ("Knowledge Nodes", start.total_knowledge_nodes, end.total_knowledge_nodes, "%d"),
            ("Mastered Nodes", start.mastered_nodes, end.mastered_nodes, "%d"),
            ("Expertise", start.expertise_average, end.expertise_average, "%.2f"),
            ("Health", start.system_health, end.system_health, "%.2f"),
            ("Interconnections", start.interconnections, end.interconnections, "%d"),
            ("Learning Events", start.learning_events, end.learning_events, "%d"),
        ]

        total_improvement = 0

        for name, start_val, end_val, fmt in metrics:
            if isinstance(start_val, float):
                change = end_val - start_val
                pct_change = (change / start_val * 100) if start_val != 0 else 0
            else:
                change = end_val - start_val
                pct_change = (change / start_val * 100) if start_val != 0 else 0

            direction = "↗️" if change > 0 else "→" if change == 0 else "↘️"
            status = "✅" if change > 0 else "⚠️" if change < 0 else "→"

            print(f"{status} {name:20s}: {fmt % start_val} → {fmt % end_val}")
            print(
                f"   {direction} Change: {change:+.1f} ({pct_change:+.1f}% over {self.running_time:.1f}s)\n"
            )

            if change > 0:
                total_improvement += abs(pct_change)

        print(f"Overall Improvement Score: {total_improvement:.1f}%\n")

        # Emergent behaviors
        print("🔮 EMERGENT BEHAVIORS DISCOVERED\n")

        if end.emergent_behaviors:
            for i, behavior in enumerate(end.emergent_behaviors, 1):
                print(f"  {i}. {behavior}")
        else:
            print("  (None detected)")

        print()

        # Learning efficiency
        print("⚡ LEARNING EFFICIENCY\n")

        if self.running_time > 0:
            learning_rate = end.learning_events / self.running_time
            nodes_per_event = (end.total_knowledge_nodes - start.total_knowledge_nodes) / max(1, end.learning_events)
            mastery_rate = (end.mastered_nodes - start.mastered_nodes) / max(1, end.learning_events)

            print(f"  Learning rate: {learning_rate:.1f} events/second")
            print(f"  Knowledge gain: {nodes_per_event:.2f} nodes/event")
            print(f"  Mastery rate: {mastery_rate:.2f} nodes mastered/event")
            print()

        # System health assessment
        print("❤️ SYSTEM HEALTH ASSESSMENT\n")

        if end.system_health >= 0.90:
            health_status = "🟢 Excellent (0.90+)"
        elif end.system_health >= 0.80:
            health_status = "🟢 Good (0.80-0.89)"
        elif end.system_health >= 0.70:
            health_status = "🟡 Moderate (0.70-0.79)"
        else:
            health_status = "🔴 Poor (<0.70)"

        print(f"  System health: {health_status}")
        print(f"  Knowledge quality: {end.mastered_nodes}/{end.total_knowledge_nodes} mastered")
        print(f"  Network density: {end.interconnections} connections")
        print()

        # Conclusions
        print("🎯 CONCLUSIONS\n")

        if total_improvement > 50:
            conclusion = "RAPID GROWTH - System learning faster than expected"
        elif total_improvement > 20:
            conclusion = "STEADY IMPROVEMENT - Normal autonomous growth"
        elif total_improvement > 0:
            conclusion = "MODEST GROWTH - Learning occurring at baseline rate"
        else:
            conclusion = "STAGNATION - No measurable improvement"

        print(f"  {conclusion}")
        print(f"  Expertise developed from {start.expertise_average:.2f} → {end.expertise_average:.2f}")
        print(f"  Knowledge base grew {(end.total_knowledge_nodes - start.total_knowledge_nodes) / start.total_knowledge_nodes * 100:.1f}%")
        print()

        return {
            "improvement_score": total_improvement,
            "health_status": health_status,
            "emergent_behaviors": len(end.emergent_behaviors),
            "conclusion": conclusion,
        }


def run_5_minute_autonomous_test():
    """Run the 5-minute autonomous learning test"""
    simulator = AutonomousLearningSimulator()
    simulator.run_autonomous_loop(duration_seconds=300)  # 5 minutes
    return simulator.analyze_evolution()


if __name__ == "__main__":
    run_5_minute_autonomous_test()
