from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph
from pgmcp.ag_vertex import AgVertex
from pgmcp.db import AgtypeRecord


# Test file for TestAgVertex
class TestAgVertex:
    @pytest.fixture
    def subject(self, ag_graph: AgGraph) -> AgVertex:
        """
        Returns the first AgVertex from ag_graph for testing.
        """
        return ag_graph.vertices[0]

    @pytest.fixture
    def agtype_record(self) -> AgtypeRecord:
        """
        Returns a real AgtypeRecord for AgVertex tests.
        """
        return AgtypeRecord(id=1, label="Human", properties={"ident": "test_vertex"})

    def test_from_agtype_record(self, agtype_record: AgtypeRecord):
        """
        Should verify that AgVertex is correctly instantiated from an AgtypeRecord, with all fields
        (id, label, properties) set as expected.
        """
        vertex = AgVertex.from_agtype_record(agtype_record)
        assert vertex.id == agtype_record.id
        assert vertex.label == agtype_record.label
        assert dict(vertex.properties) == agtype_record.properties

    def test_to_agtype_record(self, subject: AgVertex):
        """
        Should verify that AgVertex serializes back to an AgtypeRecord with the expected structure and values.
        """
        record = subject.to_agtype_record()
        assert record.id == subject.id
        assert record.label == subject.label
        assert record.properties == dict(subject.properties)

    def test_invalid_record_handling(self):
        """
        2.1.1/2.1.2/2.1.3: Pass incomplete or malformed records to the constructor/factory.
        Assert correct error handling or safe defaults. Use the global heuristic.
        """
        from pgmcp.db import AgtypeRecord

        # Missing required fields
        with pytest.raises(TypeError):
            AgtypeRecord()  # type: ignore  # intentional: missing required 'label'
        # Malformed: missing label
        with pytest.raises(TypeError):
            AgtypeRecord(id=1, properties={})  # type: ignore  # intentional: missing required 'label'
        # Malformed: wrong types
        bad2 = AgtypeRecord(id="not-an-int", label=123, properties="not-a-dict")  # type: ignore  # intentional: wrong types for id, label, properties
        with pytest.raises(Exception):
            _ = AgVertex.from_agtype_record(bad2)

    def test_property_mutation_and_sync(self, subject: AgVertex):
        """
        2.2.1/2.2.2/2.2.3: Test mutation synchronization between vertex and properties dict.
        Change properties via dict access only. Assert both views remain in sync. Use the global heuristic.
        """
        subject.properties["foo"] = 42
        assert subject.properties["foo"] == 42
        subject.properties["bar"] = "baz"
        assert subject.properties["bar"] == "baz"
        # No dynamic attribute assignment
        # Remove property
        del subject.properties["foo"]
        assert "foo" not in subject.properties
        for k, v in subject.properties.items():
            assert subject.properties[k] == v
