import psycopg2
import json
import re

def execute_explain_analyze(connection_string: str, query: str) -> dict:
    """
    Executes an EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) on the given query.
    To prevent accidental data modification on INSERT/UPDATE/DELETE queries,
    we execute this inside a transaction and rollback.
    """
    if not query.strip():
        return {"error": "Empty query provided"}
        
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
    
    try:
        # We use a context manager for the connection
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(explain_query)
                    result = cur.fetchone()
                    # We roll back anyway to prevent accidental data modifications
                    conn.rollback()
                    
                    if result and len(result) > 0:
                        plan_json = result[0]
                        return {"status": "success", "plan": plan_json}
                    else:
                        return {"status": "error", "message": "No output returned from EXPLAIN"}
                except Exception as e:
                    conn.rollback()
                    return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {e}"}

def parse_explain_output(plan_json: list) -> dict:
    """
    Parses the JSON output of EXPLAIN to find bottlenecks.
    """
    if not plan_json or not isinstance(plan_json, list):
         return {"error": "Invalid plan format"}
         
    plan = plan_json[0].get("Plan", {})
    execution_time = plan_json[0].get("Execution Time", 0.0)
    planning_time = plan_json[0].get("Planning Time", 0.0)
    
    seq_scans = []
    
    def traverse_plan(node):
        node_type = node.get("Node Type")
        if node_type == "Seq Scan":
            seq_scans.append({
                "table": node.get("Relation Name", "Unknown"),
                "cost": node.get("Total Cost", 0),
                "rows_removed_by_filter": node.get("Rows Removed by Filter", 0)
            })
            
        if "Plans" in node:
            for child in node["Plans"]:
                traverse_plan(child)
                
    traverse_plan(plan)
    
    return {
        "execution_time_ms": execution_time,
        "planning_time_ms": planning_time,
        "bottlenecks": {
            "sequential_scans": seq_scans
        },
        "flags": {
            "high_disk_io": any(scan.get("cost", 0) > 1000 for scan in seq_scans), # Arbitrary threshold for flagging
            "missing_index_risk": len(seq_scans) > 0
        }
    }


def analyze_query_plan(connection_string: str, query: str) -> dict:
    """Main function to analyze query plan."""
    result = execute_explain_analyze(connection_string, query)
    if result.get("status") == "success":
        plan_json = result.get("plan")
        summary = parse_explain_output(plan_json)
        return summary
    else:
        return result


def suggest_indexes(table_name: str, where_columns: list[str]) -> dict:
    """
    Generates recommended CREATE INDEX CONCURRENTLY statements.
    """
    if not table_name or not where_columns:
        return {"error": "table_name and where_columns are required"}
        
    cols_csv = ", ".join(where_columns)
    idx_name = f"idx_{table_name}_{'_'.join(where_columns)}"
    
    # basic heuristic impact score
    impact_score = "High" if len(where_columns) <= 3 else "Medium"
    
    ddl = f"CREATE INDEX CONCURRENTLY {idx_name} ON {table_name} ({cols_csv});"
    
    return {
        "table": table_name,
        "columns": where_columns,
        "recommended_ddl": ddl,
        "estimated_impact": impact_score,
        "note": "Ensure CONCURRENTLY is supported and run outside a transaction block if using Postgres."
    }

def check_pagination_safety(query: str) -> dict:
    """
    Audits a query for unsafe OFFSET / LIMIT pagination.
    """
    if not query:
        return {"error": "Empty query"}
        
    # very naive regex checking
    has_limit = re.search(r'\bLIMIT\b\s+\d+', query, re.IGNORECASE)
    has_offset = re.search(r'\bOFFSET\b\s+\d+', query, re.IGNORECASE)
    
    if has_offset and has_limit:
        status = "Unsafe (OFFSET pagination detected)"
        suggestion = "Use keyset (cursor-based) pagination for large tables (e.g., WHERE id > last_seen_id LIMIT X)."
        refactor = "SELECT * FROM ... WHERE cursor_column > ? ORDER BY cursor_column LIMIT ?"
        return {
            "safety_status": status,
            "issue": "OFFSET pagination becomes increasingly slow as the offset grows because the database must scan and discard all rows prior to the offset.",
            "suggestion": suggestion,
            "refactored_snippet": refactor
        }
    elif has_offset:
        return {
            "safety_status": "Warning",
            "issue": "OFFSET without LIMIT is unusual and generally unsafe for large datasets."
        }
    else:
        return {
            "safety_status": "Safe",
            "issue": "No OFFSET pagination detected."
        }
