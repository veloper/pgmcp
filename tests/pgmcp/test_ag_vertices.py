from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph


# Test file for TestAgVertices
class TestAgVertices:
    @pytest.fixture
    def ag_vertices(self, ag_graph: AgGraph):
        """
        Returns an AgVertices instance for testing query methods.
        """
        return ag_graph.vertices

    def test_query_methods(self, ag_vertices):
        """
        Should verify that query builder methods (filter, label, etc.) on AgVertices return expected results
        based on the underlying vertex data.
        """
        # Filter by label
        humans = ag_vertices.label("Human").all()
        assert all(v.label == "Human" for v in humans)
        # Filter by property
        adults = ag_vertices.prop("age", 42).all()
        assert all(v.properties.get("age") == 42 for v in adults)
        # Chained filters
        gomez = ag_vertices.label("Human").prop("ident", "gomez").first()
        assert gomez is not None
        assert gomez.properties.get("ident") == "gomez"
        # Negative case
        nobody = ag_vertices.label("Human").prop("ident", "nobody").first()
        assert nobody is None

    def test_get_by_ident(self, ag_vertices):
        """
        Should verify that get_by_ident returns the correct AgVertex for a given ident, or None if not found.
        """
        # Positive case
        v = ag_vertices.get_by_ident("gomez")
        assert v is not None
        assert v.properties.get("ident") == "gomez"
        # Negative case
        none_v = ag_vertices.get_by_ident("not_a_vertex")
        assert none_v is None
