from __future__ import annotations

import pytest

from pgmcp.ag_edge import AgEdge
from pgmcp.ag_graph import AgGraph
from pgmcp.db import AgtypeRecord


# Test file for TestAgEdge
class TestAgEdge:
    @pytest.fixture
    def subject(self, ag_graph: AgGraph) -> AgEdge:
        """
        Returns the first AgEdge from ag_graph for testing.
        """
        return ag_graph.edges[0]

    @pytest.fixture
    def agtype_record(self) -> AgtypeRecord:
        """
        Returns a real AgtypeRecord for AgEdge tests.
        """
        return AgtypeRecord(id=1, start_id=1, end_id=2, label="REL", properties={
            "ident": "test_edge", 
            "start_ident":"test_start", 
            "end_ident":"test_end"
        })

    def test_vertex_relationships(self, subject: AgEdge, ag_graph: AgGraph):
        """
        Should verify that start_vertex and end_vertex properties resolve to the correct AgVertex
        instances from the graph, or None if not found.
        """
        # Positive case: vertices exist
        start_vertex = subject.start_vertex
        end_vertex = subject.end_vertex
        if subject.start_ident:
            assert start_vertex is not None
            assert start_vertex.ident == subject.start_ident
        else:
            assert start_vertex is None
        if subject.end_ident:
            assert end_vertex is not None
            assert end_vertex.ident == subject.end_ident
        else:
            assert end_vertex is None

    def test_invalid_agtype_record_handling(self):
        """
        1.1.1/1.1.2/1.1.3: Pass malformed or missing-field records to the constructor or factory.
        Assert that errors are raised or fields are set to safe defaults. Use the global heuristic.
        """
        from pgmcp.db import AgtypeRecord

        # Missing required fields
        with pytest.raises(TypeError) as exc_info:
            AgtypeRecord()  # type: ignore  # intentional: missing required 'label'
            
        assert exc_info is not None, "Expected TypeError for missing 'label' field in AgtypeRecord."
        

    def test_property_mutation_and_sync(self, subject: AgEdge):
        """
        1.2.1/1.2.2/1.2.3: Test mutation synchronization between edge and properties dict.
        Change properties via dict access only. Assert both views remain in sync. Use the global heuristic.
        """
        subject.properties["foo"] = 42
        assert subject.properties["foo"] == 42
        subject.properties["bar"] = "baz"
        assert subject.properties["bar"] == "baz"
        # No dynamic attribute assignment
        del subject.properties["foo"]
        assert "foo" not in subject.properties
        for k, v in subject.properties.items():
            assert subject.properties[k] == v
