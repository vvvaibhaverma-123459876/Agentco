#!/usr/bin/env python3
"""
Seed initial societies into the database.

This script creates the five foundational societies:
- Engineering Society
- Safety Society
- Economic Society
- Governance Society
- Memory Society
"""
from __future__ import annotations

import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from civilization.societies import create_society

SEED_SOCIETIES = [
    {
        "name": "Engineering Society",
        "domain": "engineering",
        "purpose": "Define engineering standards, review implementations, and govern technical decisions",
        "authority_scope": ["engineering", "architecture", "code_review"],
    },
    {
        "name": "Safety Society",
        "domain": "safety",
        "purpose": "Ensure safety standards, review safety-critical decisions, and manage risk mitigation",
        "authority_scope": ["safety", "risk_management", "incident_response"],
    },
    {
        "name": "Economic Society",
        "domain": "economics",
        "purpose": "Govern economic policies, budget allocation, and financial integrity",
        "authority_scope": ["economics", "budget", "compliance"],
    },
    {
        "name": "Governance Society",
        "domain": "governance",
        "purpose": "Define governance rules, oversee decision-making processes, and manage disputes",
        "authority_scope": ["governance", "justice", "authority"],
    },
    {
        "name": "Memory Society",
        "domain": "memory",
        "purpose": "Maintain institutional memory, record precedents, and preserve historical context",
        "authority_scope": ["memory", "precedent", "history"],
    },
]


def main():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"
    )

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True

        created = []
        for seed in SEED_SOCIETIES:
            try:
                society = create_society(
                    name=seed["name"],
                    domain=seed["domain"],
                    purpose=seed["purpose"],
                    authority_scope=seed["authority_scope"],
                    db=conn,
                )
                created.append(society.id)
                print(f"✓ Created society: {seed['name']} ({society.id})")
            except Exception as e:
                # Society might already exist, which is fine
                print(f"  (skipped {seed['name']}: {e})")

        conn.close()

        if created:
            print(f"\nSeeded {len(created)} societies successfully")
            return 0
        else:
            print("No new societies created (may already exist)")
            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
