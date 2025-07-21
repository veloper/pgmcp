import io, logging

from typing import List, Type, TypeVar, Union

import mistletoe, nltk

from mistletoe.block_token import CodeFence, Heading
from mistletoe.block_token import List as MdList
from mistletoe.block_token import Paragraph as MdParagraph
from mistletoe.block_token import Table as MdTable

# Use a module alias to prevent circular import issues while allowing type hinting.
from pgmcp import markdown_document as md


# TypeVar for generic Document parsing, allowing for subclassing.
T = TypeVar("T", bound=md.MdDocument)


class MarkdownParser:
    """
    Parses a markdown string into a structured Document object.
    This parser separates the parsing logic from the Pydantic data models,
    ensuring a clean separation of concerns.
    """

    def parse(self, text: str, doc_class: Type[T], title: str | None = None) -> T:
        """
        Main entry point for parsing markdown text.
        Args:
            text: The markdown string to parse.
            doc_class: The class to instantiate for the document (e.g., Document or a subclass).
        Returns:
            An instance of doc_class representing the structured content.
        """
        
        ast = mistletoe.Document(io.StringIO(text))
        sections = self._build_sections(list(ast.children or []))
        doc = doc_class.model_validate({
            "text": text,
            "sections": sections,
            "title": title if title else None
        })
        return doc

    def _extract_text(self, token) -> str:
        """Recursively extracts all text content from a mistletoe token."""
        # For tokens with children, extract from children first
        if hasattr(token, "children") and token.children:
            parts = []
            for child in token.children:
                if child:  # Make sure child is not None
                    child_text = self._extract_text(child)
                    if child_text:
                        parts.append(child_text)
            if parts:
                return "".join(parts)
        
        # Handle tokens with direct content (like RawText)
        if hasattr(token, "content") and token.content is not None:
            return str(token.content)
        
        return ""

    def _split_sentences(self, paragraph_text: str) -> List[md.MdSentence]:
        """Uses NLTK for robust sentence splitting, downloading 'punkt' if necessary."""
        try:
            sentence_texts = nltk.sent_tokenize(paragraph_text)
        except LookupError:
            
            nltk.download('punkt', quiet=True)
            sentence_texts = nltk.sent_tokenize(paragraph_text)
        
        return [md.MdSentence(text=sentence_text) for sentence_text in sentence_texts]

    def _generate_table_text(self, token) -> str:
        """Generate the markdown text representation of a table."""
        lines = []
        
        # Add header row if it exists
        if hasattr(token, 'header') and token.header:
            header_cells = [self._extract_text(cell).strip() for cell in token.header.children or []]
            lines.append("| " + " | ".join(header_cells) + " |")
            # Separator row
            lines.append("|" + "|".join(["-" * (len(cell) + 2) for cell in header_cells]) + "|")
        
        # Add data rows
        for row in token.children or []:
            cells = [self._extract_text(cell).strip() for cell in row.children or []]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def _generate_list_text(self, token, is_ordered: bool, indent_level: int = 0) -> str:
        """Generate the markdown text representation of a list with proper indentation."""
        lines = []
        indent = "  " * indent_level  # 2 spaces per indent level
        
        for i, item in enumerate(token.children or []):
            item_text = ""
            # Extract text from the item, handling nested lists
            for child in item.children or []:
                if isinstance(child, MdList):
                    # This is a nested list
                    nested_ordered = hasattr(child, "start") and child.start is not None
                    nested_text = self._generate_list_text(child, nested_ordered, indent_level + 1)
                    item_text += "\n" + nested_text if item_text else nested_text
                else:
                    # Regular text content
                    child_text = self._extract_text(child)
                    if child_text.strip():
                        item_text += child_text if not item_text else " " + child_text
            
            if is_ordered:
                lines.append(f"{indent}{i + 1}. {item_text}")
            else:
                lines.append(f"{indent}- {item_text}")
        
        return "\n".join(lines)

    def _parse_block(self, token) -> Union[md.MdParagraph, md.MdListing, md.MdTable, md.MdCodeBlock, dict, None]:
        """Converts a single mistletoe token into a Pydantic model or a heading dict."""
        if isinstance(token, Heading):
            return {"type": "heading", "level": token.level, "title": self._extract_text(token)}
        
        if isinstance(token, MdParagraph):
            para_text = self._extract_text(token)
            return md.MdParagraph(text=para_text, sentences=self._split_sentences(para_text))
        
        if isinstance(token, MdList):
            items = []
            is_ordered = hasattr(token, "start") and token.start is not None
            
            for item in token.children or []:
                item_content = []
                nested_items = []
                
                for child in item.children or []:
                    if isinstance(child, MdList):
                        # This is a nested list - parse it recursively
                        nested_block = self._parse_block(child)
                        if nested_block:
                            nested_items.append(nested_block)
                    else:
                        # Regular text content
                        child_text = self._extract_text(child).strip()
                        if child_text:
                            item_content.append(child_text)
                
                # Create the main item text
                main_text = " ".join(item_content) if item_content else ""
                if main_text:
                    items.append(md.MdListingItem(text=main_text))
                
                # Add any nested list items
                items.extend(nested_items)
            
            list_text = self._generate_list_text(token, is_ordered, 0)
            return md.MdListing(text=list_text, listing_items=items, ordered=is_ordered)

        if isinstance(token, CodeFence):
            return md.MdCodeBlock(
                text=self._extract_text(token),
                delimiter="```",
                language_id=token.language or None,
            )

        if isinstance(token, MdTable):
            table_rows = []
            
            # Include header row if it exists
            if hasattr(token, 'header') and token.header:
                header_cells = [md.MdTableRowCell(text=self._extract_text(cell).strip()) for cell in token.header.children or []]
                header_text = "| " + " | ".join([cell.text for cell in header_cells]) + " |"
                table_rows.append(md.MdTableRow(text=header_text, cells=header_cells))
            
            # Include data rows
            for row in token.children or []:
                cell_objects = [md.MdTableRowCell(text=self._extract_text(cell).strip()) for cell in row.children or []]
                # Generate proper markdown row text with spacing
                row_text = "| " + " | ".join([cell.text for cell in cell_objects]) + " |"
                table_rows.append(md.MdTableRow(text=row_text, cells=cell_objects))
            
            table_text = self._generate_table_text(token)
            return md.MdTable(text=table_text, table_rows=table_rows)

        fallback_text = self._extract_text(token)
        if fallback_text.strip():
            return md.MdParagraph(text=fallback_text, sentences=self._split_sentences(fallback_text))
        
        return None

    def _build_sections(self, tokens: List) -> List[md.MdSection]:
        """Builds a hierarchical list of Section objects from a flat list of tokens."""
        root = {"level": 0, "title": "root", "section_items": []}
        stack = [root]
        
        for i, token in enumerate(tokens):
            block = self._parse_block(token)
            if not block:
                continue

            if isinstance(block, dict) and block.get("type") == "heading":
                # Pop stack until we find a section with a lower level
                while len(stack) > 1 and block["level"] <= stack[-1]["level"]:
                    stack.pop()
                
                new_section_dict = {
                    "level": block["level"],
                    "title": block["title"],
                    "text": "",
                    "section_items": [],
                }
                # Add the new section as a section_item to its parent
                stack[-1]["section_items"].append(new_section_dict)
                stack.append(new_section_dict)
            else:
                stack[-1]["section_items"].append(block)

        return [self._convert_dict_to_section(s) for s in root["section_items"] if isinstance(s, dict) and "level" in s]

    def _generate_section_text(self, section_dict: dict, processed_items: List) -> str:
        """Generate the markdown text representation of a section."""
        lines = []
        
        # Add the heading
        heading_prefix = "#" * section_dict["level"]
        lines.append(f"{heading_prefix} {section_dict['title']}")
        lines.append("")  # Empty line after heading
        
        # Add content items, preserving their markdown representation
        for item in processed_items:
            if isinstance(item, md.MdCodeBlock):
                # For code blocks, include the delimiters and language
                lang_part = item.language_id if item.language_id else ""
                lines.append(f"```{lang_part}")
                lines.append(item.text.rstrip())  # Remove trailing newline to avoid double newlines
                lines.append("```")
                lines.append("")  # Empty line after code block
            elif hasattr(item, "text") and not isinstance(item, md.MdSection):
                lines.append(item.text)
                lines.append("")  # Empty line between items
            elif isinstance(item, md.MdSection):
                # For nested sections, we'll include their text representation
                lines.append(item.text)
                lines.append("")
        
        # Remove trailing empty lines
        while lines and lines[-1] == "":
            lines.pop()
        
        return "\n".join(lines)

    def _convert_dict_to_section(self, section_dict: dict) -> md.MdSection:
        """Recursively converts an intermediate dictionary into a final Section model."""
        # Process section_items: convert section dicts to Section objects, keep other items as-is
        processed_items = []
        for item in section_dict.get("section_items", []):
            if isinstance(item, dict) and "level" in item:
                # This is a subsection dict, convert it to a Section
                processed_items.append(self._convert_dict_to_section(item))
            else:
                # This is a regular content item (Paragraph, Listing, Table, CodeBlock)
                processed_items.append(item)
        
        # Build text content using proper markdown representation
        text_content = self._generate_section_text(section_dict, processed_items)

        return md.MdSection(
            text=text_content,
            level=section_dict["level"],
            title=section_dict["title"],
            section_items=processed_items,
        )
