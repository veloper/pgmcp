# PGMCP: PostgreSQL Model Context Protocol

## Overview

PGMCP connects the `pgkeen` Docker image (with many AI/ML extensions pre-installed) to a mesh-based FastMCP-backed server. It bridges AI Agents with Apache AGE, low-level PostgreSQL administration, asynchronous crawling, knowledge base ingestion/curation, and more.

## Servers

### PgMCP Server (`server.py`)

This is the main FastMCP server, acting as the central hub for all sub-servers listed below. It provides a unified interface for managing the various components of the PGMCP ecosystem and remains focused on its routing and composition role. All of the sub-servers below are mounted to this server.

Each sub-server is under the umbrella of supporting `pgkeen` PostgreSQL, leveraging its extensive collection of installable extensions.

> [!NOTE]  
> In the future, these sub-servers may be spun off into their own FastMCP server projects.

### Apache AGE Server (`server_age.py`)

These tools provide an interface for AI Agents to manage multiple graphs in Apache AGE. They expose tools for creating, updating, administering, and visualizing graphs.

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

### Knowledge Base Server (`server_kb.py`)

The Knowledge Base Server provides a unified interface for managing, curating, and ingesting technical documentation and web content into a hierarchical knowledge base. It supports corpus discovery, ingestion workflows, document management, embedding, and retrieval (RAG).


[crawl_to_kbase.webm](https://github.com/user-attachments/assets/0cae39ca-bde8-4f9f-a92f-2e4ed92d67f1)


| Tool Name           | Purpose/Description                                                                 | Arguments                                                                                                 |
|---------------------|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `ingest_crawl_job`  | Ingest a completed crawl job into the knowledge base as a new corpus.                | `crawl_job_id: int`                                                                                       |
| `embed_corpus`      | Embed all documents in a corpus to enable semantic search and retrieval.             | `corpus_id: int`                                                                                          |
| `rag`               | Search the knowledge base using RAG (Retrieval-Augmented Generation) with scoping.   | `query: str`, `corpus_id: List[int] \| None = None` , `documents_id: List[int] \| None = None`                |
| `list_corpora`      | List all corpora in the knowledge base.                                              | `per_page: int = 15`, `page: int = 1`, `sort: str = "id\|created_at\|updated_at\|name"`, `order: str = "asc\|desc"` |
| `destroy_corpus`    | Destroy a corpus and all its associated documents and chunks.                        | `corpus_id: int`                                                                                          |
| `list_documents`    | List all documents, or within a specific corpus.                                     | `corpus_id: int \| None = None`                                                                            |
| `destroy_document`  | Destroy a document by ID and all its associated chunks.                              | `document_id: int`                                                                                        |


### Crawl Server (`server_crawl.py`)

These tools offer a unified interface for AI Agents to orchestrate, monitor, and analyze web crawling jobs with Scrapy and PostgreSQL. They support the full job lifecycle as well as metadata and log management.

Scrapy's configuration is flexible and will eventually be exposable. Currently, sensible defaults are set for local crawling. The crawl toolset streamlines job management and provides detailed insights into job execution and results.

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

> [!NOTE] 
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
   You should see something like this:

    ```
    [07/30/25 14:32:54] INFO     Starting MCP server 'pgmcp' with transport 'streamable-http' on http://0.0.0.0:8000/mcp/
    INFO:     Started server process [13951]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    ```


## Client Setup

### VSCode
1. Open Command Palette (Cmd+Shift+P or Ctrl+Shift+P).
2. Select `MCP: Add Server...`
3. Choose "HTTP" option.
4. Enter the server URL (e.g., `http://localhost:8000/mcp/`).
5. Enter a "server id" (e.g., `pgmcp`).
6. Select `Global` for the scope.
7. Done. (It should appear in the `extensions` sidebar.)

### Roo / Cline / Claude
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
