import pytest

from pgmcp.markdown_document import MdCodeBlock, MdDocument, MdListing, MdParagraph, MdSection


def find_section_by_title(sections, title):
    for section in sections:
        if section.title == title:
            return section
        found = find_section_by_title(section.children, title)
        if found:
            return found
    return None

def find_nested_listing(listing):
    for item in listing.listing_items:
        if isinstance(item, MdListing):
            return True
        if hasattr(item, 'listing_items'):
            if find_nested_listing(item):
                return True
    return False

def test_01_heading_and_paragraph():
    md = """# Title\n\nThis is a paragraph."""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    assert len(section.section_items) == 1
    para = section.section_items[0]
    assert hasattr(para, 'sentences')
    assert para.sentences[0].text == 'This is a paragraph.'

def test_02_add_unordered_list():
    md = """# Title\n\nThis is a paragraph.\n\n- Item 1\n- Item 2"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    assert any(hasattr(item, 'sentences') for item in section.section_items)
    assert any(hasattr(item, 'listing_items') for item in section.section_items)
    for item in section.section_items:
        if isinstance(item, MdListing):
            assert item.ordered is False
            assert [li.text for li in item.listing_items] == ['Item 1', 'Item 2']

def test_04_add_ordered_list():
    md = """# Title\n\n1. First\n2. Second"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    found = False
    for item in section.section_items:
        if isinstance(item, MdListing):
            found = True
            assert item.ordered is True
            assert [li.text for li in item.listing_items] == ['First', 'Second']
    assert found

def test_05_add_code_block():
    md = """# Title\n\n```python\nprint('hi')\n```"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    found = False
    for item in section.section_items:
        if hasattr(item, 'delimiter'):
            found = True
            assert item.text.strip() == "print('hi')"
            assert isinstance(item, MdCodeBlock)
            assert item.delimiter == '```'
    assert found

def test_06_add_table():
    md = """# Title\n\n| Col1 | Col2 |\n|------|------|\n| A    | B    |\n| C    | D    |"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    found = False
    for item in section.section_items:
        if hasattr(item, 'table_rows'):
            found = True
            assert len(item.table_rows) == 3              # type: ignore
            assert item.table_rows[0].cells[0].text == 'Col1'  # type: ignore
            assert item.table_rows[0].cells[1].text == 'Col2'  # type: ignore
            assert item.table_rows[1].cells[0].text == 'A'    # type: ignore
            assert item.table_rows[1].cells[1].text == 'B'    # type: ignore
            assert item.table_rows[2].cells[0].text == 'C'    # type: ignore
            assert item.table_rows[2].cells[1].text == 'D'    # type: ignore
    assert found


def test_08_paragraph_before_and_after_list():
    md = """# Title\n\nIntro paragraph.\n\n- Item 1\n- Item 2\n\nOutro paragraph."""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert section is not None
    paras = [item for item in section.section_items if hasattr(item, 'sentences')]
    lists = [item for item in section.section_items if hasattr(item, 'listing_items')]
    assert len(paras) == 2
    assert paras[0] and isinstance(paras[0], MdParagraph)
    assert paras[1] and isinstance(paras[1], MdParagraph)
    assert paras[0].sentences[0].text == 'Intro paragraph.'
    assert paras[1].sentences[0].text == 'Outro paragraph.'
    assert len(lists) == 1
    assert isinstance(lists[0], MdListing)
    assert [li.text for li in lists[0].listing_items] == ['Item 1', 'Item 2']

def test_10_code_block_in_list():
    md = """# Title\n\n- Item 1\n- Item 2\n  ```python\n  print('hi')\n  ```\n- Item 3"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    assert isinstance(section, MdSection)
    found_code = False
    for item in section.section_items:
        if isinstance(item, MdListing):
            for li in item.listing_items:
                if hasattr(li, 'text') and 'print' in li.text:
                    found_code = True
    assert found_code

def test_11_table_with_caption():
    md = """# Title\n\nTable: Example\n\n| Col1 | Col2 |\n|------|------|\n| A    | B    |"""
    doc = MdDocument.from_str(md)
    section = find_section_by_title(doc.sections, 'Title')
    # Should have a paragraph (caption) and a table
    assert section is not None
    paras = [item for item in section.section_items if hasattr(item, 'sentences')]
    tables = [item for item in section.section_items if hasattr(item, 'table_rows')]
    assert len(paras) == 1
    assert 'Table: Example' in paras[0].text
    assert len(tables) == 1
    assert tables[0].table_rows[0].cells[0].text == 'Col1' # type: ignore
    assert tables[0].table_rows[0].cells[1].text == 'Col2' # type: ignore
