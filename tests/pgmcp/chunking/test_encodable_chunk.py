from textwrap import dedent

import pytest

from pgmcp.chunking.chunk_meta import ChunkMeta
from pgmcp.chunking.encodable_chunk import EncodableChunk


@pytest.fixture
def meta_dict():
    return {"heading": "Section 1", "extra": 42}

@pytest.fixture
def content_multiline():
    return "line1\nline2\n  indented\n"

@pytest.fixture
def content_simple():
    return "foo\nbar\n"

@pytest.fixture
def empty_meta_dict():
    return {}

@pytest.fixture
def encodable_chunk(meta_dict, content_multiline):
    return EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": content_multiline,
        "model": "cl100k_base",
        "max_tokens": 8191,
        "reserve_tokens": 0
    })

@pytest.fixture
def encodable_chunk_simple(meta_dict, content_simple):
    return EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": content_simple,
        "model": "cl100k_base",
        "max_tokens": 8191,
        "reserve_tokens": 0
    })

@pytest.fixture
def encodable_chunk_empty(empty_meta_dict):
    return EncodableChunk.model_validate({
        "meta": empty_meta_dict,
        "content": "",
        "model": "cl100k_base",
        "max_tokens": 8191,
        "reserve_tokens": 0
    })

@pytest.fixture
def encodable_chunk_overflow():
    meta = {"foo": "bar"}
    return EncodableChunk.model_validate({
        "meta": meta,
        "content": "a" * 10000,
        "model": "cl100k_base",
        "max_tokens": 100,
        "reserve_tokens": 0
    })

@pytest.fixture
def complex_meta():
    return {
        "title": "PostgreSQL",
        "part_id": 27,
        "Header 1": "PostgreSQL¶",
        "Header 2": "PostgreSQL Data Types¶"
    }


@pytest.fixture
def encodable_chunk_complex(complex_meta, complex_content):
    return EncodableChunk.model_validate({
        "meta": complex_meta,
        "content": complex_content,
        "model": "cl100k_base",
        "max_tokens": 8191,
        "reserve_tokens": 0
    })

def test_yaml_heredoc_content(encodable_chunk, content_multiline):
    yaml_str = encodable_chunk.to_str()
    assert "content: |" in yaml_str
    # Check each line with YAML indentation
    for line in content_multiline.splitlines():
        indented_line = f"  {line}" if line.strip() else ""
        assert indented_line in yaml_str
    assert "meta:" in yaml_str and "heading:" in yaml_str

def test_empty_content_and_meta(encodable_chunk_empty):
    yaml_str = encodable_chunk_empty.to_str()
    assert "content: |" in yaml_str
    assert "meta:" in yaml_str
    assert encodable_chunk_empty.content_token_count == 0
    assert encodable_chunk_empty.meta_token_count >= 0
    assert encodable_chunk_empty.token_count == len(encodable_chunk_empty.encoder.encode(yaml_str))

def test_overflowing(encodable_chunk_overflow):
    assert encodable_chunk_overflow.is_overflowing

def test_yaml_meta_is_mapping(encodable_chunk):
    yaml_str = encodable_chunk.to_str()
    # Meta should be a YAML mapping, not a string or scalar
    assert "meta:" in yaml_str
    assert "heading:" in yaml_str
    assert not any(line.strip().startswith('meta: |') for line in yaml_str.splitlines())

def test_yaml_content_is_heredoc(encodable_chunk):
    yaml_str = encodable_chunk.to_str()
    # Content must always be a heredoc (literal block scalar)
    assert "content: |" in yaml_str
    # There should be no 'content:' line without '|'
    assert not any(line.strip() == 'content:' for line in yaml_str.splitlines())

def test_yaml_envelope_structure(encodable_chunk):
    yaml_str = encodable_chunk.to_str()
    # Envelope must start with meta, then content, with correct indentation
    lines = yaml_str.splitlines()
    meta_idx = next(i for i, l in enumerate(lines) if l.strip().startswith('meta:'))
    content_idx = next(i for i, l in enumerate(lines) if l.strip().startswith('content: |'))
    assert meta_idx < content_idx
    # There should be no curly braces (JSON) in the YAML output
    assert '{' not in yaml_str and '}' not in yaml_str

def test_complex_yaml_output(encodable_chunk_complex, complex_meta, complex_content):
    yaml_str = encodable_chunk_complex.to_str()
    # Meta keys and values must appear in YAML
    for k, v in complex_meta.items():
        assert f"{k}:" in yaml_str
        if isinstance(v, str):
            assert v in yaml_str
        else:
            assert str(v) in yaml_str
    # Content must be heredoc and match input (with YAML indentation)
    assert "content: |" in yaml_str
    for line in complex_content.splitlines():
        if line.strip():
            assert f"  {line}" in yaml_str
    # Envelope structure
    assert yaml_str.strip().startswith("meta:")
    # Only check for curly braces in meta, not in content
    meta_end = yaml_str.index('content: |')
    meta_yaml = yaml_str[:meta_end]
    assert '{' not in meta_yaml and '}' not in meta_yaml

