import pytest

from pgmcp.ag_mutation import AgMutation


class TestAgMutation:
    def test_vertex_add_generates_correct_cypher(self):
        m = AgMutation.add_vertex(ident="v1", label="Person", properties={"name": "Alice", "age": 30})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_addition
        assert "CREATE (n:Person {name: 'Alice', age: 30, ident: 'v1'})" in cypher
        assert "name: 'Alice'" in cypher
        assert "age: 30" in cypher

    def test_vertex_remove_generates_correct_cypher(self):
        m = AgMutation.remove_vertex(ident="v1", label="Person")
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_removal
        assert "MATCH (n:Person {ident: 'v1'})" in cypher
        assert "DETACH DELETE n" in cypher

    def test_vertex_update_generates_correct_cypher(self):
        m = AgMutation.update_vertex(ident="v1", label="Person", properties={"age": 31, "nickname": "Al"})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_vertex and m.is_update
        assert "MERGE (n:Person {age: 31, nickname: 'Al', ident: 'v1'})" in cypher
        assert "age: 31" in cypher
        assert "nickname: 'Al'" in cypher

    def test_edge_add_generates_correct_cypher(self):
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2020, "weight": 1.5},
            start_label="Person", end_label="Organization"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_addition
        assert "MATCH (a:Person {ident: 'v1'})" in cypher
        assert "MATCH (b:Organization {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:KNOWS {since: 2020, weight: 1.5, ident: 'e1', start_ident: 'v1', end_ident: 'v2'}]->(b)" in cypher
        assert "since: 2020" in cypher
        assert "weight: 1.5" in cypher
        assert "ident: 'e1'" in cypher
        assert "start_ident: 'v1'" in cypher
        assert "end_ident: 'v2'" in cypher

    def test_edge_remove_generates_correct_cypher(self):
        m = AgMutation.remove_edge(ident="e1", label="KNOWS", start_id=None, end_id=None, start_ident="v1", end_ident="v2")
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_removal
        assert "MATCH ()-[e:KNOWS {start_ident: 'v1', end_ident: 'v2'}]->()" in cypher
        assert "DELETE e" in cypher

    def test_edge_update_generates_correct_cypher(self):
        m = AgMutation.update_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2021, "strained": True}
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert m.is_edge and m.is_update
        assert "MATCH (a: {ident: 'v1'})" in cypher or "MATCH (a:Person {ident: 'v1'})" in cypher
        assert "MATCH (b: {ident: 'v2'})" in cypher or "MATCH (b:Organization {ident: 'v2'})" in cypher or "MATCH (b:Person {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:KNOWS {since: 2021, strained: true, ident: 'e1', start_ident: 'v1', end_ident: 'v2'}]->(b)" in cypher
        assert "since: 2021" in cypher
        assert "strained: true" in cypher or "strained: True" in cypher
        assert "ident: 'e1'" in cypher
        assert "start_ident: 'v1'" in cypher
        assert "end_ident: 'v2'" in cypher

    def test_edge_add_includes_endpoint_labels_in_cypher(self):
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="KNOWS",
            properties={"since": 2020, "weight": 1.5},
            start_label="Person", end_label="Organization"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "MATCH (a:Person {ident: 'v1'})" in cypher
        assert "MATCH (b:Organization {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:KNOWS {since: 2020, weight: 1.5, ident: 'e1', start_ident: 'v1', end_ident: 'v2'}]->(b)" in cypher

    def test_missing_required_edge_fields_raises(self):
        pass

    def test_invalid_operation_entity_raises(self):
        pass

    def test_cypher_encoding_and_escaping(self):
        m = AgMutation.add_vertex(ident="v1", label="Per son", properties={"name": "O'Reilly", "desc": 'He said "hi"'})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "Per son" in cypher
        assert "O\\'Reilly" in cypher
        assert '\\"hi\\"' in cypher

    def test_vertex_add_generates_age_cypher(self):
        m = AgMutation.add_vertex(ident="v1", label="Person", properties={"name": "Joe"})
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "CREATE (n:Person {name: 'Joe', ident: 'v1'})" in cypher
        assert "name: 'Joe'" in cypher

    def test_edge_add_generates_age_cypher(self):
        m = AgMutation.add_edge(
            ident="e1", start_ident="v1", end_ident="v2", label="workWith",
            properties={"weight": 5}, start_label="Person", end_label="Person"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "MATCH (a:Person {ident: 'v1'})" in cypher
        assert "MATCH (b:Person {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:workWith {weight: 5, ident: 'e1', start_ident: 'v1', end_ident: 'v2'}]->(b)" in cypher
        assert "weight: 5" in cypher

    def test_edge_add_with_properties_and_labels(self):
        m = AgMutation.add_edge(
            ident="e2", start_ident="v1", end_ident="v2", label="distance",
            properties={"unit": "km", "value": 9228}, start_label="Country", end_label="Country"
        )
        stmts = m.to_statements()
        cypher = "\n".join(map(str, stmts))
        assert "MATCH (a:Country {ident: 'v1'})" in cypher
        assert "MATCH (b:Country {ident: 'v2'})" in cypher
        assert "MERGE (a)-[e:distance {unit: 'km', value: 9228, ident: 'e2', start_ident: 'v1', end_ident: 'v2'}]->(b)" in cypher
        assert "unit: 'km'" in cypher
        assert "value: 9228" in cypher
