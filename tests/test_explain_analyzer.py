import pytest

from app.optimizer.explain_analyzer import (
    get_plan,
    walk_plan,
    summarize_nodes,
    find_bottlenecks,
)


# ---------- Fast tests: a hand-made plan, no database needed ----------

FAKE_PLAN = {
    "Node Type": "Gather",
    "Total Cost": 100.0,
    "Plan Rows": 11,
    "Plans": [
        {
            "Node Type": "Seq Scan",
            "Relation Name": "t",
            "Total Cost": 90.0,
            "Plan Rows": 5,
            "Filter": "(a = 1)",
        }
    ],
}


def test_walk_plan_finds_child_nodes():
    types = [n["Node Type"] for n in walk_plan(FAKE_PLAN)]
    assert types == ["Gather", "Seq Scan"]


def test_summarize_nodes_fills_missing_fields_with_none():
    gather, scan = summarize_nodes(FAKE_PLAN)
    assert gather["table"] is None and gather["filter"] is None
    assert scan["table"] == "t" and scan["filter"] == "(a = 1)"


def test_seq_scan_with_filter_is_flagged():
    problems = find_bottlenecks(FAKE_PLAN)
    assert len(problems) == 1
    assert problems[0]["problem"] == "seq_scan_with_filter"


def test_seq_scan_without_filter_is_not_flagged():
    plan = {"Node Type": "Seq Scan", "Relation Name": "t",
            "Total Cost": 10.0, "Plan Rows": 100}
    assert find_bottlenecks(plan) == []


# ---------- Database tests: need Postgres running ----------

@pytest.mark.db
def test_get_plan_returns_top_node(ro_conn):
    plan = get_plan(ro_conn, "SELECT * FROM transactions WHERE user_id = 42")
    assert "Node Type" in plan


@pytest.mark.db
def test_unindexed_filter_is_flagged(ro_conn):
    plan = get_plan(ro_conn, "SELECT * FROM transactions WHERE user_id = 42")
    problems = find_bottlenecks(plan)
    assert len(problems) == 1
    assert problems[0]["table"] == "transactions"
    assert "user_id" in problems[0]["filter"]


@pytest.mark.db
def test_primary_key_lookup_is_not_flagged(ro_conn):
    plan = get_plan(ro_conn, "SELECT * FROM transactions WHERE id = 42")
    assert find_bottlenecks(plan) == []