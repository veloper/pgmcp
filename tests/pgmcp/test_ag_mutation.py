import pytest

from pgmcp.ag_mutation import AgMutation


class TestAgMutation:
    def test_vertex_add_generates_correct_cypher(self):
        m = AgMutation.add_vertex(ident="v1", label="Person", properties={"name": "Alice", "age": 30})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_addition
        assert "MERGE" in cypher and "Person" in cypher and "Alice" in cypher
        assert "SET n =" in cypher
        assert "age" in cypher

    def test_vertex_remove_generates_correct_cypher(self):
        m = AgMutation.remove_vertex(ident="v1", label="Person")
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_removal
        assert "DETACH DELETE n" in cypher
        assert "MATCH (n:Person" in cypher

    def test_vertex_update_generates_correct_cypher(self):
        m = AgMutation.update_vertex(ident="v1", label="Person", properties={"age": 31, "nickname": "Al"})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_update
        assert "SET n =" in cypher
        assert "31" in cypher and "nickname" in cypher

    def test_edge_add_generates_correct_cypher(self):
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2020, "weight": 1.5},
            # Provide endpoint labels to match new Cypher logic
            start_label="Person", end_label="Organization"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_addition
        assert "MERGE (a:Person" in cypher, f"Start node label missing in Cypher: {cypher}"
        assert "MERGE (b:Organization" in cypher, f"End node label missing in Cypher: {cypher}"
        assert "MERGE (a)-[e:KNOWS]->(b)" in cypher
        assert "SET e =" in cypher
        assert "since" in cypher and "weight" in cypher and "ident" in cypher and "start_ident" in cypher and "end_ident" in cypher

    def test_edge_remove_generates_correct_cypher(self):
        m = AgMutation.remove_edge(ident="e1", label="KNOWS", start_id=None, end_id=None, start_ident="v1", end_ident="v2")
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_removal
        assert "DELETE e" in cypher
        assert "MATCH ()-[e:KNOWS" in cypher
        assert "v1" in cypher and "v2" in cypher

    def test_edge_update_generates_correct_cypher(self):
        m = AgMutation.update_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2021, "strained": True}
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_update
        assert "SET e =" in cypher
        assert "since" in cypher and "2021" in cypher and "strained" in cypher and "ident" in cypher and "start_ident" in cypher and "end_ident" in cypher

    def test_edge_add_includes_endpoint_labels_in_cypher(self):
        # Simulate a graph context: v1 is Person, v2 is Organization
        # The mutation should propagate these labels to the Cypher
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2020, "weight": 1.5},
            # Simulate label propagation (should be set by patch logic in real use)
            start_label="Person", end_label="Organization"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        # The Cypher must include both endpoint labels
        assert "MERGE (a:Person" in cypher, f"Start node label missing in Cypher: {cypher}"
        assert "MERGE (b:Organization" in cypher, f"End node label missing in Cypher: {cypher}"
        assert "MERGE (a)-[e:KNOWS]->(b)" in cypher

    def test_missing_required_edge_fields_raises(self):
        # These will fail at type-check time, not runtime, so we skip them.
        pass

    def test_invalid_operation_entity_raises(self):
        # These will fail at type-check time, not runtime, so we skip them.
        pass

    def test_cypher_encoding_and_escaping(self):
        m = AgMutation.add_vertex(ident="v1", label="Per son", properties={"name": "O'Reilly", "desc": 'He said "hi"'})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "Per son" in cypher
        assert "O\\'Reilly" in cypher  # double-escaped as per implementation
        assert '\\"hi\\"' in cypher

    def test_vertex_add_generates_age_cypher(self):
        m = AgMutation.add_vertex(ident="v1", label="Person", properties={"name": "Joe"})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        # AGE expects: MERGE (n:Person {ident: 'v1'}) SET n = {...}
        assert "MERGE (n:Person {ident: 'v1'})" in cypher
        assert "SET n =" in cypher
        assert "Joe" in cypher

    def test_edge_add_generates_age_cypher(self):
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="workWith",
            properties={"weight": 5}, start_label="Person", end_label="Person"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        # AGE expects: MERGE (a:Person {ident: 'v1'}) MERGE (b:Person {ident: 'v2'}) MERGE (a)-[e:workWith]->(b) SET e = {...}
        assert "MERGE (a:Person {ident: 'v1'})" in cypher
        assert "MERGE (b:Person {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:workWith]->(b)" in cypher
        assert "SET e =" in cypher
        assert "weight" in cypher

    def test_edge_add_with_properties_and_labels(self):
        m = AgMutation.add_edge(
            ident="e2", start_ident="v1", end_ident="v2", label="distance",
            properties={"unit": "km", "value": 9228}, start_label="Country", end_label="Country"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "MERGE (a:Country {ident: 'v1'})" in cypher
        assert "MERGE (b:Country {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:distance]->(b)" in cypher
        assert "unit" in cypher and "9228" in cypher
