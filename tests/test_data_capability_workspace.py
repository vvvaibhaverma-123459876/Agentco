from __future__ import annotations

from agentco_capability.tools import ToolDeniedError, execute_tool, summarize_csv


def test_csv_summary_produces_evaluator_checkable_calculation():
    summary = summarize_csv("name,value\nred,4\nblue,10\n")
    assert summary["row_count"] == 2
    assert summary["numeric_summary"]["value"]["mean"] == 7


def test_fixture_sql_allows_select_only():
    result = execute_tool("fixture_sql", {"rows": [{"value": 4}, {"value": 10}], "query": "select avg(value) as average from data"}, ["fixture_sql"])
    assert result["rows"][0]["average"] == 7.0


def test_fixture_sql_rejects_mutation():
    try:
        execute_tool("fixture_sql", {"rows": [{"value": 4}], "query": "delete from data"}, ["fixture_sql"])
    except ToolDeniedError as exc:
        assert "only permits SELECT" in str(exc) or "prohibited" in str(exc)
    else:
        raise AssertionError("data workspace accepted mutation")
