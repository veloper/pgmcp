# PGMCP: PostgreSQL Model Context Protocol

## Overview

PGMCP connects the `pgkeen` Docker image (with many AI/ML extensions pre-installed) to a mesh-based FastMCP backed server, bridging AI Agents with Apache AGE, low-level PostgreSQL administration, asynchronous crawling, knowledge base ingestion/curation, and more.

## Servers

### PgMCP Server (`server.py`)

This is the main FastMCP server acting as the main server for all of the sub-servers below. It provides a unified interface for managing the various components of the PGMCP ecosystem and it kept focused on its routing and composition role. All of the sub-server below are 'mount'ed to this server.

Each of the sub-servers henceforth fit under the umbrella of supporting `pgkeen` Postgresql -- leveraging its extensive collection of install extensions.


> [!INFO]  
> In the future these sub-servers may be spun off into their own FastMCP server projects.

### Apache AGE Server (`server_age.py`)

These tools provide an interface for AI Agents to manage multiple graphs in Apache AGE. It exposes tools for creating, updating, administering, and visualizing graphs.

| Tool Name               | Purpose/Description                                                                 | Arguments                                                                                   |
|-------------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `get_or_create_graph`   | Get or create a graph with the specified name.                                      | `graph_name: str`                                                                           |
| `list_graphs`           | List all graph names in the database.                                               |                                                                                             |
| `upsert_graph`          | Upsert both vertices and edges into the specified graph (deep merge).                | `graph_name: str`, `vertices: List[Dict[str, Any]]`, `edges: List[Dict[str, Any]]`          |
| `upsert_edge`           | Insert or update an edge's properties in a graph non-destructively.                 | `graph_name: str`, `label: str`, `edge_start_ident: str`, `edge_end_ident: str`, `properties: Dict[str, Any]` |
| `upsert_vertex`         | Insert or update a vertex's properties in a graph non-destructively.                | `graph_name: str`, `vertex_ident: str`, `label: str`, `properties: Dict[str, Any]`          |
| `drop_graphs`           | Drop one or more graphs by name.                                                    | `graph_names: List[str]`                                                                    |
| `drop_vertex`           | Remove a vertex by ident.                                                           | `graph_name: str`, `vertex_ident: str`                                                      |
| `drop_edge`             | Remove an edge by ident.                                                            | `graph_name: str`, `edge_ident: str`                                                        |
| `generate_visualization`| Generate a single-page HTML file visualizing a graph using vis.js and pyvis.        | `graph_name: str`                                                                           |


### Crawl Server (`server_crawl.py`)

These tools offer a unified interface for AI Agents to orchestrate, monitor, and analyze web crawling jobs with Scrapy and PostgreSQL, supporting the full job lifecycle as well as metadata and log management.

Scrapy's configuration is flexible and eventually exposable. Sensible defaults for local crawling are set for now. The toolset streamlines job management and delivers detailed insights into job execution and results.



| Tool Name            | Purpose/Description                                                                 | Arguments                              |
|----------------------|-------------------------------------------------------------------------------------|-------------------------------------------------------|
| `create_job`         | Define a new CrawlJob in an IDLE state.                                           | `start_urls: List[str]`, `depth: int = 3` |
| `start_job`          | Enqueue a CrawlJob by its ID to be run by the Scrapy engine.                      | `crawl_job_id: int`                       |
| `monitor_job`        | Follow a CrawlJob, reporting process to the client, for a max time.               | `crawl_job_id: int, timeout: float = 30.0` |
| `get_job`            | Get extra information about a specific CrawlJob by its ID.                        | `job_id: int`                             |
| `list_jobs`          | List all CrawlJobs and their metadata.                                            | `per_page: int = 15`, `page: int = 1`, `sort: str = None`, `order: str = None` |
| `get_job_logs`       | Get detailed logs for a specific CrawlJob by its ID.                              | `per_page: int = 15`, `page: int = 1`, `sort: str = None`, `order: str = None` |


### PSQL Server (`server_psql.py`)

This server provides a set of tools for low-level PostgreSQL administration, including executing SQL queries, managing extensions, and handling functions. It is designed to be used by AI Agents for advanced database management tasks.

> [!INFO] 
> Basic enforcement of SQL query safety is provided, but it is recommended to use these tools with caution, especially in production environments.


