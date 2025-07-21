import os

import pytest, pytest_asyncio

from fastmcp import Client, FastMCP

from pgmcp.server_crawl import mcp


# Set env to trick rich into thinking it's a much wider terminal
os.environ["COLUMNS"] = "140"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["TERM"] = "xterm-256color"

@pytest.fixture(scope="session")
def mcp_server() -> FastMCP:
    return mcp

@pytest.mark.asyncio
async def test_crawl_define_job(mcp_server: FastMCP):
    async with Client(mcp_server) as client:
        start_urls = ["https://docs.scrapy.org/en/latest"]
        depth = 3
        result = await client.call_tool("create_job", {"start_urls": start_urls, "depth": depth})
        
        # Test that the job was created successfully
        assert "Job defined successfully" in result.data["metadata"]["message"]
        assert result.data["record"]["start_urls"] == start_urls
        assert result.data["record"]["settings"]["DEPTH_LIMIT"] == depth
        
        # Verify the job was actually saved to the database
        assert result.data["record"]["id"] is not None
        assert result.data["record"]["created_at"] is not None
        assert result.data["record"]["updated_at"] is not None

@pytest.mark.asyncio
async def test_crawl_list_jobs(mcp_server: FastMCP):
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_jobs", {"per_page": 10, "page": 1})

        assert isinstance(result.data, dict)
        
        assert "metadata" in result.data
        assert "collection" in result.data
        
        assert isinstance(result.data["collection"], list)
        assert len(result.data["collection"]) > 0

        # Check if aggregate fields are included automatically
        first_job = result.data["collection"][0]
        
        # Verify aggregate fields are present
        assert 'log_count' in first_job, "log_count should be included in job data"
        assert 'item_count' in first_job, "item_count should be included in job data"
        
        # Verify aggregate values are integers (even if 0)
        assert isinstance(first_job['log_count'], int), "log_count should be an integer"
        assert isinstance(first_job['item_count'], int), "item_count should be an integer"
        
        # metadata should have count, page, and per_page
