import uuid

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple, Type, cast

import pytest, pytest_asyncio

from pgmcp.ag_edge import AgEdge
from pgmcp.ag_graph import AgGraph
from pgmcp.ag_properties import AgProperties
from pgmcp.ag_vertex import AgVertex
from pgmcp.apache_age import ApacheAGE
from pgmcp.db import AgtypeRecord, DbRecord


class TestApacheAGE:
    """Integration tests for ApacheAGE class using real database."""

    # ==================================================
    # Fixtures
    # ==================================================
    
    @pytest_asyncio.fixture
    async def unique_graph_name(self):
        """Fixture providing unique test graph name."""
        from pgmcp.royal_description import RoyalDescription
        return RoyalDescription.generate(4, delimiter='_')
    
    @pytest_asyncio.fixture
    async def apache_age(self, apache_age: ApacheAGE):
        """Fixture providing ApacheAGE instance."""
        return apache_age
    
    # ==================================================
    # Tests
    # ==================================================

    @pytest.mark.asyncio
    async def test_graph_exists_with_persisted_graph(self, apache_age: ApacheAGE, persisted_ag_graph: AgGraph):
        """Test graph_exists returns True for a graph that exists in the database."""
        assert await apache_age.graph_exists(persisted_ag_graph.name) is True, "The persisted graph should exist in the database."
        
    @pytest.mark.asyncio
    async def test_graph_exists_false_for_nonexistent(self, apache_age: ApacheAGE):
        """Test graph_exists returns False for non-existing graph."""
        assert await apache_age.graph_exists("non_existent_graph") is False, "The non-existent graph should not be found."

    @pytest.mark.asyncio
    async def test_create_and_drop_graph_lifecycle(self, apache_age: ApacheAGE, ag_graph: AgGraph, unique_graph_name: str):
        """Test complete graph lifecycle: create, verify exists, drop, verify gone."""
        new_name = unique_graph_name
        ag_graph.name = new_name
        
        # NOT EXISTS TO START
        assert await apache_age.graph_exists(ag_graph.name) is False, "Graph should not exist before creation."
        
        # CREATE
        await apache_age.create_graph(ag_graph.name)
        
        # CONFIRM EXISTS
        assert await apache_age.graph_exists(ag_graph.name), "Graph should exist after creation."
        
        # DROP
        await apache_age.drop_graph(ag_graph.name)
        
        # CONFIRM NOT EXISTS
        assert not await apache_age.graph_exists(ag_graph.name), "Graph should not exist after dropping."
        

    @pytest.mark.asyncio
    async def test_ensure_graph_creates_when_missing(self, apache_age: ApacheAGE, ag_graph: AgGraph, unique_graph_name: str):
        """Test ensure_graph creates graph when it doesn't exist."""
        new_name = unique_graph_name
        ag_graph.name = new_name
        
        assert await apache_age.graph_exists(ag_graph.name) is False, "Graph should not exist before ensure_graph is called."
        await apache_age.ensure_graph(ag_graph.name)
        assert await apache_age.graph_exists(ag_graph.name), "Graph should exist after ensure_graph is called."
        
    @pytest.mark.asyncio
    async def test_ensure_graph_creates_when_exists(self, apache_age: ApacheAGE, ag_graph: AgGraph, unique_graph_name: str):
        """Test ensure_graph creates graph when it doesn't exist."""
        new_name = unique_graph_name
        ag_graph.name = new_name
        
        await apache_age.create_graph(ag_graph.name) 
        assert await apache_age.graph_exists(ag_graph.name), "Graph should exist before ensure_graph is called."
        await apache_age.ensure_graph(ag_graph.name)
        assert await apache_age.graph_exists(ag_graph.name), "Graph should still exists after ensure_graph is called."
        


    @pytest.mark.asyncio
    async def test_get_graph_retrieves_existing_data(self, apache_age: ApacheAGE, persisted_ag_graph: AgGraph):
        """Test get_graph retrieves existing graph data."""
        graph = await apache_age.get_graph(persisted_ag_graph.name)
        assert isinstance(graph, AgGraph), "get_graph should return an AgGraph instance."
        assert graph.name == persisted_ag_graph.name, "Retrieved graph name should match persisted graph name."
        
        assert len(graph.vertices) > 0, "Graph should have vertices."
        
    
        
    
    @pytest.mark.asyncio
    async def test_patch_graph_using_context_manager(self, apache_age: ApacheAGE, contextmanager_patched_persisted_ag_graph: Tuple[AgGraph, AgGraph]):
        """Test patch_graph as async contextmanager test is done in fixture for later reused,
        just make sure the expected nodes and relationships are present for uncle fester"""
        
        base, patched = contextmanager_patched_persisted_ag_graph
        
        assert isinstance(patched, AgGraph),               "Patched graph should be an instance of AgGraph."
        assert patched.name == base.name,                  "Patched graph should have a different name than the base."
        assert len(patched.vertices) > len(base.vertices), "Patched graph should have more vertices than the base."
        assert len(patched.edges) > len(base.edges),       "Patched graph should have more edges than the base."

    @pytest.mark.asyncio
    async def test_patch_graph_using_awaitable_with_changes(self, apache_age: ApacheAGE, awaitable_patched_persisted_ag_graph: Tuple[AgGraph, AgGraph]):
        """Test patch_graph as awaitable with explicit changes."""
        
        base, patched = awaitable_patched_persisted_ag_graph
        
        assert isinstance(patched, AgGraph),               "Patched graph should be an instance of AgGraph."
        assert patched.name == base.name,                  "Patched graph should have a different name than the base."
        assert len(patched.vertices) > len(base.vertices), "Patched graph should have more vertices than the base."
        assert len(patched.edges) > len(base.edges),       "Patched graph should have more edges than the base."


# class TestApacheAGEEdgeCases:
#     """Test edge cases and error scenarios."""

#     @pytest_asyncio.fixture
#     async def apache_age(self):
#         """Fixture providing ApacheAGE instance."""
#         pass

#     @pytest.mark.asyncio
#     async def test_get_graph_nonexistent_raises_error(self, apache_age):
#         """Test get_graph raises appropriate error for non-existent graph."""
#         pass

#     @pytest.mark.asyncio
#     async def test_drop_nonexistent_graph_handles_gracefully(self, apache_age):
#         """Test dropping non-existent graph doesn't raise error."""
#         pass

#     @pytest.mark.asyncio
#     async def test_cypher_query_with_empty_result(self, apache_age, persisted_graph):
#         """Test cypher query that returns no results."""
#         pass


# class TestApacheAGEComplexOperations:
#     """Test complex database operations and workflows."""

#     @pytest_asyncio.fixture
#     async def apache_age(self):
#         """Fixture providing ApacheAGE instance."""
#         pass

#     @pytest.mark.asyncio
#     async def test_full_graph_operations_workflow(self, apache_age):
#         """Test complete workflow: create, populate, query, modify, verify."""
#         pass

#     @pytest.mark.asyncio
#     async def test_graph_with_multiple_labels_and_properties(self, apache_age):
#         """Test graph with diverse node types and rich properties."""
#         pass
