import json
from fastmcp import FastMCP
from analyzer import analyze_query_plan, suggest_indexes, check_pagination_safety

# Initialize the MCP server
mcp = FastMCP("DB-Performance-MCP")

@mcp.tool()
def analyze_query(connection_string: str, query: str) -> str:
    """
    Runs EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) on a target SQL query and returns execution bottlenecks.
    (PostgreSQL only).
    """
    result = analyze_query_plan(connection_string, query)
    return json.dumps(result, indent=2)

@mcp.tool()
def suggest_db_indexes(table_name: str, where_columns: list[str]) -> str:
    """
    Generates recommended CREATE INDEX CONCURRENTLY SQL statements based on filtered columns.
    """
    result = suggest_indexes(table_name, where_columns)
    return json.dumps(result, indent=2)

@mcp.tool()
def check_query_pagination(query: str) -> str:
    """
    Audits a query for unsafe OFFSET / LIMIT pagination on large tables and suggests alternatives.
    """
    result = check_pagination_safety(query)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
