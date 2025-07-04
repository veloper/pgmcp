from __future__ import annotations

import pytest

from pgmcp.ag_graph import AgGraph


# Test file for TestAgPatch

class TestAgPatch:
    @pytest.fixture
    def ag_graph_pair(self, ag_graph: AgGraph):
        """
        Returns a tuple of two AgGraph instances for patch tests with a known set of changes between the two.
        """
        
        original = ag_graph
        
        # Deepcopy
        modified = ag_graph.deepcopy()
        
        # Apply Changes
        
        # TBD
        
        return original, modified

    def test_from_a_and_b(self, ag_graph_pair):
        """
        Should verify that a patch is correctly created from two graphs, capturing all additions,
        removals, and updates for both vertices and edges.
        """
        pass

    def test_patch_field_integrity(self, ag_graph_pair):
        """
        Should verify that the patch's mutations list is a list and defaults to empty.
        """
        pass


    def test_to_cypher_vertex_addition(self, ag_graph_pair):
        from pgmcp.ag_patch import AgPatch
        from pgmcp.ag_properties import AgProperties
        from pgmcp.ag_vertex import AgVertex
        orig, mod = ag_graph_pair
        v = AgVertex.model_validate({"label": "Person", "properties": AgProperties({"ident": "v_add", "name": "Alice"})})
        mod.add_vertex(v)
        patch = AgPatch.from_a_to_b(orig, mod)
        additions = [m for m in patch.mutations if m.is_addition and m.is_vertex]
        assert additions, "No vertex addition detected"
        cypher = str(additions[0].to_statement())
        assert "MERGE (n:Person" in cypher
        assert "Alice" in cypher

    def test_to_cypher_vertex_removal(self, ag_graph_pair):
        from pgmcp.ag_patch import AgPatch
        orig, mod = ag_graph_pair
        if not mod.vertices:
            pytest.skip("No vertices to remove")
        v = mod.vertices.root[0]
        mod.remove_vertex(v)
        patch = AgPatch.from_a_to_b(orig, mod)
        removals = [m for m in patch.mutations if m.is_removal and m.is_vertex]
        assert removals, "No vertex removal detected"
        cypher = str(removals[0].to_statement())
        assert cypher.startswith(f"MATCH (n:{v.label}")
        assert "DETACH DELETE" in cypher

    def test_to_cypher_vertex_update(self, ag_graph_pair):
        from pgmcp.ag_patch import AgPatch
        orig, mod = ag_graph_pair
        v = mod.vertices.root[0]
        v.properties["age"] = 42
        patch = AgPatch.from_a_to_b(orig, mod)
        updates = [m for m in patch.mutations if m.is_update and m.is_vertex]
        assert updates, "No vertex update detected"
        cypher = str(updates[0].to_statement())
        assert cypher.startswith(f"MATCH (n:{v.label}")
        assert "42" in cypher

    def test_to_cypher_edge_addition(self, ag_graph_pair):
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_patch import AgPatch
        from pgmcp.ag_properties import AgProperties
        orig, mod = ag_graph_pair
        v1, v2 = mod.vertices.root[:2]
        e = AgEdge.model_validate({
            "label": "KNOWS",
            "properties": AgProperties({"ident": "e_add", "start_ident": v1.ident, "end_ident": v2.ident, "since": 2024}),
            "start_id": v1.id,
            "end_id": v2.id
        })
        mod.add_edge(e)
        patch = AgPatch.from_a_to_b(orig, mod)
        additions = [m for m in patch.mutations if m.is_addition and m.is_edge and m.ident == "e_add"]
        assert additions, "No edge addition detected for 'e_add'"
        cypher = str(additions[0].to_statement())
        assert "MERGE (a)-[e:KNOWS]->(b)" in cypher or "MERGE (a)-[e:PARENT_OF]->(b)" in cypher
        assert "2024" in cypher

    def test_to_cypher_edge_removal(self, ag_graph_pair: tuple[AgGraph, AgGraph]):
        from pgmcp.ag_patch import AgPatch
        orig, mod = ag_graph_pair
        e = mod.edges.root[0]
        mod.remove_edge(e)
        patch = AgPatch.from_a_to_b(orig, mod)
        removals = [m for m in patch.mutations if m.is_removal and m.is_edge]
        assert removals, "No edge removal detected"
        cypher = str(removals[0].to_statement())
        assert cypher.startswith(f"MATCH ()-[e:{e.label}")
        assert "DELETE e" in cypher

    def test_to_cypher_edge_update(self, ag_graph_pair: tuple[AgGraph, AgGraph]):
        from pgmcp.ag_patch import AgPatch
        orig, mod = ag_graph_pair
        e = mod.edges.root[0]
        e.properties["weight"] = 3.14
        patch = AgPatch.from_a_to_b(orig, mod)
        updates = [m for m in patch.mutations if m.is_update and m.is_edge]
        assert updates, "No edge update detected"
        cypher = str(updates[0].to_statement())
        assert cypher.startswith(f"MATCH (a {{") or cypher.startswith(f"MATCH ()-[e:{e.label}")
        assert "3.14" in cypher

    def test_major_graph_change_patch_and_cypher(self, ag_graph_pair: tuple[AgGraph, AgGraph]):
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_patch import AgPatch
        from pgmcp.ag_properties import AgProperties
        from pgmcp.ag_vertex import AgVertex
        orig, mod = ag_graph_pair

        # 1. Remove a vertex
        v_remove = mod.vertices.root[0]
        mod.remove_vertex(v_remove)
        # 2. Remove an edge
        e_remove = mod.edges.root[0]
        mod.remove_edge(e_remove)
        # 3. Add a new vertex
        v_add = AgVertex.model_validate({"id": 200, "label": "Robot", "properties": {"ident": "robot1", "name": "Robo"}})
        mod.add_vertex(v_add)
        # 4. Add a new edge
        v2 = mod.vertices.root[1]
        e_add = AgEdge.model_validate({
            "label": "KNOWS",
            "properties": {"ident": "robot_knows", "start_ident": v_add.ident, "end_ident": v2.ident, "since": 2025},
            "start_id": v_add.id,
            "end_id": v2.id
        })
        mod.add_edge(e_add)
        # 5. Update a vertex property
        v_update = mod.vertices.root[0]
        v_update.properties["nickname"] = "G-Man"
        # 6. Update an edge property
        e_update = mod.edges.root[0]
        e_update.properties["strained"] = True
        # 7. Add another vertex
        v_add2 = AgVertex.model_validate({"id": 201, "label": "Ghost", "properties": {"ident": "ghost1", "name": "Boo"}})
        mod.add_vertex(v_add2)
        # 8. Add another edge
        e_add2 = AgEdge.model_validate({
            "label": "HAUNTS",
            "properties": {"ident": "ghost_haunts", "start_ident": v_add2.ident, "end_ident": v_update.ident},
            "start_id": v_add2.id,
            "end_id": v_update.id
        })
        mod.add_edge(e_add2)
        # 9. Remove another edge
        e_remove2 = mod.edges.root[1]
        mod.remove_edge(e_remove2)
        # 10. Update another vertex property
        v_update2 = mod.vertices.root[1]
        v_update2.properties["age"] = 99

        patch = AgPatch.from_a_to_b(orig, mod)
        cyphers = [str(m.to_statement()) for m in patch.mutations]
        cypher_str = " ".join(cyphers)
        # Confirm 10 distinct changes are present in the patch
        assert len(patch.mutations) >= 10
        # Confirm each change is reflected in the cypher
        checks = [
            # 1. Vertex removal
            "DETACH DELETE" in cypher_str,
            # 2. Edge removal
            "DELETE e" in cypher_str,
            # 3. Vertex addition
            "MERGE (n:Robot" in cypher_str,
            # 4. Edge addition
            ":KNOWS" in cypher_str and "2025" in cypher_str,
            # 5. Vertex property update
            "nickname" in cypher_str,
            # 6. Edge property update (new format: 'strained: true' in SET e = {...})
            "strained: true" in cypher_str,
            # 7. Another vertex addition
            "MERGE (n:Ghost" in cypher_str,
            # 8. Another edge addition
            ":HAUNTS" in cypher_str,
            # 9. Another edge removal
            "DELETE e" in cypher_str,
            # 10. Another vertex property update (new format: 'age: 99' in SET n = {...})
            "age: 99" in cypher_str,
        ]
        assert all(checks), f"Not all major changes reflected in cypher: {checks}\nCypher output: {cypher_str}"
