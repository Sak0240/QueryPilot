import psycopg

from app.optimizer.sql_parser import parse_and_validate, SQLValidationError
from app.optimizer.explain_analyzer import get_plan, find_bottlenecks
from app.optimizer.schema_collector import collect_schema
from app.optimizer.llm_optimizer import get_suggestions, LLMError
from app.optimizer.safety_validator import (
    validate_candidate_sql,
    validate_index_suggestion,
)
from app.optimizer.result_comparator import results_match
from app.optimizer.benchmark import benchmark_candidate, benchmark_index
from app.optimizer.sql_parser import parse_and_validate
from app.optimizer.explain_analyzer import get_plan, find_bottlenecks
from app.optimizer.schema_collector import collect_schema
from app.optimizer.explain_analyzer import get_plan, find_bottlenecks, summarize_nodes

def analyze_query(conn, sql: str) -> dict:
    """Validate a query, then gather everything the AI will need.

    Raises SQLValidationError if the query is not allowed.
    `conn` must be a read-only connection.
    """
    # Step 1: the guard runs FIRST. Nothing touches the database before this passes.
    parsed = parse_and_validate(sql)

    # Step 2: use the cleaned-up SQL from the guard, not the raw user text.
    plan = get_plan(conn, parsed.sql)

    # Step 3: find slow patterns and collect the schema for the tables used.
    return {
        "sql": parsed.sql,
        "statement_type": parsed.statement_type,
        "tables": parsed.tables,
        "plan": plan,
        "bottlenecks": find_bottlenecks(plan),
        "schema": collect_schema(conn, parsed.tables),
    }
def optimize_query(ro_conn, admin_conn, sql: str, suggest=get_suggestions) -> dict:
    """Full pipeline: analyze, ask the model, validate, compare, benchmark.

    `suggest` can be replaced with a fake function to try this without the model.
    """
    analysis = analyze_query(ro_conn, sql)          # raises SQLValidationError if unsafe
    tables = analysis["tables"]
    original = analysis["sql"]
    existing = {
        idx["name"]
        for info in analysis["schema"].values()
        for idx in info["indexes"]
    }

    report = {
        "original_sql": original,
        "bottlenecks": analysis["bottlenecks"],
        "explanation": "",
        "candidate": None,        # rewritten query result
        "indexes": [],            # one entry per index suggestion
    }

    # Layer 4: ask the model
    try:
        suggestions = suggest(analysis)
    except LLMError as e:
        report["explanation"] = f"Model step failed: {e}"
        return report
    report["explanation"] = suggestions["explanation"]

    # Layers 5 and 6 for the rewritten query
    if suggestions["candidate_sql"]:
        entry = {"sql": suggestions["candidate_sql"], "accepted": False}
        try:
            cleaned = validate_candidate_sql(suggestions["candidate_sql"], tables)
            entry["sql"] = cleaned
            same, reason = results_match(ro_conn, original, cleaned)
            entry["validation"] = reason
            if same:
                plan_before = summarize_nodes(get_plan(ro_conn, original))
                plan_after = summarize_nodes(get_plan(ro_conn, cleaned))
                if plan_before == plan_after:
                    entry["validation"] = "Same execution plan as the original. No real change"
                else:
                    entry["accepted"] = True
                    entry["performance"] = benchmark_candidate(ro_conn, original, cleaned)
        except (SQLValidationError, psycopg.Error, ValueError) as e:
            entry["validation"] = f"Rejected: {e}"
        finally:
            ro_conn.rollback()      # clear any failed transaction state
        report["candidate"] = entry

    # Layers 5 and 6 for each index suggestion
    for index_sql in suggestions["index_suggestions"]:
        entry = {"sql": index_sql, "accepted": False}
        try:
            cleaned = validate_index_suggestion(index_sql, tables, existing)
            entry["sql"] = cleaned
            entry["performance"] = benchmark_index(admin_conn, original, cleaned)
            entry["accepted"] = True
            entry["validation"] = "Valid. Tested inside a transaction and rolled back"
        except (SQLValidationError, psycopg.Error) as e:
            entry["validation"] = f"Rejected: {e}"
        report["indexes"].append(entry)

    return report