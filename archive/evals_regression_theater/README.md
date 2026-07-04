# Archived: theatrical regression tests (G9)

These files were removed from `evals/regression/` because a pytest pass on
them did not mean anything about AgentCo:

- Several contain **no assertions at all** (`test_comprehensive_gap_analysis.py`,
  `test_action_loop_integration.py`, `test_civilization_load.py`) — they print
  "PASSED" and `return True/False`, which pytest treats as a pass either way.
- The "model comparison" benchmarks (`test_model_comparison.py`,
  `test_model_benchmark_comparison.py`, `test_rag_accuracy_improvement.py`)
  compare against **fabricated hardcoded scores** for GPT-4/Claude/etc. No
  external model was ever called.
- The "civilization/learning simulators" (`test_autonomous_learning_5min.py`,
  `test_5min_established_facts.py`, `test_civilization_integration.py`,
  `test_institutions_evolution.py`, `test_knowledge_retention.py`,
  `test_phase3_dynamic_calibration.py`, `test_phase1_2_fixes.py`,
  `test_phases_2_4_integration.py`) import **no AgentCo code**: they assert
  against classes and constants defined inside the test file itself.

They are kept here as historical artifacts only. Real coverage for these
areas lives in `backend/tests/` (real Postgres, real services) and the
remaining `evals/regression/` gates.
