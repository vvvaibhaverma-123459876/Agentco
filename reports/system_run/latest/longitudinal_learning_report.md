# Longitudinal Learning Report

Generated from database state at 2026-07-02T14:56:11.718Z (run label: `longrun_1783004171466`).

- Improved cycles: 2
- Rolled-back (demotion) cycles: 1
- Durable improvement criterion met: true

| Cycle | Family | Domain | Baseline | Improved | Delta | Outcome |
|---|---|---|---|---|---|---|
| longrun_1783004171466-c1 | source_selection | longlearn_src_1783004171467 | 0.067 | 1.000 | 0.933 | improved |
| longrun_1783004171466-c2 | evidence_grounding | longlearn_ground_1783004171645 | 0.450 | 1.000 | 0.550 | improved |
| longrun_1783004171466-c3 | contradiction_handling | longlearn_demote_1783004171695 | 0.633 | n/a | n/a | rolled_back |

All rows above are read from `longitudinal_learning_cycles`; each row links a real
candidate, evaluation, canary run, and (for improved cycles) promoted skill version
with event-log lineage. Scores come from executed deterministic-benchmark policies,
not projections. This is clean-room benchmark evidence, not live-web/LLM evidence.
