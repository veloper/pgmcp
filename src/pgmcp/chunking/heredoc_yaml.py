from io import StringIO
from typing import ClassVar

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString


class HeredocYAML:
    """Utility to dump dicts/lists/strings to YAML with heredocs for strings.
    
    This specially avoids miscounts of complex utf-8 characters that can happen with
    standard YAML serialization. Using a heredoc ensures that the content is preserved
    with only a single `|-` to indicate a literal block scalar, and no escaping or other
    transformations that can affect token counts.
    """

    _yaml: ClassVar[YAML] = YAML(typ="rt")
    _yaml.default_flow_style = False
    _yaml.allow_unicode = True
    _yaml.indent(mapping=2, sequence=4, offset=2)

    @classmethod
    def heredocify(cls, val):
        """Recursively convert all strings in dicts, lists, tuples, and sets to LiteralScalarString."""
        if isinstance(val, str):
            return LiteralScalarString(val)
        elif isinstance(val, dict):
            return {k: cls.heredocify(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [cls.heredocify(v) for v in val]
        elif isinstance(val, tuple):
            return tuple(cls.heredocify(v) for v in val)
        elif isinstance(val, set):
            return {cls.heredocify(v) for v in val}
        else:
            return val

    @classmethod
    def dump(cls, val) -> str:
        buf = StringIO()
        cls._yaml.dump(cls.heredocify(val), buf)
        return buf.getvalue()

    @classmethod
    def load(cls, yaml_str: str):
        return cls._yaml.load(yaml_str)
