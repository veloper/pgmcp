"""HTML cleaning and preprocessing utilities for the chunking pipeline."""

import re, time

from functools import reduce
from typing import Callable, List, Self

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from pydantic import BaseModel, Field


class Pod:
    """A processing pod that wraps a function and tracks execution time."""
    
    def __init__(self, func: Callable[[BeautifulSoup], BeautifulSoup], name: str | None = None):
        self.func = func
        self.name = name or "Unnamed Pod"
        self.last_elapsed_ms: float = 0.0
    
    def __call__(self, dom: BeautifulSoup) -> BeautifulSoup:
        start = time.time()
        result = self.func(dom)
        self.last_elapsed_ms = (time.time() - start) * 1000
        return result


class HTMLWashingMachine:
    """A fluent API for cleaning and preprocessing HTML content for chunking.
    
    This class provides a pipeline of HTML preprocessing operations specifically
    designed to prepare HTML content for text extraction and chunking operations.
    """
    
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
        self.pods: List[Pod] = []

    def with_pod(self, pod: Callable[[BeautifulSoup], BeautifulSoup], *, report_name: str | None = None) -> Self:
        self.pods.append(Pod(pod, report_name or "Unnamed Pod"))
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
        return self.with_pod(pod, report_name="with_custom_filter_pod")

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
        return self.with_pod(pod, report_name="with_existing_heading_text_replaced")

    def with_non_pre_code_tags_replaced_with_backticks(self) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            from bs4.element import NavigableString
            for code_tag in dom.find_all("code"):
                if code_tag.find_parent("pre") is None:
                    code_tag.replace_with(NavigableString(f'`{code_tag.get_text()}`'))
            return dom
        return self.with_pod(pod, report_name="with_non_pre_code_tags_replaced_with_backticks")

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
        return self.with_pod(pod, report_name="with_dashes_encoded")

    def with_empty_tags_removed(self, tags: List[str] | None = None) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            empty_tags_to_remove = tags or ['br', 'hr', 'p', 'div', 'span']
            for tag_name in empty_tags_to_remove:
                for tag in dom.find_all(tag_name):
                    if isinstance(tag, Tag):
                        if not tag.get_text(strip=True):
                            tag.decompose()
            return dom
        return self.with_pod(pod, report_name="with_empty_tags_removed")

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
        return self.with_pod(pod, report_name="with_tags_converted_to_heading")

    def with_tags_removed(
        self,
        selector: str,
    ) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            for tag in dom.select(selector):
                tag.decompose()
            return dom
        return self.with_pod(pod, report_name="with_tags_removed")

    def with_script_tags_removed(self) -> Self: return self.with_tags_removed("script")
    def with_style_tags_removed(self) -> Self: return self.with_tags_removed("style")
    def with_img_tags_removed(self) -> Self: return self.with_tags_removed("img")
    def with_link_tags_removed(self) -> Self: return self.with_tags_removed("link")
    def with_meta_tags_removed(self) -> Self: return self.with_tags_removed("meta")
    def with_comments_removed(self) -> Self:
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            # Remove all HTML comments <!-- ... -->
            comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
            for comment in dom.find_all(string=comment_pattern):
                comment.extract()
            return dom
        return self.with_pod(pod, report_name="with_comments_removed")
    
    def with_anchor_tags_replaced_with_text(self) -> Self:
        """Replace <a> tags with their text contents only, removing the tags themselves."""
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            for a_tag in dom.find_all("a"):
                if isinstance(a_tag, Tag):
                    text = a_tag.get_text(strip=True)
                    if text:
                        a_tag.replace_with(NavigableString(text))
                    else:
                        a_tag.decompose()
            return dom
        return self.with_pod(pod, report_name="with_anchor_tags_replaced_with_text")
    
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
        return self.with_pod(pod, report_name="with_tags_before_h1_removed")

    def with_possible_buttons_removed(self) -> Self:
        """Heuristically remove elements likely to be buttons, but do not remove .not-a-button elements."""

        BUTTON_PREFIXES = (
            "copy", "copy to clipboard", "copy link", "share", "download",
            "read more", "learn more", "view more", "see more", "more", "open", "close",
            "submit", "cancel", "ok", "yes", "no", "apply", "reset", "save", "edit",
            "delete", "remove", "add", "create", "update", "change", "select", "choose",
            "like", "dislike", "upvote", "downvote", "vote", "rate", "review", "comment",
            "search", "filter", "sort", "next", "previous", "ask ai", "+1", "-1",
        )

        BUTTON_CLASSES = {
            "btn", "button", "btn-primary", "btn-secondary", "btn-success", "btn-danger", "btn-warning", "btn-info",
            "btn-light", "btn-dark", "btn-muted", "btn-xl", "btn-lg", "btn-md", "btn-sm", "btn-xs", "btn-tiny",
            "btn-block", "btn-group", "btn-toolbar"
        }
        selector = ",".join([f".{class_name}" for class_name in BUTTON_CLASSES])
        candidate_tags = {"button", "a", "span", "div", "input"}

        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            # Optimized: Remove tags by class using find_all and set intersection
            for tag in dom.find_all(candidate_tags):
                if not isinstance(tag, Tag):
                    continue
                tag_classes = tag.get("class")
                if tag_classes and set(tag_classes) & BUTTON_CLASSES:
                    tag.decompose()

            # Remove tags by text prefix match, but only for likely candidates
            to_remove = []
            for tag in dom.find_all(candidate_tags):
                if not isinstance(tag, Tag):
                    continue
                if not tag.contents:
                    continue
                if len(tag.contents) == 1 and isinstance(tag.contents[0], NavigableString):
                    text = str(tag.contents[0]).strip().lower()
                else:
                    text = tag.get_text(strip=True).lower()
                if text and len(text) <= 128 and text.startswith(BUTTON_PREFIXES):
                    to_remove.append(tag)
            if to_remove:
                for tag in to_remove:
                    tag.decompose()
            return dom

        return self.with_pod(pod, report_name="with_possible_buttons_removed")

    def with_readability_applied_trafilatura(self) -> Self:
        """Apply trafilatura to the HTML content and transform the dom into the Document's content."""
        from trafilatura import extract
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            current_html = str(dom)
            extracted = extract(current_html, include_comments=False, include_tables=True, include_images=False, )
            
            if extracted:
                return BeautifulSoup(extracted, "lxml")
            return dom
        
        return self.with_pod(pod, report_name="with_readability_applied_trafilatura")
    
    def with_readability_applied_newspaper(self) -> Self:
        """Apply newspaper3k to extract main article text from HTML content."""
        from newspaper import Article
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            current_html = str(dom)
            article = Article('')
            article.set_html(current_html)
            article.parse()
            text = article.text if article.text else current_html
            # Optionally wrap in <div> for HTML compatibility
            html = f"<div>{text}</div>"
            return BeautifulSoup(html, "lxml")
        return self.with_pod(pod, report_name="with_readability_applied_newspaper")
    
    
    def with_readability_applied_lxml(self) -> Self:
        from readability import Document
        """Apply readability-lxml to the HTML content and transform the dom into the Document's content."""
        
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            current_html = str(dom)
            doc = Document(current_html)
            html = doc.summary()
            return BeautifulSoup(html, "lxml")
            # We need to now decide which is the better candidate, original HTML, or what was used prior to this point.
            # for now, we'll err on the side of a ratio of 0.1, meaning if the readability content is less than 10%
            # the original HTML, we'll use the original HTML.
            original_length = len(current_html)
            readability_length = len(html)
            ratio = 0.2
            use_readability = readability_length >= (original_length * ratio)
            # use_readability = True
            
            if use_readability:
                return BeautifulSoup(html, "lxml")
            else:
                return dom
        
        return self.with_pod(pod, report_name="with_readability_applied")

    def with_readability_applied_justext(self) -> Self:
        """Apply jusText for boilerplate removal and main content extraction."""
        import justext
        def pod(dom: BeautifulSoup) -> BeautifulSoup:
            current_html = str(dom)
            paragraphs = justext.justext(current_html, justext.get_stoplist("English"))
            html = "\n\n</p><p>".join([p.text for p in paragraphs if not p.is_boilerplate])
            html = f"<p>{html}</p>"
            return BeautifulSoup(html, "lxml")
        return self.with_pod(pod, report_name="with_readability_applied_justext")

    def report(self) -> dict:
        """Return a dict of pod name to elapsed milliseconds for the last wash."""
        return {pod.name: pod.last_elapsed_ms for pod in self.pods}
