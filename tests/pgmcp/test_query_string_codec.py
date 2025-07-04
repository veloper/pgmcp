from collections import OrderedDict
from functools import wraps
from types import SimpleNamespace
from typing import Any, Callable, Dict, Generic, List, Self, TypeVar

import pytest

from _pytest.fixtures import FixtureRequest

from src.pgmcp.query_string_codec import QueryStringCodec


# ======================================================================
#  CORE IMPLEMENTATION
# ======================================================================

T = TypeVar('T')

class LetObject(Generic[T]):
    """
    A callable, self-resolving object that can also redefine its own
    behavior for the current test scope.
    """
    def __init__(self, registry: 'LetRegistry', name: str):
        self._registry = registry
        self._name = name

    def __call__(self) -> T:
        """Resolves the object's value via the registry's layered context."""
        return self._registry.resolve(self._name)

    def let(self, definition: Callable[["LetRegistry"], T]) -> None:
        """Overrides the definition for this object in the current test scope."""
        self._registry.override(self._name, definition)
        
    def set(self, value: Any) -> None:
        """Sets a static value for this object in the current test scope."""
        self.let(lambda _: value)

    def __repr__(self) -> str:
        return f"<LetObject '{self._name}'>"


class LetRegistry:
    """
    The central controller. Manages layered definitions to allow for
    temporary, test-scoped overrides.
    """
    def __init__(self):
        # A stack of dictionaries. Base layer is at index 0. Overrides are pushed on top.
        self._definitions_stack: List[Dict[str, Callable]] = [{}]
        self._let_objects: Dict[str, LetObject] = {}
        self._memoized_values: Dict[str, Any] = {}

    def let(self, name: str, func: Callable) -> LetObject:
        """Creates a BASE definition and returns the callable LetObject."""
        if not callable(func):
            definition = lambda _: func
        else:
            definition = func
        self._definitions_stack[0][name] = definition

        if name not in self._let_objects:
            self._let_objects[name] = LetObject(self, name)
        return self._let_objects[name]

    def override(self, name: str, func: Callable) -> None:
        """Creates a TEMPORARY override in a new layer on the definition stack."""
        if not callable(func):
            definition = lambda _: func
        else:
            definition = func
        if len(self._definitions_stack) == 1:
            self._definitions_stack.append({})
        self._definitions_stack[-1][name] = definition

    def resolve(self, name: str) -> Any:
        """Resolves a value, searching from the top override layer down to the base."""
        if name in self._memoized_values:
            return self._memoized_values[name]

        definition_func = None
        for layer in reversed(self._definitions_stack):
            if name in layer:
                definition_func = layer[name]
                break

        if definition_func:
            dependency_resolver = SimpleNamespace(**self._let_objects)
            value = definition_func(dependency_resolver)
            self._memoized_values[name] = value
            return value

        raise NameError(f"let variable '{name}' is not defined.")

    def reset(self) -> None:
        """Resets the context by clearing memos and discarding override layers."""
        self._memoized_values.clear()
        self._definitions_stack = self._definitions_stack[:1]



let_registry = LetRegistry()

"""
Building up a graph of JIT lets that can be used to quickly test effects upstream affecting outcomes downstream.
"""

codec_kwargs = let_registry.let("codec_kwargs", lambda _: {})
codec = let_registry.let("codec", lambda r: QueryStringCodec(**r.codec_kwargs()))

# Test various query params
params_input = let_registry.let("params_input", lambda r: "a=1&b=2")
params_decoded = let_registry.let("query_output", lambda r: r.codec().decode(r.params_input()))

python_input = let_registry.let("python_input", lambda r: OrderedDict([("a", "1"), ("b", "2")]))
python_encoded = let_registry.let("python_output", lambda r: r.codec().encode(r.python_input()))



@pytest.fixture(scope="function", autouse=True)
def reset_let_registry():
    """Critical fixture to reset the let_registry before each test."""
    let_registry.reset()
    
