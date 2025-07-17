import hashlib, os, pickle, re, time

from asyncio import run
from collections import defaultdict
from copy import deepcopy
from functools import reduce
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Self, cast

import aiofiles, html2text, markdown2, trafilatura

from bs4 import BeautifulSoup
from bs4.element import Tag
from httpx import AsyncClient, Response
from markdownify import MarkdownConverter
from markdownify import markdownify as md
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from rich import inspect
from rich.console import Console
from rich.pretty import Pretty
from trafilatura.metadata import Document
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import CompositeElement, Element, ElementMetadata, Title
from unstructured.partition.html import partition_html
from unstructured.partition.md import partition_md

from pgmcp.custom_markdown_converter import CustomMarkdownConverter
from pgmcp.html_washing_machine import HTMLWashingMachine


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



def pretty_print(obj: Any) -> None:
    console = Console()
    console.print(Pretty(obj, indent_guides=True, expand_all=True, max_depth=4))

async def fetch_url(url: str, cache: bool = False, cache_dir: str = "/tmp/fetch_cache", ttl: int = 7 * 24 * 60 * 60) -> Response:
    """
    Fetches the content of a URL asynchronously using httpx, with optional caching.

    Args:
        url (str): The URL to fetch.
        cache (bool): Whether to use caching. Defaults to False.
        cache_dir (str): Directory to store cache files. Defaults to "/tmp/fetch_cache".
        ttl (int): Cache validity in seconds. Defaults to 1 week.

    Returns:
        Response: The HTTP response object.
    """
    if not cache:
        async with AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response

    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    cache_file_path = directory / f"{hashlib.md5(url.encode()).hexdigest()}.pkl"

    def is_cache_valid(path):
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < ttl

    if is_cache_valid(cache_file_path):
        async with aiofiles.open(cache_file_path, "rb") as f:
            data = await f.read()
            response = pickle.loads(data)
            return response
    else:
        async with AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        async with aiofiles.open(cache_file_path, "wb") as f:
            await f.write(pickle.dumps(response))
        return response


def convert_html_to_markdown_content(
    html: str,
) -> str:
    """
    Converts HTML content to Markdown.
    
    Uses:
        - `HTMLWashingMachine` to package the cleaning pipeline.
        - `readability-py` augment content extraction.
        - `markdownify` to convert the washed HTML to Markdown.
    
    Args:
        html (str): The HTML content to convert.

    Returns
        str: The converted Markdown content.
    """
    machine = HTMLWashingMachine.create(html) \
        .with_dashes_encoded() \
        .with_tags_before_h1_removed() \
        .with_non_pre_code_tags_replaced_with_backticks() \
        .with_script_tags_removed() \
        .with_style_tags_removed() \
        .with_meta_tags_removed() \
        .with_link_tags_removed() \
        .with_possible_buttons_removed() \
        .with_readability_applied()

    clean_html = machine.wash()
    
    converter = CustomMarkdownConverter()
    markdown_text = converter.convert(clean_html)
    
    return markdown_text

    
    
    return markdown_content

async def amain():
    """
    Example usage of the utility functions.
    """
    console = Console()
    
    # Fetch a URL
    console.log("Fetching URL...")
    url = "https://docs.unstructured.io/open-source/core-functionality/chunking"
    # url = "https://python.langchain.com/api_reference/unstructured/document_loaders/langchain_unstructured.document_loaders.UnstructuredLoader.html#langchain_unstructured.document_loaders.UnstructuredLoader"
    # url = "https://docs.scrapy.org/en/latest/topics/spiders.html"
    response = await fetch_url(url)

    

    raw_html = response.text
    
    markdown_text = convert_html_to_markdown_content(raw_html)
        
    console.log("Normalized HTML:")

    print(markdown_text)
    exit(0)


    

    

if __name__ == "__main__":
    run(amain())


