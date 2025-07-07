from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar

import pytest

from pgmcp.ag_edges import AgEdge
from pgmcp.ag_graph import AgGraph
from pgmcp.ag_mutation import AgMutation
from pgmcp.ag_patch import AgPatch
from pgmcp.ag_vertex import AgVertex
from pgmcp.server_age import ApacheAGE


T = TypeVar('T')
class MISSING:
    pass
@dataclass
class LazyFix(Generic[T]):
    """A functor that lazily evaluates a function to get a value for which it then serves on subsequent calls."""
    
    func: Callable[[], T]
    _result: T | MISSING = MISSING()
    def __call__(self) -> T:
        """Call the fixture to get the value."""
        if isinstance(self._result, MISSING):
            self._result = self.func()
        return self._result


# Test file for TestAgPatch

@pytest.fixture
def original_graph(ag_graph: AgGraph) -> AgGraph:
    """Returns a fresh AgGraph instance for patch tests."""
    return ag_graph


@pytest.fixture
def modifyable_graph(ag_graph: AgGraph) -> LazyFix[AgGraph]:
    """Returns a deepcopy of the `original_graph` for modification."""
    return LazyFix(func=lambda: ag_graph.deepcopy())

@pytest.fixture
def ag_patch(original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph]) -> LazyFix[AgPatch]:
    """Returns the result of AgPatch.from_a_to_b for `original_graph` and `modifyable_graph`."""
    return LazyFix(func=lambda: AgPatch.from_a_to_b(original_graph, modifyable_graph()))

