from copy import deepcopy
from functools import reduce
from typing import Any, Dict


def deep_merge(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively deep merges any number of dicts into a new dict.
    - Later dicts override earlier ones.
    - Nested dicts are merged.
    - Lists/tuples: if both are lists/tuples and both elements are dicts, merge by index; else overwrite.
    - Sets: overwrite, do not union.
    - All other types: replaced by later value.
    """
    def _merge(a, b) -> Any:
        if isinstance(a, dict) and isinstance(b, dict):
            result = dict(a)
            for k, v in b.items():
                if k in result:
                    result[k] = _merge(result[k], v)
                else:
                    result[k] = v
            return result
        elif isinstance(a, list) and isinstance(b, list):
            # Merge by index if both lists and both elements are dicts
            if all(isinstance(x, dict) for x in a) and all(isinstance(x, dict) for x in b):
                length = max(len(a), len(b))
                merged = []
                for i in range(length):
                    if i < len(a) and i < len(b):
                        merged.append(_merge(a[i], b[i]))
                    elif i < len(a):
                        merged.append(a[i])
                    else:
                        merged.append(b[i])
                return merged
            else:
                return b 
        elif isinstance(a, tuple) and isinstance(b, tuple):
            # Same logic as lists
            if all(isinstance(x, dict) for x in a) and all(isinstance(x, dict) for x in b):
                length = max(len(a), len(b))
                merged = []
                for i in range(length):
                    if i < len(a) and i < len(b):
                        merged.append(_merge(a[i], b[i]))
                    elif i < len(a):
                        merged.append(a[i])
                    else:
                        merged.append(b[i])
                return tuple(merged)
            else:
                return b
        else:
            return b

    # Short circuit for empty input
    if not dicts:
        return {}
    
    # Deep Copy _all_ Dicts 
    # This avoids modifying the originals While slower, this ensures we dont end up in a situation where it's impossible
    # to track down where a bug.
    safe_dicts = [deepcopy(d) for d in dicts]
   
   
    # Short circuit if they are not all dicts
    if not all(isinstance(d, dict) for d in safe_dicts):
        raise TypeError("All arguments must be dictionaries.")
    
    # Short circuit if only one dict is provided
    if len(safe_dicts) == 1: 
        return safe_dicts[0]
    
    # Reduce to a single dict via progressive deep merging from left to right, merging one after another on top
    # of the previous one. This ensures that the last dict has the highest precedence.
    initial_seed : Dict[str, Any] = {}
    result : Dict[str, Any] = reduce(_merge, safe_dicts, initial_seed)

    return result
