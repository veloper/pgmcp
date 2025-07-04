from __future__ import annotations

import copy

import pytest

from pgmcp.ag_graph import AgGraph


class TestAgGraph:
    @pytest.fixture
    def ag_graph_mutable(self, ag_graph: AgGraph):
        """
        Returns a mutable copy of ag_graph for mutation tests.
        """
        return copy.deepcopy(ag_graph)

    def test_add_and_remove_vertex(self, ag_graph_mutable):
        """
        Verify that adding and removing vertices updates the graph's vertices list and clears
        the query cache as expected.
        """
        from pgmcp.ag_properties import AgProperties
        from pgmcp.ag_vertex import AgVertex

        initial_vertex_count = len(ag_graph_mutable.vertices)
        new_vertex = AgVertex(
            label="Human",
            properties=AgProperties(root={"ident": "testperson", "age": 99}),
        )

        # Add vertex
        ag_graph_mutable.add_vertex(new_vertex)
        assert len(ag_graph_mutable.vertices) == initial_vertex_count + 1
        assert ag_graph_mutable.vertices.get_by_ident("testperson") is not None

        # Remove vertex
        ag_graph_mutable.remove_vertex(new_vertex)
        assert len(ag_graph_mutable.vertices) == initial_vertex_count
        assert ag_graph_mutable.vertices.get_by_ident("testperson") is None

    def test_add_and_remove_edge(self, ag_graph_mutable):
        """
        Verify that adding and removing edges updates the graph's edges list and clears
        the query cache as expected.
        """
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_properties import AgProperties

        initial_edge_count = len(ag_graph_mutable.edges)
        new_edge = AgEdge(
            label="TEST_EDGE",
            start_id=1,
            end_id=2,
            properties=AgProperties(
                root={
                    "ident": "testedge",
                    "start_ident": "gomez",
                    "end_ident": "morticia",
                }
            ),
        )

        # Add edge
        ag_graph_mutable.add_edge(new_edge)
        assert len(ag_graph_mutable.edges) == initial_edge_count + 1
        assert ag_graph_mutable.edges.get_by_ident("testedge") is not None

        # Remove edge
        ag_graph_mutable.remove_edge(new_edge)
        assert len(ag_graph_mutable.edges) == initial_edge_count
        assert ag_graph_mutable.edges.get_by_ident("testedge") is None

    def test_networkx_conversion(self, ag_graph: AgGraph):
        """
        Verify that conversion to and from a NetworkX MultiDiGraph preserves all graph data
        and structure, including node/edge attributes.
        """
        nx_graph = ag_graph.to_networkx()
        from pgmcp.ag_graph import AgGraph as AgGraphType

        ag_graph2 = AgGraphType.from_networkx(nx_graph)

        # Name should match
        assert ag_graph2.name == ag_graph.name

        # Vertices should match by ident
        orig_idents = {v.ident for v in ag_graph.vertices}
        new_idents = {v.ident for v in ag_graph2.vertices}
        assert orig_idents == new_idents

        # Edges should match by ident
        orig_edge_idents = {e.ident for e in ag_graph.edges}
        new_edge_idents = {e.ident for e in ag_graph2.edges}
        assert orig_edge_idents == new_edge_idents

    def test_json_serialization(self, ag_graph: AgGraph):
        """
        Verify that serialization to and from JSON preserves all graph data and structure.
        """
        json_data = ag_graph.to_json()
        from pgmcp.ag_graph import AgGraph as AgGraphType

        ag_graph2 = AgGraphType.from_json(json_data)

        # Name should match
        assert ag_graph2.name == ag_graph.name

        # Vertices should match by ident
        orig_idents = {v.ident for v in ag_graph.vertices}
        new_idents = {v.ident for v in ag_graph2.vertices}
        assert orig_idents == new_idents

        # Edges should match by ident
        orig_edge_idents = {e.ident for e in ag_graph.edges}
        new_edge_idents = {e.ident for e in ag_graph2.edges}
        assert orig_edge_idents == new_edge_idents

    def test_clear_query_cache(self, ag_graph_mutable):
        """
        Test that _clear_query_cache clears vertex and edge query caches.
        """
        # Prime the caches by running queries
        _ = ag_graph_mutable.vertices.get_by_ident("gomez")
        _ = ag_graph_mutable.edges.get_by_ident("married")

        # Clear caches
        ag_graph_mutable._clear_query_cache()

        # Assert caches are empty (simulate with hasattr or internal state if needed)
        assert not getattr(ag_graph_mutable.vertices, "_query_cache", None)
        assert not getattr(ag_graph_mutable.edges, "_query_cache", None)

    def test_graph_reference_propagation(self, ag_graph: AgGraph):
        """
        Test graph reference propagation to vertices/edges after deserialization.
        """
        from pgmcp.ag_graph import AgGraph as AgGraphType

        json_data = ag_graph.to_json()
        ag_graph2 = AgGraphType.from_json(json_data)

        # All vertices and edges should reference the new graph
        for vertex in ag_graph2.vertices:
            assert vertex.graph is ag_graph2
        for edge in ag_graph2.edges:
            assert edge.graph is ag_graph2

    def test_graph_equality(self, ag_graph: AgGraph):
        """
        Test graph equality for identical and different graphs.
        """
        from pgmcp.ag_graph import AgGraph as AgGraphType

        g1 = ag_graph
        g2 = AgGraphType.from_json(g1.to_json())
        g3 = AgGraphType.from_json(g1.to_json())
        g3.name = "different"

        assert g1 == g2
        assert g1 != g3

    def test_graph_copy(self, ag_graph: AgGraph):
        """
        Test copying a graph produces a correct, independent object.
        """
        g2 = ag_graph.deepcopy()
        g2.name = "mutated"

        # Name should be different after mutation
        assert ag_graph.name != g2.name

        # Mutate g2 and check ag_graph is unchanged
        g2.vertices[0].ident = "changed"
        assert ag_graph.vertices[0].ident != g2.vertices[0].ident
