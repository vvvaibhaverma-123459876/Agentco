from scripts.verify_migrations_native import build_report


def test_migration_report_fails_when_department_institution_column_missing():
    table_out = "\n".join(
        [
            "agent_task_events",
            "agent_tasks",
            "autonomy_goals",
            "decision_log",
            "departments",
            "institution_specialist_assignments",
            "institution_work_requests",
            "override_queue",
            "prediction_ledger",
            "specialist_allocation_history",
        ]
    )
    column_out = "\n".join(
        [
            "departments|authority_scope",
            "departments|entity_type",
            "departments|id",
            "departments|metadata",
            "departments|parent_id",
            "institution_work_requests|department_id",
            "institution_work_requests|id",
            "institution_work_requests|institution_id",
            "institution_work_requests|status",
            "institution_specialist_assignments|department_id",
            "institution_specialist_assignments|id",
            "institution_specialist_assignments|institution_id",
            "institution_specialist_assignments|specialist_role",
            "specialist_allocation_history|department_id",
            "specialist_allocation_history|id",
            "specialist_allocation_history|specialist_role",
            "specialist_allocation_history|work_request_id",
            "autonomy_goals|goal_depth",
            "autonomy_goals|goal_path",
            "autonomy_goals|id",
            "autonomy_goals|institution_id",
            "autonomy_goals|rollup_status",
        ]
    )

    report = build_report(
        migration_script="ts-node src/db/migrate.ts",
        conn_code=0,
        conn_out="agentco|agentco",
        table_code=0,
        table_out=table_out,
        column_code=0,
        column_out=column_out,
    )

    assert report["success"] is False
    assert report["core_schema_status"] == "missing"
    assert report["missing_columns"] == {"departments": ["institution_id"]}


def test_migration_report_accepts_runtime_required_schema():
    table_out = "\n".join(
        [
            "agent_task_events",
            "agent_tasks",
            "autonomy_goals",
            "decision_log",
            "departments",
            "institution_specialist_assignments",
            "institution_work_requests",
            "override_queue",
            "prediction_ledger",
            "specialist_allocation_history",
        ]
    )
    column_out = "\n".join(
        [
            "departments|authority_scope",
            "departments|entity_type",
            "departments|id",
            "departments|institution_id",
            "departments|metadata",
            "departments|parent_id",
            "institution_work_requests|department_id",
            "institution_work_requests|id",
            "institution_work_requests|institution_id",
            "institution_work_requests|status",
            "institution_specialist_assignments|department_id",
            "institution_specialist_assignments|id",
            "institution_specialist_assignments|institution_id",
            "institution_specialist_assignments|specialist_role",
            "specialist_allocation_history|department_id",
            "specialist_allocation_history|id",
            "specialist_allocation_history|specialist_role",
            "specialist_allocation_history|work_request_id",
            "autonomy_goals|goal_depth",
            "autonomy_goals|goal_path",
            "autonomy_goals|id",
            "autonomy_goals|institution_id",
            "autonomy_goals|rollup_status",
        ]
    )

    report = build_report(
        migration_script="ts-node src/db/migrate.ts",
        conn_code=0,
        conn_out="agentco|agentco",
        table_code=0,
        table_out=table_out,
        column_code=0,
        column_out=column_out,
    )

    assert report["success"] is True
    assert report["missing_tables"] == []
    assert report["missing_columns"] == {}
