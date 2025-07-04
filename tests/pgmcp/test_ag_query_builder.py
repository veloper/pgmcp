from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph
from pgmcp.ag_query_builder import AgQueryBuilderVertex


class TestAgQueryBuilder:
    @pytest.fixture
    def ag_query_builder(self, ag_graph: AgGraph):
        """
        Returns an AgQueryBuilder instance for testing filter chain and cache behavior.
        """
        return ag_graph.vertices.query()

    def test_filter_chain(self, ag_query_builder: AgQueryBuilderVertex):
        """
        Test that chaining filter, label, and prop steps produces the correct filtered results from the query builder.
        This uses the Addams Family graph from the ag_graph fixture.
        """
        # Filter by label 'Human' and property 'age' > 20
        humans = ag_query_builder.label("Human").all()
        assert all(v.label == "Human" for v in humans)
        # Filter by label and property
        gomez = ag_query_builder.label("Human").prop("ident", "gomez").first()
        assert gomez is not None
        assert gomez.properties["ident"] == "gomez"
        # Chaining label and prop should be equivalent to props
        gomez2 = ag_query_builder.label("Human").props(ident="gomez").first()
        assert gomez2 is not None
        assert gomez2.properties["ident"] == "gomez"
        # Negative case: no such person
        nobody = ag_query_builder.label("Human").prop("ident", "nobody").first()
        assert nobody is None

    def test_cache_behavior(self, ag_query_builder: AgQueryBuilderVertex, ag_graph: AgGraph):
        """
        Verify that the query builder uses and invalidates the cache as expected during queries and graph mutations.
        The cache should be used for repeated queries, and invalidated when the graph is mutated (vertex added/removed).
        """
        # Prime the cache with a query
        all_vertices_1 = ag_query_builder.all()
        assert all_vertices_1, "Should return vertices on first query."
        # Query again, should hit cache (no mutation)
        all_vertices_2 = ag_query_builder.all()
        assert all_vertices_2 == all_vertices_1, "Cache should return same results."

        # Mutate the graph: add a new vertex
        from pgmcp.ag_properties import AgProperties
        from pgmcp.ag_vertex import AgVertex

        new_vertex = AgVertex(label="Human", properties=AgProperties(root={"ident": "newperson", "age": 42}))
        ag_graph.add_vertex(new_vertex)
        # Query again, should NOT hit cache (should see new vertex)
        all_vertices_3 = ag_query_builder.all()
        idents = {v.properties.get("ident") for v in all_vertices_3}
        assert "newperson" in idents, "Cache should be invalidated after mutation."

        # Remove a vertex and check cache invalidation again
        to_remove = next((v for v in all_vertices_3 if v.properties.get("ident") == "newperson"), None)
        assert to_remove is not None, "New vertex should exist."
        ag_graph.remove_vertex(to_remove)
        all_vertices_4 = ag_query_builder.all()
        idents_after_removal = {v.properties.get("ident") for v in all_vertices_4}
        assert "newperson" not in idents_after_removal, "Cache should be invalidated after removal."
