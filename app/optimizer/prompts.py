import json

from app.optimizer.explain_analyzer import summarize_nodes

SYSTEM_PROMPT = """You are a PostgreSQL query optimization assistant.
You receive one SQL query, its EXPLAIN plan nodes, detected bottlenecks, and the
schema (columns and existing indexes) of the tables it uses.

Rules:
- Use only tables and columns that appear in the schema. Never invent any.
- candidate_sql must be ONE read-only SELECT that returns exactly the same
  rows and columns as the original. If you cannot improve the query itself,
  set candidate_sql to null.
- index_suggestions must be CREATE INDEX statements only. Do not suggest an
  index that already exists in the schema.
- Keep the explanation under 80 words.

Answer with JSON only, no markdown, in exactly this shape:
{
  "explanation": "why the query is slow and what you changed",
  "candidate_sql": "SELECT ..." or null,
  "index_suggestions": ["CREATE INDEX ..."]
}"""


def build_user_prompt(analysis: dict) -> str:
    """Turn the output of analyze_query into a compact prompt."""
    # Compact schema: one line per column, plus index definitions
    schema_lines = []
    for table, info in analysis["schema"].items():
        cols = ", ".join(f"{c['name']} {c['type']}" for c in info["columns"])
        schema_lines.append(f"Table {table}({cols})")
        for idx in info["indexes"]:
            schema_lines.append(f"  Index: {idx['definition']}")

    return "\n".join([
        "SQL:",
        analysis["sql"],
        "",
        "Schema:",
        *schema_lines,
        "",
        "Plan nodes (top to bottom):",
        json.dumps(summarize_nodes(analysis["plan"])),
        "",
        "Bottlenecks:",
        json.dumps(analysis["bottlenecks"]),
    ])