class TestAgPatch:
    """
    Tests the ag_patch instance itself through the above three fixtures.
    Modify the `modifyable_graph` fixture to then assert on the results of the ag_patch() invocation's results.
    """

    def test_fixture_operations(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """ Should verify the basic operations of the ag_patch instance. """
        patch = ag_patch()
        assert isinstance(patch, AgPatch), "ag_patch should return a valid AgPatch instance"
        assert patch.graph_a == original_graph, "Patch graph_a does not match original_graph"
        assert patch.graph_b == modifyable_graph(), "Patch graph_b does not match modifyable_graph"


    def test_vertex_add(self, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when a vertex is added."""
        mod = modifyable_graph()
        
        # Making nodes the three way possible to do so.
        node1 = mod.add_vertex("Person", "larry", properties={ "name": "Larry Llama", })
        node2 = mod.add_vertex({ "label": "Person", "ident": "bob", "properties": { "name": "Bob Builder" } })
        node3 = mod.add_vertex(AgVertex.model_validate({ "label": "Person", "ident": "sally", "properties": { "name": "Sally Snake" } }))
        
        # Create the patch
        patch = ag_patch()
        mutations = patch.mutations
        assert isinstance(patch, AgPatch), "ag_patch should return a valid AgPatch instance"
        
        assert len(mutations) == 3, "There should be 3 mutations for the added vertices"
        for i, mutation in enumerate(mutations):
            assert mutation.is_vertex, f"Mutation {i} should be a vertex mutation, got {mutation}"
            assert mutation.is_addition, f"Mutation {i} should be an addition mutation, got {mutation}"

    def test_vertex_update(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when a vertex is updated."""
        # Setup the original graph to contain the prior 3 vertices
        original_graph.add_vertex("Person", "larry", properties={ "name": "Larry Llama" })
        original_graph.add_vertex("Person", "bob", properties={ "name": "Bob Builder" })
        original_graph.add_vertex("Person", "sally", properties={ "name": "Sally Snake" })



        mod = modifyable_graph()
        
        # Get Larry and confirm initial conditions
        larry = mod.vertices.get_by_ident("larry")
        assert larry is not None, "Larry vertex should exist in the modifyable graph"
        assert larry.properties.get("name") == "Larry Llama", "Larry's name should be 'Larry Llama' before update"
        
        
        # Update Larry's name
        larry.properties["name"] = "Larry Llama Updated"
        
        
        larry1 = mod.vertices.get_by_ident("larry")
        assert larry1 is not None, "Larry vertex should still exist after update"
        assert larry1.properties.get("name") == "Larry Llama Updated", "Larry's name should be 'Larry Llama Updated' after update"
        
        
        # Check the patch
        patch = ag_patch()
        assert patch is not None, "Patch should exist"
        assert len(patch.mutations) == 1, "There should be 1 mutation for the updated vertex"
        
        
        mutation = patch.mutations[0]
        assert isinstance(mutation, AgMutation), "Mutation should be an instance of AgMutation"
        assert mutation.is_vertex, "Mutation should be a vertex mutation"
        assert mutation.is_update, "Mutation should be an update mutation"
        assert mutation.ident == "larry", "Mutation should be for the 'larry' vertex"
        assert mutation.label == "Person", "Mutation should have label 'Person'"
        assert mutation.properties.get("name") == "Larry Llama Updated", "Mutation properties should reflect the updated name"

    def test_vertex_remove(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when a vertex is removed."""
        # Setup the original graph to contain the prior 3 vertices
        original_graph.add_vertex("Person", "larry", properties={ "name": "Larry Llama" })
        original_graph.add_vertex("Person", "bob", properties={ "name": "Bob Builder" })
        original_graph.add_vertex("Person", "sally", properties={ "name": "Sally Snake" })

        mod = modifyable_graph()
        
        # Remove Larry
        larry = mod.vertices.get_by_ident("larry")
        assert larry is not None, "Larry vertex should exist in the modifyable graph"
        
        mod.remove_vertex(larry)
        
        # Confirm Larry is removed
        larry1 = mod.vertices.get_by_ident("larry")
        assert larry1 is None, "Larry vertex should not exist after removal"
        
        # Check the patch
        patch = ag_patch()
        assert patch is not None, "Patch should exist"
        assert len(patch.mutations) == 1, "There should be 1 mutation for the removed vertex"
        
        mutation = patch.mutations[0]
        assert isinstance(mutation, AgMutation), "Mutation should be an instance of AgMutation"
        assert mutation.is_vertex, "Mutation should be a vertex mutation"
        assert mutation.is_removal, "Mutation should be a removal mutation"
        assert mutation.ident == "larry", "Mutation should be for the 'larry' vertex"

    def test_edge_add(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when an edge is added."""
        # Setup expected vertices in the original graph
        original_graph.add_vertex("Person", "larry", properties={ "name": "Larry Llama" })
        original_graph.add_vertex("Person", "bob", properties={ "name": "Bob Builder" })
        original_graph.add_vertex("Person", "sally", properties={ "name": "Sally Snake" })

        mod = modifyable_graph()
        

        # Add edges
        edge1 = mod.add_edge("KNOWS", "larry", "bob", properties={ "since": "2020-01-01" })
        edge2 = mod.add_edge({ "label": "KNOWS", "start_ident": "bob", "end_ident": "sally", "properties": { "since": "2021-01-01" } })
        edge3 = mod.add_edge(AgEdge.model_validate({ "label": "KNOWS", "start_ident": "sally", "end_ident": "larry", "properties": { "since": "2022-01-01" } }))
        
        # Confirm all edges have an `ident` set (automagically by AgGraph)
        assert edge1.ident is not None, "Edge 1 should have an ident"
        assert edge2.ident is not None, "Edge 2 should have an ident"
        assert edge3.ident is not None, "Edge 3 should have an ident"
        
        # Create the patch
        patch = ag_patch()
        assert patch is not None, "Patch should exist"
        assert len(patch.mutations) == 3, "There should be 3 mutations for the added edges"

        for mutation in patch.mutations:
            assert isinstance(mutation, AgMutation), "Mutation should be an instance of AgMutation"
            assert mutation.is_edge, "Mutation should be an edge mutation"
            assert mutation.is_addition, "Mutation should be an addition mutation"
            assert mutation.start_ident is not None, "Mutation should have a start_ident"
            assert mutation.end_ident is not None, "Mutation should have an end_ident"
            assert mutation.properties.get("since") is not None, "Mutation properties should have a 'since' field"


    def test_edge_update(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when an edge is updated."""
        # Setup the original graph with vertices and edges
        original_graph.add_vertex("Person", "larry", properties={ "name": "Larry Llama" })
        original_graph.add_vertex("Person", "bob", properties={ "name": "Bob Builder" })
        original_graph.add_vertex("Person", "sally", properties={ "name": "Sally Snake" })
        original_graph.add_edge("KNOWS", "larry", "bob", properties={ "since": "2020-01-01", "weight": 0.23 })
        original_graph.add_edge({ "label": "KNOWS", "start_ident": "bob", "end_ident": "sally", "properties": { "since": "2021-01-01", "weight": 0.5 } })
        original_graph.add_edge(AgEdge.model_validate({ "label": "KNOWS", "start_ident": "sally", "end_ident": "larry", "properties": { "since": "2022-01-01", "weight": 0.8 } }))

        mod = modifyable_graph()

        # Get the edge and confirm initial conditions
        edge = mod.edges.start_ident("larry").end_ident("bob").first()
        assert edge is not None, "Edge from larry to bob should exist in the modifyable graph"
        assert edge.properties.get("since") == "2020-01-01", "Edge 'since' property should be '2020-01-01' before update"
        assert edge.properties.get("weight") == 0.23, "Edge 'weight' property should be 0.23 before update"

        # Update edge properties
        edge.properties["since"] = "2022-02-02"
        edge.properties["weight"] = 0.97

        # Confirm update
        edge1 = mod.edges.start_ident("larry").end_ident("bob").first()
        assert edge1 is not None, "Edge from larry to bob should still exist after update"
        assert edge1.properties.get("since") == "2022-02-02", "Edge 'since' property should be updated"
        assert edge1.properties.get("weight") == 0.97, "Edge 'weight' property should be updated"

        # Check the patch
        patch = ag_patch()
        assert patch is not None, "Patch should exist"
        assert len(patch.mutations) == 1, "There should be 1 mutation for the updated edge"

        mutation = patch.mutations[0]
        assert isinstance(mutation, AgMutation), "Mutation should be an instance of AgMutation"
        assert mutation.is_edge, "Mutation should be an edge mutation"
        assert mutation.is_update, "Mutation should be an update mutation"
        assert mutation.start_ident == "larry", "Mutation should be for edge starting at 'larry'"
        assert mutation.end_ident == "bob", "Mutation should be for edge ending at 'bob'"
        assert mutation.label == "KNOWS", "Mutation should have label 'KNOWS'"
        assert mutation.properties.get("since") == "2022-02-02", "Mutation properties should reflect the updated 'since'"
        assert mutation.properties.get("weight") == 0.97, "Mutation properties should reflect the updated 'weight'"
        assert mutation.properties.get("start_ident") == "larry", "Mutation properties should have 'start_ident' set to 'larry'"
        assert mutation.properties.get("end_ident") == "bob", "Mutation properties should have 'end_ident' set to 'bob'"
        
        # get a fresh graph from the database, ensure that the edge has has its properties updated
        


    def test_edge_remove(self, original_graph: AgGraph, modifyable_graph: LazyFix[AgGraph], ag_patch: LazyFix[AgPatch]):
        """Should detect when an edge is removed."""
        # Setup the original graph with vertices and edges
        original_graph.add_vertex("Person", "larry", properties={ "name": "Larry Llama" })
        original_graph.add_vertex("Person", "bob", properties={ "name": "Bob Builder" })
        original_graph.add_vertex("Person", "sally", properties={ "name": "Sally Snake" })
        original_graph.add_edge("KNOWS", "larry", "bob", properties={ "since": "2020-01-01" })
        original_graph.add_edge({ "label": "KNOWS", "start_ident": "bob", "end_ident": "sally", "properties": { "since": "2021-01-01" } })
        original_graph.add_edge(AgEdge.model_validate({ "label": "KNOWS", "start_ident": "sally", "end_ident": "larry", "properties": { "since": "2022-01-01" } }))

        mod = modifyable_graph()

        # Remove the edge from larry to bob
        edge = mod.edges.start_ident("larry").end_ident("bob").first()
        assert edge is not None, "Edge from larry to bob should exist in the modifyable graph"
        
        mod.remove_edge(edge)
        
        # Confirm edge is removed
        edge1 = mod.edges.start_ident("larry").end_ident("bob").first()
        assert edge1 is None, "Edge from larry to bob should not exist after removal"

        # Check the patch
        patch = ag_patch()
        assert patch is not None, "Patch should exist"
        assert len(patch.mutations) == 1, "There should be 1 mutation for the removed edge"

        mutation = patch.mutations[0]
        assert isinstance(mutation, AgMutation), "Mutation should be an instance of AgMutation"
        assert mutation.is_edge, "Mutation should be an edge mutation"
        assert mutation.is_removal, "Mutation should be a removal mutation"
        assert mutation.start_ident == "larry", "Mutation should be for edge starting at 'larry'"
        assert mutation.end_ident == "bob", "Mutation should be for edge ending at 'bob'"
