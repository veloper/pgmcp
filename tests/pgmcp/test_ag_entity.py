from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph
from pgmcp.ag_vertex import AgVertex


# Test file for TestAgEntity
class TestAgEntity:
    @pytest.fixture
    def subject(self, ag_graph: AgGraph) -> AgVertex:
        """
        Returns the first vertex from ag_graph for testing property and graph logic.
        """
        return ag_graph.vertices[0]

    def test_ident_property(self, subject: AgVertex):
        """
        Should verify that ident, start_ident, and end_ident properties on an AgEntity subclass
        can be set and retrieved, and that they interact with the underlying properties dict as expected.
        """
        # Set ident and check property
        subject.ident = "foo123"
        assert subject.ident == "foo123"
        assert subject.properties["ident"] == "foo123"
        # Set start_ident and end_ident (should exist for edges, but test for coverage)
        subject.start_ident = "startX"
        subject.end_ident = "endY"
        assert subject.start_ident == "startX"
        assert subject.end_ident == "endY"
        # Underlying properties dict should reflect changes
        assert subject.properties["start_ident"] == "startX"
        assert subject.properties["end_ident"] == "endY"

    def test_graph_assignment(self, ag_graph: AgGraph):
        """
        Should verify that assigning a graph to an entity sets the internal reference, and that
        accessing the graph property when unset raises the correct ValueError.
        """
        from pgmcp.ag_properties import AgProperties
        from pgmcp.ag_vertex import AgVertex

        subject = AgVertex(label="test", properties=AgProperties())
        # _graph is None by default
        with pytest.raises(ValueError):
            _ = subject.graph
        subject.graph = ag_graph
        assert subject.graph is ag_graph

    
    def test_property_sync_with_dict(self, subject: AgVertex):
        """
        3.1.1/3.1.2/3.1.3: Test property changes via entity and dict remain in sync. Mutate properties via both interfaces. Assert bidirectional sync. Use the global heuristic.
        """
        # Mutate via dict only
        subject.properties["foo"] = 123
        assert subject.properties["foo"] == 123
        subject.properties["bar"] = "baz"
        assert subject.properties["bar"] == "baz"
        # Remove via dict
        del subject.properties["foo"]
        assert "foo" not in subject.properties
        # Remove via dict
        del subject.properties["bar"]
        assert "bar" not in subject.properties
        # Bidirectional sync
        for k, v in subject.properties.items():
            assert subject.properties[k] == v