| Tool Name                        | Purpose/Description                                                      | Arguments                                                                                      |
|-----------------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `select`                         | Execute a SQL SELECT query and return rows.                              | `query: str`, `params: Dict[str, Any] = {}`                                                    |
| `delete`                         | Execute a SQL DELETE query.                                              | `query: str`, `params: Dict[str, Any] = {}`                                                    |
| `insert`                         | Execute a SQL INSERT query.                                              | `query: str`, `params: Dict[str, Any] = {}`                                                    |
| `update`                         | Execute a SQL UPDATE query.                                              | `query: str`, `params: Dict[str, Any] = {}`                                                    |
| `upsert`                         | Execute a SQL UPSERT (INSERT ... ON CONFLICT UPDATE) query.              | `query: str`, `params: Dict[str, Any] = {}`                                                    |
| `create_extension_if_not_exists`  | Create a PostgreSQL extension if it does not exist.                      | `extension_name: str`                                                                          |
| `create_or_replace_function`      | Create or replace a PostgreSQL function.                                 | `sql: str`                                                                                     |
| `drop_function`                   | Drop a PostgreSQL function by name.                                      | `function_name: str`                                                                           |
| `list_functions`                  | List all functions in the specified schema.                              | `schema: str = "public"`                                                                       |
| `http_request`                    | Make an HTTP request using the pg_http extension.                        | `url: str`, `method: str = "GET"`, `headers: Dict[str, str] = {}`, `body: Dict[str, Any] = {}` |


### Knowledge Base Server (`server_kb.py`) [*Work in Progress*]

These tools provide a unified interface for AI Agents to manage, curate, and ingest technical documentation and web content into a hierarchical knowledge base. The system supports corpus discovery, crawl job curation, and ingestion workflows, ensuring only high-quality, relevant documentation is added.

| Tool Name                  | Purpose/Description                                                                                      | Arguments                                                      |
|----------------------------|----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `find_corpus`              | Find a corpus by its name within the knowledge base.                                                     | `corpus_name: str`                                             |
| `ingest_crawl_job`         | Ingest curated CrawlItems from a CrawlJob into the knowledge base, following AI-driven curation.         | `crawl_job_id: int`                                            |
| `list_corpus`              | List all corpora in the knowledge base with pagination and sorting.                                     | `per_page: int = 15`, `page: int = 1`, `sort: str = None`, `order: str = None` |
| `get_or_create_corpus`     | Get or create a corpus with the specified name.                                                          | `corpus_name: str`                                            |
| `delete_corpus`            | Delete a corpus by its identifier.                                                                 | `corpus_id: int`                                               |
| `list_documents`           | List all documents in a corpus with pagination and sorting.                                           | `corpus_id: int`, `per_page: int = 15`, `page: int = 1`, `sort: str = None`, `order: str = None` |
| `get_document`             | Get a specific document by its identifier.                                                              | `document_id: int`                                             |
| `search_documents`         | Search for documents in a corpus using a query string.                                                  | `corpus_id: int`, `query: str`, `per_page: int = 15`, `page: int = 1`, `sort: str = None`, `order: str = None` |
| `create_document`          | Create a new document in a corpus.                                                                       | `corpus_id: int`, `title: str`, `content: str`               |

## Server Setup

1. Clone the repository:

    ```bash
    git clone <repository-url> /your/local/path/to/pgmcp
    ```

2. Navigate to the project directory:

    ```bash
    cd /your/local/path/to/pgmcp
    ```
3. Install the required dependencies:

    ```bash
    uv sync
    ```
4. Run the server:

    ```bash
    uv run pgmcp run --port 8000 --transport streamable-http
    ```

## Client Setup

### VSCODE
1. Open Command Palette (Cmd+Shift+P or Ctrl+Shift+P).
2. Select `MCP: Add Server...`
3. Choose "HTTP" option.
4. Enter the server URL (e.g., `http://localhost:8000/mcp/`).
5. Enter a "server id" (e.g., `pgmcp`).
6. Select `Global` for the scope.
7. Done. (It should appear in the `extensions` sidebar.)

### Roo / Cline / Claude MCP Setup
```json
{
  "mcpServers": {
    "pgmcp": {
      "url": "http://localhost:7999/mcp/",
      "type": "streamable-http",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```
