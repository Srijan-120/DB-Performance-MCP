# Database Query & Index Performance Optimizer MCP Server

A lightweight Model Context Protocol (MCP) server written in Python using `FastMCP`. It provides LLM clients (Cursor, Claude Desktop, AntiGravity) with tools to analyze SQL queries, suggest indexes, and flag unpaginated large-table query risks.

## Features

- **Analyze Query Plan**: Connects to a PostgreSQL database, runs `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` inside a rolled-back transaction to safely detect performance bottlenecks like sequential scans.
- **Suggest Indexes**: Generates `CREATE INDEX CONCURRENTLY` DDL statements for a table given a list of commonly filtered columns.
- **Check Pagination Safety**: Audits query strings for `OFFSET / LIMIT` pagination that can degrade performance on large tables, suggesting keyset (cursor-based) alternatives.

## Prerequisites

- Python 3.11+
- PostgreSQL (if using the `analyze_query` tool)

## Installation

1. Clone this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

To start the MCP server, run:

```bash
python server.py
```

## Setup in Cursor

To use this MCP server in Cursor, you can add it to your Cursor MCP configuration.

1. Open Cursor Settings.
2. Go to **Features** > **MCP Servers**.
3. Add a new server with the following details:
   - **Name**: `DB-Performance-MCP`
   - **Type**: `command`
   - **Command**: `python /path/to/DB-Performance-MCP/server.py` (adjust the path appropriately)

## Docker Support

You can also run the server via Docker:

```bash
docker build -t db-performance-mcp .
docker run db-performance-mcp
```