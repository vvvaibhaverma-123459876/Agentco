# Database Table Usage

Generated from migrations + service/test references + live row counts.

- Total tables declared in migrations: 219
- Referenced by a runtime service: 175
- Speculative (no service reference, no rows): 37

Classification:
- **runtime** — a `backend/src/services` file references the table.
- **test-only** — only tests reference it.
- **written-elsewhere** — has rows but no service/test reference found (likely written by SQL functions/triggers or Python).
- **speculative** — no reference and no rows; schema exists but capability is unproven.

| Table | Migration | Runtime writers | Rows | Classification |
|---|---|---|---|---|
| action_attestations | 018_refoundation_canonical_schema.sql | protected-surface-validator.service.ts, provenance.service.ts | 4 | runtime |
| active_constitution | 027_calibration_constitution.sql | calibration-constitution.service.ts | 3 | runtime |
| active_trust_policies | 028_trust_policy_versions.sql | autonomy-orchestrator.service.ts, trust-policy-canary.service.ts, trust-policy.service.ts | 0 | runtime |
| actor_key_ring | 086_key_ring.sql | identity-authority.service.ts | 3 | runtime |
| actor_permissions | 079_identity_authority.sql | identity-authority.service.ts | 2 | runtime |
| actors | 079_identity_authority.sql | civilization-runtime.service.ts, domain-registry.service.ts, event-log.service.ts | 128 | runtime |
| adaptive_strategies | 058_adaptive_strategy.sql | adaptive-strategy.service.ts | 28 | runtime |
| agent_identities | 079_identity_authority.sql | identity-authority.service.ts | 31 | runtime |
| agent_membership_edges | 078_agent_membership_id_compatibility.sql | — | 0 | speculative |
| agent_memories | 015_agent_memories.sql | memory-promotion-pipeline.service.ts, memory-retrieval.service.ts | 5 | runtime |
| agent_memory | 002_agent_memory.sql | memory-promotion-pipeline.service.ts, memory-store.service.ts | 3 | runtime |
| agent_state | 001_agent_state.sql | memory-store.service.ts | 29 | runtime |
| allowed_change_types | 027_calibration_constitution.sql | calibration-constitution.service.ts, civilization-runtime.service.ts, trust-policy.service.ts | 3 | runtime |
| artifacts | 033_artifacts.sql | action-executor.service.ts, autonomy-orchestrator.service.ts, candidate-evaluation.service.ts | 5 | runtime |
| audit_events | 097_self_modification_validation_compatibility.sql | civilization-runtime.service.ts, protected-surface-validator.service.ts, self-modification-validator.service.ts | 2 | runtime |
| authority_decision_chains | 084_authority_chain.sql | identity-authority.service.ts | 5 | runtime |
| authority_delegation_grants | 084_authority_chain.sql | identity-authority.service.ts | 1 | runtime |
| autonomy_actions | 023_autonomy_episodes.sql | action-executor.service.ts, trajectory-store.service.ts | 2 | runtime |
| autonomy_audit_events | 058_bounded_learning.sql | bounded-learning-run.service.ts | 159 | runtime |
| autonomy_calibration_events | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 5 | runtime |
| autonomy_calibration_reports | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 1 | runtime |
| autonomy_claim_validations | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 3 | runtime |
| autonomy_claims | 050_autonomy_action_loop.sql | action-executor.service.ts, autonomy-orchestrator.service.ts, bounded-learning-run.service.ts | 19 | runtime |
| autonomy_dead_letters | 022_autonomy_tasks.sql | crash-recovery.service.ts, task-engine.service.ts | 0 | runtime |
| autonomy_episodes | 023_autonomy_episodes.sql | action-executor.service.ts, calibration-change-governance.service.ts, longitudinal-learning-harness.service.ts | 131 | runtime |
| autonomy_evidence | 050_autonomy_action_loop.sql | action-executor.service.ts, autonomy-orchestrator.service.ts, bounded-learning-run.service.ts | 6 | runtime |
| autonomy_goal_actions | 050_autonomy_action_loop.sql | action-executor.service.ts, autonomy-orchestrator.service.ts | 22 | runtime |
| autonomy_goals | 025_goal_management_clean.sql | action-executor.service.ts, autonomy-orchestrator.service.ts, deadlock-detector.service.ts | 27 | runtime |
| autonomy_interventions | 023_autonomy_episodes.sql | observability.service.ts, trajectory-store.service.ts | 0 | runtime |
| autonomy_loop_detection | 050_autonomy_action_loop.sql | action-executor.service.ts | 2 | runtime |
| autonomy_memory | 050_autonomy_action_loop.sql | action-executor.service.ts, reflection.service.ts | 0 | runtime |
| autonomy_outcomes | 023_autonomy_episodes.sql | autonomy-orchestrator.service.ts, eval-harness.service.ts, reward-calculator.service.ts | 2 | runtime |
| autonomy_plan_steps | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, planner.service.ts | 4 | runtime |
| autonomy_plans | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, eval-harness.service.ts, planner.service.ts | 2 | runtime |
| autonomy_provider_calibration | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 1 | runtime |
| autonomy_routed_claims | 058_bounded_learning.sql | bounded-learning-run.service.ts | 0 | runtime |
| autonomy_searches | 050_autonomy_action_loop.sql | — | 0 | speculative |
| autonomy_self_mod_gates | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 3 | runtime |
| autonomy_source_discovery_runs | 058_bounded_learning.sql | — | 0 | speculative |
| autonomy_source_trustworthiness | 059_calibration_framework.sql | claim-accuracy-tracker.service.ts | 0 | runtime |
| autonomy_task_events | 022_autonomy_tasks.sql | — | 0 | speculative |
| autonomy_tasks | 022_autonomy_tasks.sql | autonomy-orchestrator.service.ts, crash-recovery.service.ts, observability.service.ts | 2 | runtime |
| autonomy_team_activations | 051_team_activations.sql | action-executor.service.ts, team-activation.service.ts | 9 | runtime |
| autonomy_workflow_checkpoints | 022_autonomy_tasks.sql | autonomy-orchestrator.service.ts, crash-recovery.service.ts, task-engine.service.ts | 2 | runtime |
| backup_recovery_log | 056_production_deployment.sql | — | 1 | test-only |
| baseline_metrics | 030_trust_impact_assessment.sql | trust-impact-assessment.service.ts | 0 | runtime |
| beliefs | 010_beliefs.sql | multi-agent-ensemble.service.ts | 0 | runtime |
| benchmark_eval_runs | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| build_ledger | 076_build_ledger.sql | civilization-runtime.service.ts | 0 | runtime |
| calibration_cells | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| calibration_change_requests | 029_calibration_change_requests.sql | calibration-change-governance.service.ts | 0 | runtime |
| calibration_constitution_versions | 027_calibration_constitution.sql | calibration-constitution.service.ts, civilization-runtime.service.ts | 3 | runtime |
| calibration_drift_events | 032_calibration_drift_monitor.sql | calibration-drift-monitor.service.ts | 0 | runtime |
| candidate_evaluations | 111_self_improvement_loop.sql | candidate-evaluation.service.ts, skill-canary.service.ts | 18 | runtime |
| candidate_regression_tests | 104_candidate_regression_tests.sql | candidate-evaluation.service.ts, regression-test-generator.service.ts, skill-deployment.service.ts | 152 | runtime |
| capability_expansion_decisions | 107_capability_expansion_gate.sql | capability-expansion-gate.service.ts | 20 | runtime |
| change_approvals | 029_calibration_change_requests.sql | calibration-change-governance.service.ts | 0 | runtime |
| change_request_events | 029_calibration_change_requests.sql | calibration-change-governance.service.ts | 0 | runtime |
| change_to_policy_conversions | 029_calibration_change_requests.sql | calibration-change-governance.service.ts | 0 | runtime |
| civilization_coordinator_ticks | 077_civilization_vertical_slice.sql | civilization-runtime.service.ts | 6 | runtime |
| civilization_entities | 026_civilization_learning_entities.sql | — | 0 | speculative |
| civilization_generality_metrics | 077_civilization_vertical_slice.sql | civilization-runtime.service.ts | 0 | runtime |
| civilization_governance_reviews | 026_civilization_learning_entities.sql | — | 0 | speculative |
| civilization_learning_events | 026_civilization_learning_entities.sql | — | 0 | speculative |
| civilization_memberships | 026_civilization_learning_entities.sql | — | 0 | speculative |
| civilization_resource_accounts | 081_resource_ledger.sql | civilization-runtime.service.ts, resource-ledger.service.ts | 5 | runtime |
| civilization_resource_reservations | 082_resource_reservations.sql | civilization-runtime.service.ts, resource-ledger.service.ts | 3 | runtime |
| civilization_resource_transactions | 081_resource_ledger.sql | civilization-runtime.service.ts, resource-ledger.service.ts | 6 | runtime |
| civilization_vector_documents | 077_civilization_vertical_slice.sql | — | 0 | speculative |
| civilization_vector_index | 077_civilization_vertical_slice.sql | — | 0 | speculative |
| civilization_vertical_slice_runs | 077_civilization_vertical_slice.sql | civilization-runtime.service.ts | 6 | runtime |
| claims | 018_refoundation_canonical_schema.sql | action-executor.service.ts, adaptive-strategy.service.ts, autonomy-action-planner.service.ts | 0 | runtime |
| coalition_collaboration_events | 060_coalition_formation.sql | — | 0 | speculative |
| coalition_composition_recommendations | 060_coalition_formation.sql | coalition-formation.service.ts | 1 | runtime |
| coalition_formations | 060_coalition_formation.sql | coalition-formation.service.ts | 0 | runtime |
| coalition_member_assignments | 060_coalition_formation.sql | — | 0 | speculative |
| coalition_performance | 060_coalition_formation.sql | — | 0 | speculative |
| consistency_checks | 055_deadlock_prevention.sql | deadlock-detector.service.ts, load-test-harness.service.ts | 0 | runtime |
| constitution_compliance_checks | 029_calibration_change_requests.sql | calibration-change-governance.service.ts | 0 | runtime |
| constitution_verifications | 027_calibration_constitution.sql | calibration-constitution.service.ts | 5 | runtime |
| constitutions | 018_refoundation_canonical_schema.sql | protected-surface-validator.service.ts | 0 | runtime |
| cross_institutional_evidence_access | 054_goal_hierarchies.sql | goal-hierarchy.service.ts | 0 | runtime |
| customer_data | 008_customer_data.sql | — | 0 | speculative |
| cutover_checklist | 056_production_deployment.sql | — | 5 | test-only |
| deadlock_incidents | 055_deadlock_prevention.sql | deadlock-detector.service.ts, load-test-harness.service.ts | 0 | runtime |
| decision_log | 004_decision_log.sql | audit-log.service.ts, civilization-runtime.service.ts, hash-chain-anchor.service.ts | 263 | runtime |
| departments | 052b_institutions.sql | civilization-live-flow.service.ts, civilization-runtime.service.ts, deadlock-detector.service.ts | 215 | runtime |
| deployment_events | 056_production_deployment.sql | — | 4 | test-only |
| disaster_recovery_snapshots | 056_production_deployment.sql | — | 2 | test-only |
| disputes | 109_judiciary.sql | calibration-constitution.service.ts, judiciary.service.ts | 4 | runtime |
| domain_registry | 102_domain_registry.sql | capability-expansion-gate.service.ts, civilization-runtime.service.ts, domain-registry.service.ts | 37 | runtime |
| drift_resolutions | 032_calibration_drift_monitor.sql | calibration-drift-monitor.service.ts | 0 | runtime |
| drift_thresholds | 032_calibration_drift_monitor.sql | calibration-drift-monitor.service.ts | 0 | runtime |
| entity_hierarchy | 057_reputation_learning.sql | reputation-learning.service.ts | 0 | runtime |
| entity_reputation_audit_log | 052b_institutions.sql | — | 0 | speculative |
| entity_reputation_baseline | 052b_institutions.sql | — | 0 | speculative |
| eval_cases | 025_goal_management_clean.sql | — | 0 | speculative |
| eval_failures | 025_goal_management_clean.sql | — | 0 | speculative |
| eval_results | 025_goal_management_clean.sql | — | 0 | speculative |
| eval_runs | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, calibration-change-governance.service.ts, eval-harness.service.ts | 2 | runtime |
| eval_scorecards | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, eval-harness.service.ts, observability.service.ts | 2 | runtime |
| eval_suites | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, eval-harness.service.ts | 1 | runtime |
| event_dead_letters | 083_transactional_outbox.sql | transactional-outbox.service.ts | 1 | runtime |
| event_history | 005_event_history.sql | event-bus.service.ts, identity-authority.service.ts, protected-surface-validator.service.ts | 94 | runtime |
| event_log | 080_event_log.sql | civilization-live-flow.service.ts, civilization-runtime.service.ts, event-log.service.ts | 755 | runtime |
| event_outbox | 083_transactional_outbox.sql | civilization-runtime.service.ts, transactional-outbox.service.ts | 755 | runtime |
| evidence_artifacts | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| evidence_deduplication_map | 054_goal_hierarchies.sql | goal-hierarchy.service.ts | 1 | runtime |
| evidence_vector_documents | 101_evidence_vector_index.sql | evidence-vector-index.service.ts | 3 | runtime |
| evidence_vector_index | 101_evidence_vector_index.sql | evidence-vector-index.service.ts | 9 | runtime |
| failure_recovery_incidents | 056_production_deployment.sql | — | 0 | test-only |
| generality_domain_scores | 103_generality_metric_tracker.sql | generality-metric-tracker.service.ts | 22 | runtime |
| generality_metric_runs | 103_generality_metric_tracker.sql | generality-metric-tracker.service.ts | 21 | runtime |
| goal_budgets | 025_goal_management_clean.sql | goal-manager.service.ts | 2 | runtime |
| goal_conflicts | 025_goal_management_clean.sql | — | 0 | speculative |
| goal_dependency_graph | 055_deadlock_prevention.sql | deadlock-detector.service.ts | 0 | runtime |
| goal_evidence | 025_goal_management_clean.sql | goal-formation.service.ts, goal-manager.service.ts | 2 | runtime |
| goal_execution_locks | 055_deadlock_prevention.sql | deadlock-detector.service.ts | 0 | runtime |
| goal_reviews | 025_goal_management_clean.sql | goal-manager.service.ts | 1 | runtime |
| goal_rollup_results | 054_goal_hierarchies.sql | goal-hierarchy.service.ts | 0 | runtime |
| goal_status_events | 025_goal_management_clean.sql | goal-manager.service.ts | 7 | runtime |
| governance_coalition_formations | 074_governance_coalition_formations.sql | governance-reputation-integration.service.ts | 2 | runtime |
| governance_constraint_violations | 055_deadlock_prevention.sql | deadlock-detector.service.ts | 0 | runtime |
| governance_entity_roles | 040_governance_rbac.sql | governance-rbac.service.ts | 5 | runtime |
| governance_kill_switches | 098_governance_kill_switch.sql | civilization-runtime.service.ts, kill-switch.service.ts | 13 | runtime |
| governance_permissions | 040_governance_rbac.sql | governance-rbac.service.ts | 10 | runtime |
| governance_rbac_audit | 040_governance_rbac.sql | governance-rbac.service.ts | 6 | runtime |
| governance_reputation_audit | 059_governance_reputation_integration.sql | governance-reputation-integration.service.ts | 112 | runtime |
| governance_reputation_decisions | 059_governance_reputation_integration.sql | governance-reputation-integration.service.ts | 14 | runtime |
| governance_reputation_votes | 059_governance_reputation_integration.sql | governance-reputation-integration.service.ts | 112 | runtime |
| governance_role_permissions | 040_governance_rbac.sql | — | 33 | written-elsewhere |
| governance_roles | 040_governance_rbac.sql | governance-rbac.service.ts | 5 | runtime |
| hash_chain_anchors | 087_hash_chain_anchors.sql | hash-chain-anchor.service.ts | 3 | runtime |
| idempotency_records | 096_idempotency_store.sql | civilization-runtime.service.ts, idempotency-store.service.ts | 3 | runtime |
| if | 062_runtime_schema_compatibility.sql | action-executor.service.ts, adaptive-strategy.service.ts, audit-log.service.ts | 0 | runtime |
| institution_consistency_audit | 052b_institutions.sql | — | 0 | speculative |
| institution_specialist_assignments | 053_work_assignment_schema.sql | institution-work-assignment.service.ts, reputation-scale.service.ts | 15 | runtime |
| institution_work_requests | 053_work_assignment_schema.sql | civilization-runtime.service.ts, goal-hierarchy.service.ts, institution-claim-vetting.service.ts | 27 | runtime |
| institutional_knowledge_items | 026_civilization_learning_entities.sql | — | 0 | speculative |
| institutions | 052b_institutions.sql | civilization-live-flow.service.ts, civilization-runtime.service.ts, deadlock-detector.service.ts | 44 | runtime |
| learner_candidates | 034_learner_infrastructure.sql | candidate-evaluation.service.ts, civilization-live-flow.service.ts, civilization-runtime.service.ts | 46 | runtime |
| learner_runs | 034_learner_infrastructure.sql | civilization-live-flow.service.ts, learner.service.ts | 44 | runtime |
| load_test_results | 056_production_deployment.sql | load-test-harness.service.ts | 2 | runtime |
| longitudinal_learning_cycles | 111_self_improvement_loop.sql | longitudinal-learning-harness.service.ts | 3 | runtime |
| memory_events | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| memory_retrieval_events | 023_autonomy_episodes.sql | — | 0 | speculative |
| metric_snapshots | 021_observability_traces.sql | — | 0 | speculative |
| metrics | 021_observability_traces.sql | adaptive-strategy.service.ts, autonomy-action-planner.service.ts, autonomy-metrics.service.ts | 0 | runtime |
| override_cases | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| override_queue | 013_override_queue.sql | override-queue.service.ts, protected-surface-validator.service.ts | 8 | runtime |
| perception_adapter_runs | 024_perception_infrastructure.sql | perception.service.ts | 0 | runtime |
| perception_artifacts | 024_perception_infrastructure.sql | perception.service.ts | 0 | runtime |
| perception_events | 024_perception_infrastructure.sql | autonomy-orchestrator.service.ts, perception.service.ts | 2 | runtime |
| perception_sources | 024_perception_infrastructure.sql | autonomy-orchestrator.service.ts, perception.service.ts | 1 | runtime |
| performance_metrics | 007_performance_metrics.sql | — | 0 | speculative |
| permissions | 079_identity_authority.sql | civilization-runtime.service.ts, governance-rbac.service.ts, identity-authority.service.ts | 6 | runtime |
| plan_reviews | 025_goal_management_clean.sql | planner.service.ts | 0 | runtime |
| plan_status_events | 025_goal_management_clean.sql | planner.service.ts | 0 | runtime |
| policies | 018_refoundation_canonical_schema.sql | autonomy-orchestrator.service.ts, civilization-runtime.service.ts, deterministic-benchmark.service.ts | 0 | runtime |
| policy_canary_deployments | 028_trust_policy_versions.sql | civilization-runtime.service.ts, trust-policy-canary.service.ts, trust-policy.service.ts | 0 | runtime |
| policy_change_events | 028_trust_policy_versions.sql | trust-policy-canary.service.ts, trust-policy.service.ts | 0 | runtime |
| policy_evaluations | 028_trust_policy_versions.sql | trust-policy.service.ts | 0 | runtime |
| policy_reviews | 028_trust_policy_versions.sql | trust-policy.service.ts | 0 | runtime |
| precedents | 109_judiciary.sql | judiciary.service.ts | 2 | runtime |
| prediction_ledger | 011_prediction_ledger.sql | calibration-change-governance.service.ts, civilization-runtime.service.ts, credential.service.ts | 1 | runtime |
| principals | 018_refoundation_canonical_schema.sql | provenance.service.ts | 3 | runtime |
| production_metrics | 056_production_deployment.sql | — | 3 | test-only |
| prohibited_change_types | 027_calibration_constitution.sql | calibration-constitution.service.ts, civilization-runtime.service.ts, trust-policy.service.ts | 2 | runtime |
| prompt_registry | 006_prompt_registry.sql | — | 0 | speculative |
| proof_of_competence | 106_proof_of_competence.sql | capability-expansion-gate.service.ts, proof-of-competence.service.ts, skill-retrieval.service.ts | 22 | runtime |
| protected_surfaces | 027_calibration_constitution.sql | calibration-constitution.service.ts, civilization-runtime.service.ts | 2 | runtime |
| replay_batches | 023_autonomy_episodes.sql | civilization-live-flow.service.ts, learner.service.ts, trajectory-store.service.ts | 44 | runtime |
| replay_training_metrics | 068_learner_schema_compatibility.sql | learner.service.ts | 168 | runtime |
| reputation_audit_log | 057_reputation_learning.sql | deadlock-detector.service.ts, load-test-harness.service.ts, reputation-learning.service.ts | 739 | runtime |
| reputation_impact_weights | 031_trust_reputation_ledger.sql | trust-reputation.service.ts | 0 | runtime |
| reputation_scores | 057_reputation_learning.sql | reputation-learning.service.ts, reputation-scale.service.ts | 213 | runtime |
| reputation_snapshots | 031_trust_reputation_ledger.sql | trust-reputation.service.ts | 0 | runtime |
| resolutions | 018_refoundation_canonical_schema.sql | self-modification-validator.service.ts | 0 | runtime |
| resource_allocation_history | 058_adaptive_strategy.sql | — | 0 | speculative |
| reward_audit | 025_goal_management_clean.sql | reward-calculator.service.ts | 0 | runtime |
| reward_calculations | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, eval-harness.service.ts, reward-calculator.service.ts | 2 | runtime |
| reward_functions | 025_goal_management_clean.sql | autonomy-orchestrator.service.ts, reward-calculator.service.ts | 1 | runtime |
| role_assignments | 079_identity_authority.sql | identity-authority.service.ts | 2 | runtime |
| role_permissions | 084_authority_chain.sql | identity-authority.service.ts | 6 | runtime |
| roles | 079_identity_authority.sql | calibration-change-governance.service.ts, calibration-constitution.service.ts, coalition-formation.service.ts | 6 | runtime |
| rulings | 109_judiciary.sql | judiciary.service.ts | 3 | runtime |
| saga_executions | 100_saga_coordinator.sql | saga-coordinator.service.ts | 2 | runtime |
| saga_steps | 100_saga_coordinator.sql | saga-coordinator.service.ts | 4 | runtime |
| search_query_history | 058_adaptive_strategy.sql | — | 0 | speculative |
| self_modification_validations | 097_self_modification_validation_compatibility.sql | civilization-runtime.service.ts, self-modification-validator.service.ts | 4 | runtime |
| service_identities | 079_identity_authority.sql | domain-registry.service.ts, evidence-registry.service.ts, evidence-vector-index.service.ts | 45 | runtime |
| shared_knowledge | 003_shared_knowledge.sql | civilization-runtime.service.ts, memory-store.service.ts | 2 | runtime |
| skill_canary_runs | 111_self_improvement_loop.sql | skill-canary.service.ts, skill-deployment.service.ts | 15 | runtime |
| skill_library_entries | 105_skill_library.sql | capability-expansion-gate.service.ts, proof-of-competence.service.ts, skill-deployment.service.ts | 24 | runtime |
| skill_library_versions | 105_skill_library.sql | capability-expansion-gate.service.ts, proof-of-competence.service.ts, skill-deployment.service.ts | 24 | runtime |
| skill_promotion_loop_runs | 108_skill_promotion_loop.sql | skill-promotion-loop.service.ts, skill-retrieval.service.ts | 19 | runtime |
| skill_usage_events | 110_skill_usage_events.sql | skill-retrieval.service.ts | 2 | runtime |
| society_disputes | 026_civilization_learning_entities.sql | trust-impact-assessment.service.ts | 0 | runtime |
| sources | 018_refoundation_canonical_schema.sql | adaptive-strategy.service.ts, autonomy-action-planner.service.ts, autonomy-orchestrator.service.ts | 0 | runtime |
| spans | 021_observability_traces.sql | observability.service.ts | 0 | runtime |
| specialist_allocation_history | 054_goal_hierarchies.sql | goal-hierarchy.service.ts | 0 | runtime |
| specialist_performance_history | 053_work_assignment_schema.sql | institution-work-assignment.service.ts | 0 | runtime |
| specialist_team_patterns | 054_goal_hierarchies.sql | goal-hierarchy.service.ts | 1 | runtime |
| specialists | 052b_institutions.sql | autonomy-civilization-bridge.service.ts, autonomy-metrics.service.ts, dynamic-calibration.service.ts | 0 | runtime |
| specialization_records | 057_reputation_learning.sql | — | 0 | speculative |
| strategy_pivots | 058_adaptive_strategy.sql | — | 0 | speculative |
| structured_logs | 021_observability_traces.sql | observability.service.ts | 0 | runtime |
| task_assignments | 058_adaptive_strategy.sql | — | 0 | speculative |
| trace_audit_events | 021_observability_traces.sql | calibration-constitution.service.ts, observability.service.ts | 0 | runtime |
| trace_contexts | 021_observability_traces.sql | calibration-change-governance.service.ts, observability.service.ts | 2 | runtime |
| trajectory_store | 023_autonomy_episodes.sql | eval-harness.service.ts, learner.service.ts, longitudinal-learning-harness.service.ts | 113 | runtime |
| trust_impact_assessments | 030_trust_impact_assessment.sql | trust-impact-assessment.service.ts | 0 | runtime |
| trust_policy_versions | 028_trust_policy_versions.sql | autonomy-orchestrator.service.ts, civilization-runtime.service.ts, trust-policy-canary.service.ts | 0 | runtime |
| trust_reputation_ledger | 031_trust_reputation_ledger.sql | persistent-trust-scorer.service.ts, trust-impact-assessment.service.ts, trust-reputation.service.ts | 3 | runtime |
| trust_scores | 009_trust_scores.sql | calibration-aware-routing.service.ts, civilization-runtime.service.ts, domain-registry.service.ts | 51 | runtime |
| work_cycle_events | 053_work_assignment_schema.sql | civilization-runtime.service.ts, institution-claim-vetting.service.ts, institution-work-assignment.service.ts | 61 | runtime |
| worker_leases | 022_autonomy_tasks.sql | crash-recovery.service.ts, task-engine.service.ts, worker-coordinator.service.ts | 2 | runtime |
| workflow_intents | 018_refoundation_canonical_schema.sql | — | 0 | speculative |
| workflow_tasks | 019_durable_execution.sql | civilization-runtime.service.ts, durable-execution.service.ts | 4 | runtime |
