from app.optimizer.prompts import build_user_prompt, SYSTEM_PROMPT

FAKE_ANALYSIS = {
    "sql": "SELECT * FROM t WHERE a = 1",
    "plan": {"Node Type": "Seq Scan", "Relation Name": "t",
             "Total Cost": 10.0, "Plan Rows": 5, "Filter": "(a = 1)"},
    "bottlenecks": [{"problem": "seq_scan_with_filter"}],
    "schema": {"t": {
        "columns": [{"name": "a", "type": "integer", "nullable": False}],
        "indexes": [{"name": "t_pkey", "definition": "CREATE UNIQUE INDEX t_pkey ON t (a)"}],
    }},
}


def test_prompt_contains_sql_schema_and_index():
    p = build_user_prompt(FAKE_ANALYSIS)
    assert "SELECT * FROM t WHERE a = 1" in p
    assert "Table t(a integer)" in p
    assert "t_pkey" in p


def test_prompt_contains_bottleneck():
    assert "seq_scan_with_filter" in build_user_prompt(FAKE_ANALYSIS)


def test_system_prompt_demands_json():
    assert "JSON only" in SYSTEM_PROMPT