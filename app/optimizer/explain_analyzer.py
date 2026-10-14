def get_plan(conn, sql: str) -> dict:
    """Ask Postgres how it would run the query (does NOT run the query)."""
    row = conn.execute(f"EXPLAIN (FORMAT JSON) {sql}").fetchone()
    return row[0][0]["Plan"]


def walk_plan(node: dict) -> list[dict]:
    """Return a flat list of every node in the plan tree."""
    nodes = [node]
    for child in node.get("Plans", []):
        nodes.extend(walk_plan(child))
    return nodes


def summarize_nodes(plan: dict) -> list[dict]:
    """Keep only the fields we care about from each node."""
    return [
        {
            "type": n["Node Type"],
            "table": n.get("Relation Name"),
            "rows": n.get("Plan Rows"),
            "cost": n.get("Total Cost"),
            "filter": n.get("Filter"),
        }
        for n in walk_plan(plan)
    ]

def find_bottlenecks(plan: dict) -> list[dict]:
    """Look for slow patterns in the plan and describe each one."""
    problems = []
    for node in summarize_nodes(plan):
        if node["type"] == "Seq Scan" and node["filter"]:
            problems.append({
                "problem": "seq_scan_with_filter",
                "table": node["table"],
                "filter": node["filter"],
                "estimated_rows": node["rows"],
                "cost": node["cost"],
                "hint": f"Consider an index to support: {node['filter']}",
            })
    return problems