def test_complex_token_accounting(encodable_chunk_complex, complex_meta, complex_content):
    # Raw content token count
    assert encodable_chunk_complex.content_token_count == len(encodable_chunk_complex.encoder.encode(complex_content))
    # Meta token count (YAML-serialized meta)
    from io import StringIO

    from ruamel.yaml import YAML
    yaml = YAML(typ="rt")
    buf = StringIO()
    yaml.dump(complex_meta, buf)
    meta_yaml = buf.getvalue().rstrip()
    expected_meta_tokens = len(encodable_chunk_complex.encoder.encode(meta_yaml))
    assert encodable_chunk_complex.meta_token_count == expected_meta_tokens
    # Envelope token count is static
    chunk2 = EncodableChunk.model_validate({
        "meta": {"foo": "bar"},
        "content": "baz",
        "model": "cl100k_base",
        "max_tokens": 8191,
        "reserve_tokens": 0
    })
    assert encodable_chunk_complex.envelope_token_count == chunk2.envelope_token_count
    # Overhead is sum
    expected_overhead = (
        encodable_chunk_complex.meta_token_count +
        encodable_chunk_complex.envelope_token_count +
        encodable_chunk_complex.reserve_token_count
    )
    assert encodable_chunk_complex.overhead_token_count == expected_overhead
    # Max and remaining
    expected_max = max(0, encodable_chunk_complex.max_token_count - encodable_chunk_complex.overhead_token_count)
    assert encodable_chunk_complex.content_max_token_count == expected_max
    expected_remaining = max(0, encodable_chunk_complex.content_max_token_count - encodable_chunk_complex.content_token_count)
    assert encodable_chunk_complex.content_remaining_token_count == expected_remaining
    # to_str() output is YAML
    yaml_str = encodable_chunk_complex.to_str()
    assert yaml_str.strip().startswith("meta:")
    assert "content: |" in yaml_str
    # Only check for curly braces in meta, not in content
    meta_end = yaml_str.index('content: |')
    meta_yaml = yaml_str[:meta_end]
    assert '{' not in meta_yaml and '}' not in meta_yaml

def test_content_exactly_fills_budget(meta_dict):
    # Create content that exactly fills the available content_max_token_count
    chunk = EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": "a",  # will adjust below
        "model": "cl100k_base",
        "max_tokens": 100,
        "reserve_tokens": 0
    })
    encoder = chunk.encoder
    # Find the max content length that fits without overflowing
    for i in range(1, 1000):
        s = "a" * i
        chunk.content = s
        if chunk.is_overflowing:
            break
    else:
        i = 1000
    s = "a" * (i - 1)
    chunk.content = s
    assert not chunk.is_overflowing
    # Now add one more token, should overflow
    chunk.content = s + "a"
    assert chunk.is_overflowing

def test_reserve_token_boundary(meta_dict):
    # Reserve tokens that push content over the limit by one
    chunk = EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": "a",
        "model": "cl100k_base",
        "max_tokens": 50,
        "reserve_tokens": 0
    })
    encoder = chunk.encoder
    # Find the max content length that fits without overflowing
    for i in range(1, 1000):
        s = "a" * i
        chunk.content = s
        if chunk.is_overflowing:
            break
    else:
        i = 1000
    s = "a" * (i - 1)
    chunk.content = s
    assert not chunk.is_overflowing
    # Now add one reserve token, should overflow
    chunk.reserve_tokens = 1
    assert chunk.is_overflowing

def test_impossible_state_empty_content_no_room(meta_dict):
    """Impossible: reserve + meta + envelope leaves no room for content."""
    import pytest
    with pytest.raises(ValueError) as excinfo:
        EncodableChunk.model_validate({
            "meta": meta_dict,
            "content": "",
            "model": "cl100k_base",
            "max_tokens": 10,
            "reserve_tokens": 10
        })
    assert "Impossible chunk: no room for any content" in str(excinfo.value)

def test_impossible_state_meta_too_large():
    """Impossible: meta + envelope alone leaves no room for content."""
    import pytest
    meta = {"a": "x" * 1000}  # Large meta
    with pytest.raises(ValueError) as excinfo:
        EncodableChunk.model_validate({
            "meta": meta,
            "content": "",
            "model": "cl100k_base",
            "max_tokens": 5,
            "reserve_tokens": 0
        })
    assert "Impossible chunk: no room for any content" in str(excinfo.value)

def test_impossible_state_reserve_too_large(meta_dict):
    """Impossible: reserve tokens alone leave no room for content."""
    import pytest
    with pytest.raises(ValueError) as excinfo:
        EncodableChunk.model_validate({
            "meta": meta_dict,
            "content": "",
            "model": "cl100k_base",
            "max_tokens": 5,
            "reserve_tokens": 10
        })
    assert "Impossible chunk: no room for any content" in str(excinfo.value)

