from __future__ import annotations

import pytest

from pgmcp.ag_properties import AgProperties


# Test file for TestAgProperties
class TestAgProperties:
    @pytest.fixture
    def ag_properties(self):
        """
        Returns an AgProperties instance for testing dict-like behavior.
        """
        return AgProperties({"ident": "foo", "bar": 1})

    def test_dict_behavior(self, ag_properties):
        """
        Should verify that AgProperties behaves like a dict for getitem, setitem, delitem, iteration, etc.
        """
        # __getitem__, __setitem__, __delitem__, __contains__
        ag_properties["baz"] = 42
        assert ag_properties["baz"] == 42
        assert "baz" in ag_properties
        del ag_properties["baz"]
        assert "baz" not in ag_properties
        # get, setdefault, pop, popitem
        ag_properties.setdefault("alpha", 100)
        assert ag_properties["alpha"] == 100
        ag_properties["beta"] = 200
        assert ag_properties.pop("beta") == 200
        # keys, values, items, len, iter
        keys = set(ag_properties.keys())
        values = set(ag_properties.values())
        items = set(ag_properties.items())
        assert "ident" in keys and "bar" in keys
        assert 1 in values or "foo" in values
        assert all(isinstance(k, str) for k, v in items)
        assert len(list(iter(ag_properties))) == len(ag_properties)
        # clear, update, copy, eq
        ag_properties.update({"x": 1, "y": 2})
        assert ag_properties["x"] == 1 and ag_properties["y"] == 2
        copy = ag_properties.copy()
        assert copy == ag_properties
        ag_properties.clear()
        assert len(ag_properties) == 0

    def test_ident_set_get(self, ag_properties):
        """
        Should verify that ident, start_ident, and end_ident properties can be set and retrieved correctly,
        and that they map to the correct keys in the underlying dict.
        """
        # ident
        ag_properties.ident = "myid"
        assert ag_properties.ident == "myid"
        # start_ident
        ag_properties.start_ident = "startid"
        assert ag_properties.start_ident == "startid"
        # end_ident
        ag_properties.end_ident = "endid"
        assert ag_properties.end_ident == "endid"
        # Underlying dict mapping
        from pgmcp.settings import get_settings

        settings = get_settings()
        assert ag_properties[settings.age.ident_property] == "myid"
        assert ag_properties[settings.age.start_ident_property] == "startid"
        assert ag_properties[settings.age.end_ident_property] == "endid"
