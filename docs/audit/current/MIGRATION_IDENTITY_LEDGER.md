# Migration Identity Ledger

- Migration count: `129`
- Directory: `backend/src/db/migrations`

## Reused Sequence Contracts

- `51`: 051_fix_fk_constraints.sql, 051_team_activations.sql — legacy_parallel_sequence_before Batch 02 controls; lexicographic order is stable and both are already part of the audited baseline
- `58`: 058_adaptive_strategy.sql, 058_bounded_learning.sql — legacy_parallel_sequence_before Batch 02 controls; independent tables and stable lexicographic order
- `59`: 059_calibration_framework.sql, 059_governance_reputation_integration.sql — legacy_parallel_sequence_before Batch 02 controls; independent tables and stable lexicographic order
- `129`: 129_civilization_kernel.sql, 129_longitudinal_mission_evidence.sql — Batch 07 reconciliation contract: Version B preserved raw duplicate sequence; Version C treats full filename as stable ID, applies lexicographic order, and requires content-hash tracking

## Migrations

| Sequence | Stable ID | Content hash | Origin commit |
|---:|---|---|---|
| 1 | `001_agent_state.sql` | `adb9a2ae0a5f54d5` | `2bf252788ad5` |
| 2 | `002_agent_memory.sql` | `e80d491c31026c6f` | `2bf252788ad5` |
| 3 | `003_shared_knowledge.sql` | `24d87e400671decc` | `2bf252788ad5` |
| 4 | `004_decision_log.sql` | `beefb9e1ac6984c2` | `2bf252788ad5` |
| 5 | `005_event_history.sql` | `72716013716452cf` | `2bf252788ad5` |
| 6 | `006_prompt_registry.sql` | `f856751509485962` | `2bf252788ad5` |
| 7 | `007_performance_metrics.sql` | `97f24b12db99a7b7` | `2bf252788ad5` |
| 8 | `008_customer_data.sql` | `c5518e5fc0c6a20f` | `2bf252788ad5` |
| 9 | `009_trust_scores.sql` | `1829e6342b49f9b7` | `0e14f1e71c04` |
| 10 | `010_beliefs.sql` | `5f77a216250b69e5` | `0e14f1e71c04` |
| 11 | `011_prediction_ledger.sql` | `6586155263954b31` | `12a0fa446aa4` |
| 12 | `012_decision_log_chain.sql` | `9707338b91149c8f` | `75fcf09e39c8` |
| 13 | `013_override_queue.sql` | `78502180cdfb5748` | `75fcf09e39c8` |
| 14 | `014_decision_log_immutability_triggers.sql` | `9cd7299b0f481959` | `75fcf09e39c8` |
| 15 | `015_agent_memories.sql` | `6316d41ce98faf1e` | `44f25ed8ca13` |
| 16 | `016_resolution_service_role.sql` | `767b3647aece057f` | `0548de116d56` |
| 17 | `017_agent_memories_lifecycle.sql` | `9aaa72de10b028d1` | `3783cc138bed` |
| 18 | `018_refoundation_canonical_schema.sql` | `b657263ec370e4a3` | `b34f009ef8ce` |
| 19 | `019_durable_execution.sql` | `90b62817f9f1720f` | `b34f009ef8ce` |
| 21 | `021_observability_traces.sql` | `54942adc4645100e` | `e7da371fcf4f` |
| 22 | `022_autonomy_tasks.sql` | `b2433c19d31b769f` | `e7da371fcf4f` |
| 23 | `023_autonomy_episodes.sql` | `8669b598fd849f2b` | `e7da371fcf4f` |
| 24 | `024_perception_infrastructure.sql` | `8160dcfb98c8673c` | `e7da371fcf4f` |
| 25 | `025_goal_management_clean.sql` | `5861fe205b1196cc` | `0d9ccc14f70d` |
| 26 | `026_civilization_learning_entities.sql` | `ce3b049cafb65ef2` | `0c98c13e315a` |
| 27 | `027_calibration_constitution.sql` | `920ae3ffcf067042` | `9f64e618bf64` |
| 28 | `028_trust_policy_versions.sql` | `2b4a6856b8ccf7a0` | `b659bf51d2dc` |
| 29 | `029_calibration_change_requests.sql` | `7acca1af24173da4` | `f4d92b1fb047` |
| 30 | `030_trust_impact_assessment.sql` | `2f915085d0d54828` | `e004309d2f5d` |
| 31 | `031_trust_reputation_ledger.sql` | `b74c425cb1f0f0d2` | `012a1b7137bc` |
| 32 | `032_calibration_drift_monitor.sql` | `d459e11e03434492` | `3f0254770013` |
| 33 | `033_artifacts.sql` | `b2d6d305552d92e9` | `75b06063b65d` |
| 34 | `034_learner_infrastructure.sql` | `7f83e4060f30a5bc` | `590a906a7324` |
| 40 | `040_governance_rbac.sql` | `0ec1ba357ecab118` | `86b39c53a024` |
| 50 | `050_autonomy_action_loop.sql` | `7037848105c4f63a` | `7fbf7e7b0fb3` |
| 51 | `051_fix_fk_constraints.sql` | `b2434750b9b217a3` | `13cb51974055` |
| 51 | `051_team_activations.sql` | `d6f91160e2ada005` | `b20798a003fc` |
| 52 | `052_specialist_http_endpoint.sql` | `13598984be6bbcb7` | `b20798a003fc` |
| None | `052b_institutions.sql` | `c3559d8da5f3a662` | `aaf0ea1641e4` |
| 53 | `053_work_assignment_schema.sql` | `77f76a3651d3cba3` | `212ebabad0e6` |
| 54 | `054_goal_hierarchies.sql` | `6180db0b189dfd9d` | `939281c1beb4` |
| 55 | `055_deadlock_prevention.sql` | `78ce7f8e007feb12` | `0684432a1e4c` |
| 56 | `056_production_deployment.sql` | `f285732142ce51f2` | `8655b69c3238` |
| 57 | `057_reputation_learning.sql` | `4c37110e0c8e3c8c` | `57d245a9874c` |
| 58 | `058_adaptive_strategy.sql` | `1b579944431c5115` | `57d245a9874c` |
| 58 | `058_bounded_learning.sql` | `681b6746ec43e13e` | `fbe3918be729` |
| 59 | `059_calibration_framework.sql` | `1577b274efd9e356` | `4715852450fb` |
| 59 | `059_governance_reputation_integration.sql` | `c3cb9e4c9cb4a3a4` | `6cccb037df72` |
| 60 | `060_coalition_formation.sql` | `bbca13e398e8b57d` | `6cccb037df72` |
| 61 | `061_add_goal_depth_column.sql` | `a6a96b56e9f9ecd6` | `36899f75c9b0` |
| 62 | `062_runtime_schema_compatibility.sql` | `61f5c261845df506` | `aa5e6c334cda` |
| 63 | `063_runtime_schema_compatibility_followup.sql` | `82def716b358e9b0` | `aa5e6c334cda` |
| 64 | `064_department_reputation_score.sql` | `d5fe1582e3b724df` | `aa5e6c334cda` |
| 65 | `065_reputation_audit_compatibility.sql` | `de2fd3ce9fd9957c` | `aa5e6c334cda` |
| 66 | `066_reward_schema_compatibility.sql` | `1c5d32adb2253df1` | `aa5e6c334cda` |
| 67 | `067_reward_legacy_defaults.sql` | `fece078d223daba7` | `aa5e6c334cda` |
| 68 | `068_learner_schema_compatibility.sql` | `e8c1da9954e7f7dc` | `aa5e6c334cda` |
| 69 | `069_trajectory_success_compatibility.sql` | `1ec084550f48b9fc` | `aa5e6c334cda` |
| 70 | `070_eval_schema_compatibility.sql` | `66ad7e7806cb77dc` | `aa5e6c334cda` |
| 71 | `071_eval_run_timestamp_default.sql` | `912b148498cca246` | `aa5e6c334cda` |
| 72 | `072_specialist_schema_compatibility.sql` | `cfdefe3ff9cc0206` | `aa5e6c334cda` |
| 73 | `073_evidence_content_text.sql` | `e6a00ebc3cc5955d` | `ec06e0b4a073` |
| 74 | `074_governance_coalition_formations.sql` | `2929f6ee444d1e4c` | `86193656494a` |
| 75 | `075_agent_tasks_canonical_view.sql` | `895bbacb2dfacc5e` | `c3cbfabe0086` |
| 76 | `076_build_ledger.sql` | `0097222b92784f4d` | `389da5c5e9b8` |
| 77 | `077_civilization_vertical_slice.sql` | `63aabd8d186abde5` | `e938a634d755` |
| 78 | `078_agent_membership_id_compatibility.sql` | `b946de2cb16d9c75` | `e938a634d755` |
| 79 | `079_identity_authority.sql` | `530c85bcd252544c` | `c79f12674fa2` |
| 80 | `080_event_log.sql` | `6eb2460a4e6d4d9f` | `69469e6dad5b` |
| 81 | `081_resource_ledger.sql` | `0a887a1f1e807337` | `58683b35b4d1` |
| 82 | `082_resource_reservations.sql` | `b66205bf799b06ac` | `bd1f4a5707dd` |
| 83 | `083_transactional_outbox.sql` | `d65797783a11c8ca` | `a9c45607e9a0` |
| 84 | `084_authority_chain.sql` | `ffdca49e4c378721` | `b86ff333f755` |
| 85 | `085_authority_chain_decision_actor_compatibility.sql` | `7f35560a7029ee56` | `b86ff333f755` |
| 86 | `086_key_ring.sql` | `ab6755e6c0307a77` | `fcfb1ce8e531` |
| 87 | `087_hash_chain_anchors.sql` | `3ed2922677df92e5` | `009cde52e02b` |
| 88 | `088_evidence_registry_events.sql` | `65ba045eb50e3ae3` | `1e1b0a0a88d3` |
| 89 | `089_department_institution_compatibility.sql` | `bbc313706ebae3ec` | `95757385b0e4` |
| 90 | `090_department_parent_type_compatibility.sql` | `0c7fb0ebe92c2a2c` | `95757385b0e4` |
| 91 | `091_department_institution_trigger_restore.sql` | `31ec16499cfffa61` | `95757385b0e4` |
| 92 | `092_agent_task_events_canonical_view.sql` | `6bcd01f688423fe5` | `95757385b0e4` |
| 93 | `093_resolution_service_role_grant_repair.sql` | `acc198d6df386b0b` | `69394a993b41` |
| 94 | `094_prediction_ledger_hardness_compatibility.sql` | `4448081dbbf9121f` | `69394a993b41` |
| 95 | `095_prediction_ledger_reserve_fields_compatibility.sql` | `1a4d9424685ac494` | `69394a993b41` |
| 96 | `096_idempotency_store.sql` | `ef0b89559c5bd213` | `69394a993b41` |
| 97 | `097_self_modification_validation_compatibility.sql` | `854d8ceef2e8c925` | `69394a993b41` |
| 98 | `098_governance_kill_switch.sql` | `ea6349806e7171d9` | `69394a993b41` |
| 99 | `099_trajectory_simulation_compatibility.sql` | `f9166a0b73154cff` | `69394a993b41` |
| 100 | `100_saga_coordinator.sql` | `40c7ea68835f77f9` | `69394a993b41` |
| 101 | `101_evidence_vector_index.sql` | `9aa6a1c0c10d9d51` | `69394a993b41` |
| 102 | `102_domain_registry.sql` | `66f484ea8a1d6d15` | `69394a993b41` |
| 103 | `103_generality_metric_tracker.sql` | `73672768002bb4c8` | `69394a993b41` |
| 104 | `104_candidate_regression_tests.sql` | `4d925b5f27653ef2` | `69394a993b41` |
| 105 | `105_skill_library.sql` | `abdc3e5ee4854ec9` | `bea00fbf7040` |
| 106 | `106_proof_of_competence.sql` | `a79c087df95a7fcf` | `bea00fbf7040` |
| 107 | `107_capability_expansion_gate.sql` | `6060624afd87cc7b` | `bea00fbf7040` |
| 108 | `108_skill_promotion_loop.sql` | `d1289dd53078df92` | `bea00fbf7040` |
| 109 | `109_judiciary.sql` | `f500fd22257239aa` | `bea00fbf7040` |
| 110 | `110_skill_usage_events.sql` | `43d209f112b9aba6` | `6e5eab446e6c` |
| 111 | `111_self_improvement_loop.sql` | `c32b4215104010ae` | `c21803276ea3` |
| 112 | `112_fix_goal_completion_metric_uuid.sql` | `55250346749f9da5` | `e5c7d7ab2cbb` |
| 113 | `113_institutional_knowledge_promotions.sql` | `2a992788e5aadbe9` | `071959f38f36` |
| 114 | `114_self_memory_retrievable.sql` | `a207f86e8336512f` | `23645bab44d2` |
| 115 | `115_autonomous_promotions.sql` | `a143723cd8fb93af` | `a787770d9e80` |
| 116 | `116_persistent_agents.sql` | `f18a7927e71078cf` | `f60c22e688b8` |
| 117 | `117_artifact_lineage_identity.sql` | `859b58652216218a` | `cfb9870c5555` |
| 118 | `118_contradictions_and_demotions.sql` | `e0000c7d568c9509` | `32429da8b6a6` |
| 119 | `119_source_relevance.sql` | `fc7a7d0278223e1e` | `4b3d4a2d4525` |
| 120 | `120_prediction_ledger_registration_invariants.sql` | `e9cb5c22c2cb57a9` | `69394a993b41` |
| 121 | `121_runtime_schema_drift_repairs.sql` | `e85e55a45e942a7f` | `c26d4f6ec6f7` |
| 122 | `122_reward_schema_drift_repairs.sql` | `b1e17f7bccdf3622` | `c26d4f6ec6f7` |
| 123 | `123_reward_calculation_schema_drift_repairs.sql` | `6203538e7707fda1` | `c26d4f6ec6f7` |
| 124 | `124_eval_schema_drift_repairs.sql` | `0e73db82d917a6f4` | `c26d4f6ec6f7` |
| 125 | `125_decision_log_protocol_version.sql` | `efd7af2253e02bad` | `bdfab886b6ef` |
| 126 | `126_decision_log_attempt_id.sql` | `d3421b1b5324f9ed` | `9636eb382b21` |
| 127 | `127_runtime_governance_artifacts.sql` | `2d8b26dee8ed6f9f` | `84c382f4ba8e` |
| 128 | `128_event_bus_outbox.sql` | `d2ef6ca40bbc8a33` | `8216f493b319` |
| 129 | `129_civilization_kernel.sql` | `8f64e6d2b1c40fbd` | `b693aaf36b95` |
| 129 | `129_longitudinal_mission_evidence.sql` | `382c99634e6f87fe` | `b0bad61da280` |
| 130 | `130_citizenship.sql` | `b95ce86ac9f9f744` | `ec168d271e9e` |
| 131 | `131_societies_and_institution_charters.sql` | `52a2f3a1049147fe` | `37b9e8c6f3bf` |
| 132 | `132_institution_coalitions.sql` | `300e56299083c1f8` | `37b9e8c6f3bf` |
| 133 | `133_missions.sql` | `ef7f08dbbf206c65` | `4c7a2e47cad6` |
| 134 | `134_civilization_economy.sql` | `5b07422d439a98ba` | `bc86859d09b1` |
| 135 | `135_governance.sql` | `c84b7b96f91b1d20` | `aea45a95027e` |
| 136 | `136_judiciary.sql` | `d8209f81dcb95f5a` | `a2cc3f652f1f` |
| 137 | `137_collective_epistemics.sql` | `2e8f5b628748b851` | `6a0806dd45a0` |
| 138 | `138_safe_evolution.sql` | `669cbeb3b1f2e5e4` | `4cea7ad642d0` |
| 139 | `139_capability_expansion.sql` | `269da9571bc96d27` | `75406a50882a` |
