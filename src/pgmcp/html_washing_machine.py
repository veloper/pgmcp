import re

from functools import reduce
from typing import Callable, List, Self

from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import BaseModel, Field


class HTMLWashingMachine:
    @classmethod
    def create(cls, html: str) -> Self:
        return cls(html=html)

    def __init__(self, html: str):
        """
        Initializes the HTMLWashingMachine with the provided HTML content.
        Args:
            html (str): The HTML content to be processed.
        """
        self.html: str = html
        self.dom: BeautifulSoup = BeautifulSoup(html, "html.parser")
        self.pods: List[Callable[[BeautifulSoup], BeautifulSoup]] = []

    def with_pod(self, pod: Callable[[BeautifulSoup], BeautifulSoup]) -> Self:
        self.pods.append(pod)
        return self

    def wash(self) -> str:
        dom = self.dom
        for pod in self.pods:
            dom = pod(dom)
        return str(dom)

    def __str__(self) -> str:
        return self.wash()

    def with_custom_filter_pod(self, selector: str, filter_func: Callable[[Tag], bool]) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            for tag in dom.select(selector):
                if filter_func(tag):
                    tag.decompose()
            return dom
        return self.with_pod(pod)

    def with_existing_heading_text_replaced(
        self,
        allowed_tags: List[str] = ["p", "span", "div", "li", "a", "strong", "em", "b", "i"],
        max_distance: int = 4,
        max_length: int = 80,
        allow_newlines: bool = False,
    ) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            def is_tag_qualified(tag: Tag) -> bool:
                if tag.name not in allowed_tags:
                    return False
                text = tag.get_text(strip=True)
                if not text or len(text) > max_length:
                    return False
                if not allow_newlines and '\n' in text:
                    return False
                return True
            heading_tags = [tag for tag in dom.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]) if isinstance(tag, Tag)]
            for heading in heading_tags:
                siblings = heading.find_next_siblings()
                qualified_text = None
                siblings_checked = 0
                for sibling in siblings:
                    if siblings_checked >= max_distance:
                        break
                    if isinstance(sibling, Tag) and is_tag_qualified(sibling) and qualified_text is None:
                        qualified_text = sibling.get_text(strip=True)
                    siblings_checked += 1
                if qualified_text:
                    heading.string = qualified_text
            return dom
        return self.with_pod(pod)

    def with_non_pre_code_tags_replaced_with_backticks(self) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            from bs4.element import NavigableString
            for code_tag in dom.find_all("code"):
                if code_tag.find_parent("pre") is None:
                    code_tag.replace_with(NavigableString(f'`{code_tag.get_text()}`'))
            return dom
        return self.with_pod(pod)

    def with_dashes_encoded(self) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            from bs4.element import NavigableString, Tag
            replacements = {
                '-': '&#45;',         # Hyphen-minus (U+002D)
                '‐': '&#8208;',      # Hyphen (U+2010)
                '‑': '&#8209;',      # Non-breaking hyphen (U+2011)
                '‒': '&#8210;',      # Figure dash (U+2012)
                '–': '&#8211;',      # En dash (U+2013)
                '—': '&#8212;',      # Em dash (U+2014)
                '―': '&#8213;',      # Horizontal bar (U+2015)
                '⁃': '&#8259;',      # Bullet (U+2043)
                '−': '&#8722;',      # Minus sign (U+2212)
                '﹘': '&#65118;',     # Small em dash (U+FE58)
                '－': '&#65293;',     # Fullwidth hyphen-minus (U+FF0D)
                '⁻': '&#8315;',      # Superscript minus (U+207B)
                '₋': '&#8331;',      # Subscript minus (U+208B)
                '﹣': '&#65121;',     # Small hyphen-minus (U+FE63)
            }
            for tag in dom.find_all(True):
                if isinstance(tag, Tag) and tag.string and isinstance(tag.string, NavigableString):
                    string_content = str(tag.string)
                    for old, new in replacements.items():
                        string_content = string_content.replace(old, new)
                    tag.string.replace_with(NavigableString(string_content))
            return dom
        return self.with_pod(pod)

    def with_empty_tags_removed(self, tags: List[str] | None = None) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            empty_tags_to_remove = tags or ['br', 'hr', 'p', 'div', 'span']
            for tag_name in empty_tags_to_remove:
                for tag in dom.find_all(tag_name):
                    if isinstance(tag, Tag):
                        if not tag.get_text(strip=True):
                            tag.decompose()
            return dom
        return self.with_pod(pod)

    def with_tags_converted_to_heading(
        self,
        selector: str,
        level: int | Callable[[Tag], int],
        keep_attrs: bool = False,
    ) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            for tag in dom.select(selector):
                tag.name = f"h{level(tag) if callable(level) else level}"
                if not keep_attrs:
                    tag.attrs.clear()
            return dom
        return self.with_pod(pod)

    def with_tags_removed(
        self,
        selector: str,
    ) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            for tag in dom.select(selector):
                tag.decompose()
            return dom
        return self.with_pod(pod)

    def with_script_tags_removed(self) -> Self: return self.with_tags_removed("script")
    def with_style_tags_removed(self) -> Self: return self.with_tags_removed("style")
    def with_img_tags_removed(self) -> Self: return self.with_tags_removed("img")
    def with_link_tags_removed(self) -> Self: return self.with_tags_removed("link")
    def with_meta_tags_removed(self) -> Self: return self.with_tags_removed("meta")
    def with_comments_removed(self) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            comments = dom.find_all(
                string=lambda text: isinstance(text, str) and bool(re.match(r'^\s*<!--.*?-->\s*$', text, re.DOTALL))
            )
            for comment in comments:
                comment.extract()
            return dom
        return self.with_pod(pod)
    
    def with_tags_before_h1_removed(self) -> Self:
        """Remove all tags and non-tag nodes before the first h1 tag's top level ancestor, while also ensuring all ancestors have their prior siblings to the h1 removed as well
        so as to prevent anything _visually_ appearing before the h1 tag.
        """
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            h1 = dom.find("h1")
            if not isinstance(h1, Tag):
                return dom
    
            # Remove all content before the top-level ancestor containing h1
            top_ancestor = h1
            while (top_ancestor.parent is not None and 
                   isinstance(top_ancestor.parent, Tag) and 
                   top_ancestor.parent.name != "body"):
                top_ancestor = top_ancestor.parent
            
            if (top_ancestor.parent is not None and 
                isinstance(top_ancestor.parent, Tag)):
                for sibling in list(top_ancestor.previous_siblings):
                    if hasattr(sibling, 'extract'):
                        sibling.extract()
    
            # For each ancestor up to top_ancestor, remove all siblings before the child in the chain
            node = h1
            while node != top_ancestor and isinstance(node.parent, Tag):
                parent = node.parent
                for sibling in list(node.previous_siblings):
                    if hasattr(sibling, 'extract'):
                        sibling.extract()
                node = parent
    
            return dom
        return self.with_pod(pod)
    
    def with_readability_applied(self) -> Self:
        from readability import Document
        """Apply readability-lxml to the HTML content and transform the dom into the Document's content."""
        
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            current_html = str(dom)
            doc = Document(current_html)
            html = doc.summary()
            
            # We need to now decide which is the better candidate, original HTML, or what was used prior to this point.
            # for now, we'll err on the side of a ratio of 0.1, meaning if the readability content is less than 10%
            # the original HTML, we'll use the original HTML.
            original_length = len(current_html)
            readability_length = len(html)
            ratio = 0.1
            use_readability = readability_length >= (original_length * ratio)
            
            if use_readability:
                return BeautifulSoup(html, "html.parser")
            else:
                return dom
            
        
        return self.with_pod(pod)

    
    def with_possible_buttons_removed(self) -> Self:
        """Heuristically remove elements likely to be buttons, but do not remove .not-a-button elements."""

        # Probable button texts and combinations, must match exact after stripping surrounding whitespace and images so as to catch cases like "img src='...' alt='copy' /> Copy".
        BUTTON_TEXTS = [
            "copy", "copy to clipboard", "copy link", "share", "download",
            "read more", "learn more", "view more", "see more", "more", "open", "close",
            "submit", "cancel", "ok", "yes", "no", "apply", "reset", "save", "edit",
            "delete", "remove", "add", "create", "update", "change", "select", "choose",
            "like", "dislike", "upvote", "downvote", "vote", "rate", "review", "comment",
            "search", "filter", "sort", "next", "previous", "ask ai", "+1", "-1",
        ]
        BUTTON_TEXTS.extend([f"{t}{s}" for t in BUTTON_TEXTS for s in ["...", " ...", " …", "…", ".", "!", "?"]])
        
        BUTTON_CLASSES = {
            "btn", "button", "btn-primary", "btn-secondary", "btn-success", "btn-danger", "btn-warning", "btn-info",
            "btn-light", "btn-dark", "btn-muted", "btn-xl", "btn-lg", "btn-md", "btn-sm", "btn-xs", "btn-tiny",
            "btn-block", "btn-group", "btn-toolbar"
        }
        
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            # 1) Remove any tag with a button class we care about
            for tag in dom.select(",".join([f".{class_name}" for class_name in BUTTON_CLASSES])):
                tag.decompose()

            
            # 2) Iterate over all remaining tags and check their get_text(strip=True).lower() if in BUTTON_TEXTS
            for tag in dom.find_all(True):
                if isinstance(tag, Tag):
                    if text := tag.get_text(strip=True).lower():
                        if text in BUTTON_TEXTS: 
                            tag.decompose()
                        
                
            return dom            
        
        return self.with_pod(pod)
