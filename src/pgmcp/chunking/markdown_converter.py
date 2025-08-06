import re

from typing import ClassVar

from markdownify import MarkdownConverter as OriginalMarkdownConverter


def convert_html_to_markdown(html: str) -> str:
    """
    Converts HTML content to Markdown using a custom Markdown converter.
    
    This function uses the `CustomMarkdownConverter` to convert the washed HTML to Markdown.
    It applies various washing steps to clean the HTML before conversion.
    
    Args:
        html (str): The HTML content to convert.

    Returns:
        str: The converted Markdown content.
    """ 
    converter = MarkdownConverter()
    return converter.convert(html)

class MarkdownConverter(OriginalMarkdownConverter):
    """
    Idiomatic extension of `markdownify.MarkdownConverter` for improved Markdown output,
    especially for HTML definition lists.

    - Renders <dl>/<dt>/<dd> as nested bullet lists for readability and Markdown compatibility.
    - <dt>: top-level bullet; <dd>: indented bullet under its <dt>.
    - Consecutive <dt> become adjacent list items.
    - Normalizes whitespace/newlines.
    - Strips images.
    - Uses ATX headings and '-' for bullets.

    Example:
        Input:
            The Type Right Here
            :   The definition content right here.
        Output:
            - The Type Right Here
              - The definition content right here.

    Use as a drop-in replacement for idiomatic Markdown from HTML, especially for definition lists.
    """
    
    re_line_with_content : ClassVar[re.Pattern] = re.compile(r'^(.*)', flags=re.MULTILINE)
    re_all_whitespace : ClassVar[re.Pattern] = re.compile(r'[\t \r\n]+')

    def __init__(self, *args, **kwargs):
        kwargs["heading_style"] = "ATX"
        kwargs["bullets"] = "-"
        kwargs["strip"] = ["img"]
        kwargs["escape_underscores"] = False
        super().__init__(*args, **kwargs)

    def convert_dt(self, el, text, parent_tags):
        # remove newlines from term text
        text = (text or '').strip()
        text = self.__class__.re_all_whitespace.sub(' ', text)
        if '_inline' in parent_tags:
            return ' ' + text + ' '
        if not text:
            return '\n'

        # TODO - format consecutive <dt> elements as directly adjacent lines):
        #   https://michelf.ca/projects/php-markdown/extra/#def-list

        return '\n\n- %s\n' % text


    def convert_dd(self, el, text, parent_tags):
        text = (text or '').strip()
        if '_inline' in parent_tags:
            return ' ' + text + ' '
        if not text:
            return '\n'

        # indent definition content lines by four spaces
        def _indent_for_dd(match):
            line_content = match.group(1)
            return '    ' + line_content if line_content else ''
        text = self.__class__.re_line_with_content.sub(_indent_for_dd, text)

        # insert definition marker into first-line indent whitespace
        text = '  -' + text[3:]

        return '%s\n' % text
