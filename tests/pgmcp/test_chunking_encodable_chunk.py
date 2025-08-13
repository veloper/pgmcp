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
    })

@pytest.fixture
def encodable_chunk_simple(meta_dict, content_simple):
    return EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": content_simple,
        "model": "cl100k_base",
        "max_tokens": 8191,
    })

@pytest.fixture
def encodable_chunk_empty(empty_meta_dict):
    return EncodableChunk.model_validate({
        "meta": empty_meta_dict,
        "content": "",
        "model": "cl100k_base",
        "max_tokens": 8191,
    })

@pytest.fixture
def encodable_chunk_overflow():
    meta = {"foo": "bar"}
    return EncodableChunk.model_validate({
        "meta": meta,
        "content": "a" * 10000,
        "model": "cl100k_base",
        "max_tokens": 100,
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


def test_content_exactly_fills_budget(meta_dict):
    # Create content that exactly fills the available content_max_token_count
    chunk = EncodableChunk.model_validate({
        "meta": meta_dict,
        "content": "a",  # will adjust below
        "model": "cl100k_base",
        "max_tokens": 100,
        
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
            
        })
    assert "Impossible chunk: no room for any content" in str(excinfo.value)


def test_content_token_count_various_cases():
    encoder = EncodableChunk.model_validate({
        "meta": {}, "content": "", "model": "cl100k_base", "max_tokens": 100, 
    }).encoder
    # Empty
    chunk = EncodableChunk.model_validate({"meta": {}, "content": "", "model": "cl100k_base", "max_tokens": 100, })
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


def test_token_count_matches_serialized():
    meta = {"foo": "bar"}
    content = "baz\nqux"
    chunk = EncodableChunk.model_validate({"meta": meta, "content": content, "model": "cl100k_base", "max_tokens": 100, })
    serialized = chunk.to_str()
    assert chunk.token_count == len(chunk.encoder.encode(serialized))

def test_content_token_count_deterministic():
    chunk = EncodableChunk.model_validate({"meta": {}, "content": "hello world", "model": "cl100k_base", "max_tokens": 100, })
    expected = len(chunk.encoder.encode("hello world"))
    assert chunk.content_token_count == expected
    chunk.content = "foo"
    expected = len(chunk.encoder.encode("foo"))
    assert chunk.content_token_count == expected
    chunk.content = "你好"
    expected = len(chunk.encoder.encode("你好"))
    assert chunk.content_token_count == expected


