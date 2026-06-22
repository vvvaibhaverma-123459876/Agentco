#!/usr/bin/env python3
"""
Evaluation Harness CLI - Runs evaluation on a candidate artifact
"""

import sys
import os

print("⚠️  Eval Harness CLI is scaffolded but eval logic is implemented via the orchestrator.")
print("   For production eval runs, use:")
print("   - make autonomy-level3-smoke  (includes eval in full loop)")
print("   - Python services: backend/src/services/eval-harness.service.ts")
print()
print("   This script would call the eval harness service with a specific candidate ID.")
print("   Example: python3 run_autonomy_eval.py --candidate-id <candidate-id>")

sys.exit(0)
