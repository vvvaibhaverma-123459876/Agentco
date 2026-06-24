"""
Specialist Agent Entry Point
=============================
Allows specialist agents to be spawned as subprocesses.

Usage:
    python -m agents.autonomy.evidence_summarizer --specialist-id=X --port=5000 --role=evidence_summarizer
"""
import sys
import argparse

# Entry point for running a specialist agent
if __name__ == "__main__":
    # This module should not be run directly
    # Instead, run a specific specialist agent
    print("Error: Please run a specific specialist agent, e.g.:")
    print("  python -m agents.autonomy.evidence_summarizer --port=5000")
    sys.exit(1)
