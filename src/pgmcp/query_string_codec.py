from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Tuple, Union
from urllib.parse import parse_qs, quote_plus, urlencode


# Self-referential type for query string values
QueryStringDict = OrderedDict[str, 'QueryStringValue']
QueryStringValue = Union[str, float, int, bool, None, List['QueryStringValue'], QueryStringDict]

# Self-referential type for two-element tuples used in urlencode
TwoElementTupleValue = Union[str, List['TwoElementTuple']]
TwoElementTuple = Tuple[str, TwoElementTupleValue] 
TwoElementTupleList = List[TwoElementTuple]


class QueryStringCodec:
    """Bidirectional codec for query string conversion with separate decode/encode parameter control.

    Handles the complexity of urllib.parse.parse_qs and urllib.parse.urlencode having different
    parameter signatures while providing a unified interface. Supports all standard query string
    parsing and encoding options with sensible defaults.

    Decode: String → QueryStringDict 
        Full: String -> parse_qs -> _convert_parse_qs_to_query_string_dict -> QueryStringDict
    Encode: QueryStringDict → String
        Full: QueryStringDict -> _convert_query_string_dict_to_urlencode_tuple_sorted_sequence -> urlencode -> String

    Decode Parameters:
        keep_blank_values (bool): Keep blank values in parsed results
        strict_parsing (bool): Raise errors on parsing failures  
        max_num_fields (int|None): Limit number of fields parsed

    Encode Parameters:
        safe (str): Characters safe from URL encoding
        quote_via (callable): URL encoding function

    Shared Parameters:
        separator (str): Field separator character
        encoding (str): Character encoding for string conversion
        errors (str): Error handling strategy for encoding issues

    Note:
        doseq=True is always used for encoding to handle ordered dicts and lists correctly.
    """

    def __init__(self, keep_blank_values: bool = False, strict_parsing: bool = False,
                 encoding: str = 'utf-8', errors: str = 'replace', max_num_fields: int | None = None,
                 separator: str = '&', safe: str = '', quote_via=quote_plus):

        # Decode-specific options
        self.keep_blank_values = keep_blank_values
        self.strict_parsing = strict_parsing
        self.max_num_fields = max_num_fields
        self.separator = separator

        # Encode-specific options  
        self.doseq = True
        self.safe = safe
        self.quote_via = quote_via

        # Shared options
        self.encoding = encoding
        self.errors = errors

    def _convert_parse_qs_to_query_string_dict(self, parsed: Dict[str, List[str]]) -> QueryStringDict:
        """Convert the output of urllib.parse.parse_qs to a QueryStringDict using recursive parsing."""

        def recursive_parse(value: Union[str, List[str]]) -> QueryStringValue:
            """Recursively parse values to handle nested lists."""
            if isinstance(value, list):
                # If it's a list, recursively parse each item
                return [recursive_parse(item) for item in value]
            elif isinstance(value, str):
                # If it's a string, decode it
                return value.encode(self.encoding).decode(self.encoding, errors=self.errors)
            else:
                # Otherwise return the value as is
                return value

        # Apply recursive parsing to all parsed values - RETURN OrderedDict
        return OrderedDict((key, recursive_parse(value)) for key, value in parsed.items())

    def _convert_query_string_dict_to_urlencode_sorted_sequence(self, query_dict: QueryStringDict) -> TwoElementTupleList:
        """Convert a QueryStringDict to urlencode-compatible tuple sequence.

        urlencode with doseq=True expects: List[Tuple[str, Union[str, List[Tuple[str, str]]]]]
        """

        if not isinstance(query_dict, OrderedDict):
            raise TypeError("query_dict must be an OrderedDict")

        def convert_value(value: QueryStringValue) -> TwoElementTupleValue:
            """Convert QueryStringValue to urlencode-compatible format."""
            if isinstance(value, (str, int, float, bool)) or value is None:
                return str(value) if value is not None else ''
            elif isinstance(value, list):
                return [('', convert_value(item)) for item in value]
            elif isinstance(value, dict):
                return [(k, convert_value(v)) for k, v in value.items()]
            else:
                return str(value)

        result: TwoElementTupleList = []
        for key, value in query_dict.items():
            result.append((key, convert_value(value)))

        return result


    def decode(self, query: str) -> QueryStringDict:
        """Decode a query string into a dictionary."""
        if not query:
            return OrderedDict()

        parsed : Dict[str, List[str]] = parse_qs(
            query,
            keep_blank_values=self.keep_blank_values,
            strict_parsing=self.strict_parsing,
            encoding=self.encoding,
            errors=self.errors,
            max_num_fields=self.max_num_fields,
            separator=self.separator,
        )

        return self._convert_parse_qs_to_query_string_dict(parsed)

    def encode(self, query_dict: QueryStringDict) -> str:
        """Encode a dictionary into a query string."""
        if not query_dict: return ''
        
        encoded = urlencode( query_dict, 
            doseq=self.doseq, 
            safe=self.safe, 
            quote_via=self.quote_via, 
            encoding=self.encoding, 
            errors=self.errors 
        )
        
        if self.separator != '&':
            # Only replace if & is not in safe characters (meaning it's a separator, not literal)
            if '&' not in self.safe:
                # Standard case: & is encoded as %26, so unencoded & are separators
                encoded = encoded.replace('&', self.separator)
            else:
                # Complex case: & appears literally, need to parse structure
                # Split on unencoded separators, rebuild with new separator
                parts = []
                current = ""
                i = 0
                while i < len(encoded):
                    if encoded[i] == '&':
                        # Check if this & is a separator (followed by key pattern)
                        if i + 1 < len(encoded) and (encoded[i+1].isalnum() or encoded[i+1] in '_-'):
                            parts.append(current)
                            current = ""
                        else:
                            current += '&'
                    else:
                        current += encoded[i]
                    i += 1
                parts.append(current)
                encoded = self.separator.join(parts)
                
        return encoded