def test_content_token_count_various_cases():
    encoder = EncodableChunk.model_validate({
        "meta": {}, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0
    }).encoder
    # Empty
    chunk = EncodableChunk.model_validate({"meta": {}, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    assert chunk.content_token_count == 0
    # ASCII
    chunk.content = "abc def"
    assert chunk.content_token_count == len(encoder.encode("abc def"))
    # Unicode
    chunk.content = "你好，世界"
    assert chunk.content_token_count == len(encoder.encode("你好，世界"))
    # Multiline
    chunk.content = "foo\nbar\nbaz"
    assert chunk.content_token_count == len(encoder.encode("foo\nbar\nbaz"))

def test_meta_token_count_various_cases():
    encoder = EncodableChunk.model_validate({
        "meta": {}, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0
    }).encoder
    from io import StringIO

    from ruamel.yaml import YAML

    # Empty dict
    meta = {}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    assert chunk.meta_token_count == len(encoder.encode(meta_yaml))
    # Nested dict
    meta = {"a": {"b": 1}}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    assert chunk.meta_token_count == len(encoder.encode(meta_yaml))
    # Long value
    meta = {"long": "x" * 100}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 200, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    assert chunk.meta_token_count == len(encoder.encode(meta_yaml))
    # Unicode
    meta = {"greet": "你好"}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    assert chunk.meta_token_count == len(encoder.encode(meta_yaml))

def test_envelope_token_count_deterministic():
    meta = {"a": 1}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "foo", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    # Envelope token count should be the same for any chunk with same structure
    chunk2 = EncodableChunk.model_validate({"meta": {"foo": "bar"}, "content": "baz", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    assert chunk.envelope_token_count == chunk2.envelope_token_count

def test_overhead_token_count_is_sum_various():
    meta = {"a": "b"}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "foo", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 5})
    expected = chunk.meta_token_count + chunk.envelope_token_count + chunk.reserve_token_count
    assert chunk.overhead_token_count == expected
    # Change reserve
    chunk.reserve_tokens = 10
    expected = chunk.meta_token_count + chunk.envelope_token_count + chunk.reserve_token_count
    assert chunk.overhead_token_count == expected
    # Change meta
    chunk.meta = type(chunk.meta).model_validate({"a": "long" * 10})
    expected = chunk.meta_token_count + chunk.envelope_token_count + chunk.reserve_token_count
    assert chunk.overhead_token_count == expected

def test_content_max_and_remaining_token_count():
    meta = {"a": "b"}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "foo", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    expected_max = max(0, chunk.max_token_count - chunk.overhead_token_count)
    assert chunk.content_max_token_count == expected_max
    expected_remaining = max(0, chunk.content_max_token_count - chunk.content_token_count)
    assert chunk.content_remaining_token_count == expected_remaining
    # Edge: incrementally fill content until just before overflow
    encoder = chunk.encoder
    base = "a"
    for i in range(1, 1000):
        s = base * i
        chunk.content = s
        if chunk.is_overflowing:
            break
    else:
        i = 1000
    s = base * (i - 1)
    chunk.content = s
    # Should not be overflowing, remaining tokens should be >= 0
    assert not chunk.is_overflowing
    assert chunk.content_remaining_token_count >= 0
    # Now add one more character, should overflow
    chunk.content = s + base
    assert chunk.is_overflowing

def test_token_count_matches_serialized():
    meta = {"foo": "bar"}
    content = "baz\nqux"
    chunk = EncodableChunk.model_validate({"meta": meta, "content": content, "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    serialized = chunk.to_str()
    assert chunk.token_count == len(chunk.encoder.encode(serialized))

def test_content_token_count_deterministic():
    chunk = EncodableChunk.model_validate({"meta": {}, "content": "hello world", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    expected = len(chunk.encoder.encode("hello world"))
    assert chunk.content_token_count == expected
    chunk.content = "foo"
    expected = len(chunk.encoder.encode("foo"))
    assert chunk.content_token_count == expected
    chunk.content = "你好"
    expected = len(chunk.encoder.encode("你好"))
    assert chunk.content_token_count == expected

def test_meta_token_count_deterministic():
    from io import StringIO

    from ruamel.yaml import YAML
    meta = {"a": 1}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    expected = len(chunk.encoder.encode(meta_yaml))
    assert chunk.meta_token_count == expected
    meta = {"foo": "bar"}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    buf = StringIO(); YAML(typ="rt").dump(meta, buf); meta_yaml = buf.getvalue().rstrip()
    expected = len(chunk.encoder.encode(meta_yaml))
    assert chunk.meta_token_count == expected

def test_overhead_token_count_deterministic():
    meta = {"a": 1}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "foo", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 2})
    expected = chunk.meta_token_count + chunk.envelope_token_count + chunk.reserve_token_count
    assert chunk.overhead_token_count == expected

def test_overflow_deterministic():
    meta = {"a": 1}
    chunk = EncodableChunk.model_validate({"meta": meta, "content": "foo", "model": "cl100k_base", "max_tokens": 100, "reserve_tokens": 0})
    # Find the minimum max_tokens that does not overflow
    total = chunk.meta_token_count + chunk.envelope_token_count + chunk.content_token_count
    chunk.max_tokens = total
    assert not chunk.is_overflowing
    # Now reduce max_tokens by 1, should overflow
    chunk.max_tokens = total - 1
    assert chunk.is_overflowing

