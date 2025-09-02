# PGMCP: PostgreSQL Model Context Protocol

## Overview

PGMCP connects the `pgkeen` Postgres Docker image to a mesh-based FastMCP-backed server. It bridges AI Agents with low-level PostgreSQL administration, asynchronous crawling, knowledge base ingestion/curation/search, and more.

## Servers

### PGMCP Server (`server.py`)

The main FastMCP server that acts as the hub for all sub-servers listed below. It provides a unified interface interacting with each sub-server and focuses on routing and tool composition. Each of the sub-servers are mounted onto this server.

### Knowledge Base Server (`server_kb.py`)

A concise interface for ingesting, curating, and semantically searching technical documentation and web content across multiple corpora. Features include corpus discovery, ingestion pipelines, document chunking, embedding, and RAG-based retrieval.


[crawl_to_kbase.webm](https://github.com/user-attachments/assets/0cae39ca-bde8-4f9f-a92f-2e4ed92d67f1)


| Tool Name           | Purpose/Description                                                                 | Arguments                                                                                                 |
|---------------------|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `rag`               | Search the knowledge base using RAG (Retrieval-Augmented Generation) with scoping.   | `query: str`, `corpus_id: List[int] \| None = None` , `documents_id: List[int] \| None = None`                |
| `ingest_crawl_job`  | Ingest a completed crawl job into the knowledge base as a new corpus.                | `crawl_job_id: int`                                                                                       |
| `embed_corpus`      | Embed all documents in a corpus to enable semantic search and retrieval.             | `corpus_id: int`                                                                                          |
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
> Basic enforcement of SQL query type safety is provided, but it is recommended to use these tools with caution, and never in production environments.


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