class TestDecoding:

    def test_decode_simple_query(self):
        params_input.set("a=1&b=2")
        assert params_decoded() == OrderedDict([("a", ["1"]), ("b", ["2"])])

    def test_decode_blank_values_when_specified(self):
        codec_kwargs.set({"keep_blank_values": True})
        params_input.set("a=&b=2")
        assert params_decoded() == OrderedDict([("a", [""]), ("b", ["2"])])

    def test_decode_raises_on_strict_parsing_error(self):
        codec_kwargs.set({"strict_parsing": True})
        params_input.set("a=1&&b=2")
        
        with pytest.raises(ValueError):
            codec().decode(params_input())

    def test_decode_with_custom_separator(self):
        codec_kwargs.set({"separator": ";"})
        params_input.set("a=1;b=2")
        assert params_decoded() == OrderedDict([("a", ["1"]), ("b", ["2"])])

    def test_decode_limits_fields_with_max_num_fields(self):
        codec_kwargs.set({"max_num_fields": 3})
        params_input.set("a=1&b=2")
        assert list(params_decoded().keys()) == ["a", "b"]

    def test_decode_empty_string(self):
        params_input.set("")
        assert params_decoded() == {}

    def test_decode_nested_lists_and_dicts(self):
        parsed = {"a": ["1", "2"], "b": ["3"]}
        out = codec()._convert_parse_qs_to_query_string_dict(parsed)
        assert out == OrderedDict([("a", ["1", "2"]), ("b", ["3"])])

    def test_decode_with_custom_encoding_and_errors(self):
        codec_kwargs.set({"encoding": "utf-8", "errors": "ignore"})
        params_input.set("a=%E2%28")
        assert "a" in params_decoded()

    def test_decode_raises_when_max_num_fields_exceeded(self):
        codec_kwargs.set({"max_num_fields": 2})
        params_input.set("&".join(f"k{i}=v{i}" for i in range(10)))
        with pytest.raises(ValueError, match="Max number of fields exceeded"):
            params_decoded()



class TestEncoding:

    def test_encode_simple_query(self):
        python_input.set(OrderedDict([("a", "1"), ("b", "2")]))
        assert python_encoded() == "a=1&b=2"    
        
    def test_encode_blank_values_when_specified(self):
        codec_kwargs.set({"keep_blank_values": True})
        python_input.set(OrderedDict([("a", ""), ("b", "2")]))
        assert python_encoded() == "a=&b=2"
        
    def test_encode_does_not_raise_on_an_empty_dict(self):
        python_input.set(OrderedDict())
        assert python_encoded() == "", "Expected empty string for empty OrderedDict"
                        
    def test_encode_with_custom_separator(self):
        codec_kwargs.set({"separator": ";"})
        python_input.set(OrderedDict([("a", "1"), ("b", "2")]))
        assert python_encoded() == "a=1;b=2", "Expected ';' as separator"        
        
    def test_encode_with_custom_encoding_and_errors(self):
        codec_kwargs.set({"encoding": "utf-8", "errors": "ignore"})
        python_input.set(OrderedDict([("a", "test")]))
        assert python_encoded() == "a=test", "Expected utf-8 encoding to work correctly"
        
    def test_encode_nested_lists_and_dicts(self):
        python_input.set(OrderedDict([("a", ["1", "2"]), ("b", ["3"])]))
        assert python_encoded() == "a=1&a=2&b=3", "Expected nested lists to be encoded correctly"
        
    def test_encode_with_custom_quote_via(self):
        from urllib.parse import quote_plus
        codec_kwargs.set({"quote_via": quote_plus})
        python_input.set(OrderedDict([("a", "hello world"), ("b", "test&value")]))
        assert python_encoded() == "a=hello+world&b=test%26value", "Expected custom quote_via to properly encode special characters"

    

    def test_encode_with_custom_safe_characters(self):
        chars = ["!", "*", "'", "(", ")", ";", ":", "@", "&", "=", "+", "$", ",", "/", "?", "#", "[", "]"]
        
        codec_kwargs.set({"safe": "".join(chars)})
        python_input.set(
            OrderedDict([
                ("a", "hello!world"),
                ("b", "test&value"),
                ("c", "special*chars'()"),
                ("d", "colon:and;semicolon"),
                ("e", "@user+name$100"),
                ("f", "path/to/resource?query#fragment"),
                ("g", "array[0]=value"),
            ])
        )
        
        result = python_encoded()
        expected = "a=hello!world&b=test&value&c=special*chars'()&d=colon:and;semicolon&e=@user+name$100&f=path/to/resource?query#fragment&g=array[0]=value"
        assert result == expected

