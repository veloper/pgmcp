from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph


class TestAgEdges:
    @pytest.fixture
    def ag_edges(self, ag_graph: AgGraph):
        """
        Returns an AgEdges instance for testing query methods.
        """
        return ag_graph.edges

    def test_query_methods(self, ag_edges):
        """
        Should verify that query builder methods (filter, label, etc.) on AgEdges return expected results
        based on the underlying edge data.
        """
        # Filter by label
        parent_edges = ag_edges.label("PARENT_OF").all()
        assert all(e.label == "PARENT_OF" for e in parent_edges)
        # Filter by property
        strained_edges = ag_edges.prop("strained", True).all()
        assert all(e.properties.get("strained") is True for e in strained_edges)
        # Filter by start_ident
        gomez_edges = ag_edges.start_ident("gomez").all()
        assert all(e.properties.get("start_ident") == "gomez" for e in gomez_edges)
        # Chained filters
        gomez_parent_edges = ag_edges.label("PARENT_OF").start_ident("gomez").all()
        assert all(e.label == "PARENT_OF" and e.properties.get("start_ident") == "gomez" for e in gomez_parent_edges)

    def test_get_by_ident(self, ag_edges):
        """
        Should verify that get_by_ident returns the correct AgEdge for a given ident, or None if not found.
        """
        # Positive case
        edge = ag_edges.get_by_ident("gomez_parent_of_wednesday")
        assert edge is not None
        assert edge.properties.get("ident") == "gomez_parent_of_wednesday"
        # Negative case
        none_edge = ag_edges.get_by_ident("not_an_edge")
        assert none_edge is None
