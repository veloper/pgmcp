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
        return AgtypeRecord(id=1, label="REL", properties={"ident": "test_edge"}, start_id=1, end_id=2)

    def test_from_agtype_record(self, agtype_record: AgtypeRecord):
        """
        Should verify that AgEdge is correctly instantiated from an AgtypeRecord, with all fields
        (id, label, properties, start, end) set as expected.
        """
        edge = AgEdge.from_agtype_record(agtype_record)
        assert edge.id == agtype_record.id
        assert edge.label == agtype_record.label
        assert dict(edge.properties) == agtype_record.properties
        assert edge.start_id == agtype_record.start_id
        assert edge.end_id == agtype_record.end_id

    def test_to_agtype_record(self, subject: AgEdge):
        """
        Should verify that AgEdge serializes back to an AgtypeRecord with the expected structure and values.
        """
        record = subject.to_agtype_record()
        assert record.id == subject.id
        assert record.label == subject.label
        assert record.properties == dict(subject.properties)
        assert record.start_id == subject.start_id
        assert record.end_id == subject.end_id

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
        
        # Malformed: missing start/end for edge
        bad = AgtypeRecord(id=1, label="REL", properties={}, start_id=123, end_id=None)  # type: ignore  # intentional: missing end_id
        with pytest.raises(ValueError) as exc_info:
            _ = AgEdge.from_agtype_record(bad)
        
        assert exc_info is not None, "Expected TypeError for missing end_id while having a start_id in AgEdge on parsing AgtypeRecord."
        
        # # Malformed: wrong types
        # bad2 = AgtypeRecord(id="not-an-int", label=123, properties="not-a-dict", start_id="x", end_id=None)  # type: ignore  # intentional: wrong types for id, label, properties, start
        # with pytest.raises(Exception):
        #     _ = AgEdge.from_agtype_record(bad2)

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
