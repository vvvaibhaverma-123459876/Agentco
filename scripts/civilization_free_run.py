#!/usr/bin/env python3
"""
Civilization Free-Run CLI
==========================

Entry point for autonomous civilization operation without user-provided goals.

Usage:
    python scripts/civilization_free_run.py --duration 60 --mode fixture
    python scripts/civilization_free_run.py --duration 300 --mode read_only_web
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.civilization_service import CivilizationService


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


async def main() -> int:
    """Run civilization free-run."""
    parser = argparse.ArgumentParser(
        description="Run AgentCo Civilization in autonomous free-run mode"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--mode",
        choices=["fixture", "read_only_web", "real"],
        default="fixture",
        help="Execution mode (default: fixture)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Starting Civilization Free-Run (duration={args.duration}s, mode={args.mode})"
    )

    try:
        service = CivilizationService(mode=args.mode)
        result = await service.run_free_run(duration_seconds=args.duration)

        # Print summary
        print("\n" + "=" * 80)
        print("CIVILIZATION FREE-RUN COMPLETE")
        print("=" * 80)
        print(f"Run ID: {result.run_id}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Mode: {result.mode}")
        print(f"Internal Goals Generated: {len(result.internal_goals_generated)}")
        print(f"Claims Extracted: {result.claims_extracted}")
        print(f"Evidence Collected: {result.evidence_collected}")
        if result.report_path:
            print(f"Report: {result.report_path}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"  - {error}")
        print("=" * 80 + "\n")

        return 0 if not result.errors else 1

    except Exception as e:
        logger.error(f"Free-run failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
