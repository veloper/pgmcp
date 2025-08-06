import pytest

from bs4 import BeautifulSoup, Tag

from pgmcp.chunking.html_washing_machine import HTMLWashingMachine


@pytest.fixture
def html():
    return '''
    <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>HTMLWashingMachine Comprehensive Test Document</title>
            <style>
                .btn, .button, .btn-primary, .btn-secondary, .btn-success, .btn-danger, .btn-warning, .btn-info, .btn-light, .btn-dark, .btn-muted,
                .btn-xl, .btn-lg, .btn-md, .btn-sm, .btn-xs, .btn-tiny, .btn-block, .btn-group, .btn-toolbar {
                border: 1px solid #333;
                padding: 4px 8px;
                margin: 2px;
                display: inline-block;
                }
                .not-a-button { color: green; }
            </style>
            <script>
                // This script should be removed
                var foo = "bar";
            </script>
            </head>
        <body>
        <!-- Navigation Section -->
        <li>
            <ul>
                <li><a href="/home">Home</a></li>
                <li><a href="/about">About</a></li>
                <li><a href="/contact">Contact</a></li>
                <li><a href="../services">Services</a></li>
                <li><a href="https://example.com">External Link</a></li>
                <li>
                    <p>Nested List</p>
                    <ul>
                        <li><a href="../site-map">Site Map</a></li>
                        <li><a href="https://example.com/terms">Terms of Service</a></li>
                    </ul>
                </li>
            </ul>
        </li>
        <!-- Headings and heading replacement -->
        <h1>Main Heading</h1>
        <p>This is a paragraph after h1.</p>
        <h2>Subheading</h2>
        <span>Span after h2</span>
        <h3>Another Heading</h3>
        <div>Div after h3</div>
        <h4>Short</h4>
        <li>List item after h4</li>
        <h5>With<br>Newline</h5>
        <a href="#">Anchor after h5</a>
        <h6>Long Heading</h6>
        <strong>This is a strong tag after h6</strong>

        <!-- Code tags, pre/code combos -->
        <pre><code>def foo():\n    return "bar"</code></pre>
        <code>inline_code</code>
        <div><code>not in pre</code></div>
        <pre><span><code>nested code in pre</code></span></pre>

        <!-- Dashes of all types -->
        <p>Hyphen-minus: -</p>
        <p>Hyphen: ‐</p>
        <p>Non-breaking hyphen: ‑</p>
        <p>Figure dash: ‒</p>
        <p>En dash: –</p>
        <p>Em dash: —</p>
        <p>Horizontal bar: ―</p>
        <p>Bullet: ⁃</p>
        <p>Minus sign: −</p>
        <p>Small em dash: ﹘</p>
        <p>Fullwidth hyphen-minus: －</p>
        <p>Superscript minus: ⁻</p>
        <p>Subscript minus: ₋</p>
        <p>Small hyphen-minus: ﹣</p>

        <!-- Empty tags -->
        <br>
        <hr>
        <p></p>
        <div></div>
        <span></span>
        <p> </p>
        <div> </div>
        <span> </span>

        <!-- Tags to be converted to headings -->
        <div class="convert-to-h2">Should become h2</div>
        <span class="convert-to-h3">Should become h3</span>

        <!-- Tags to be removed by selector -->
        <div class="remove-me">Remove me</div>
        <span class="remove-me">Remove me too</span>

        <!-- Button-like elements (by class, text, suffix, substring) -->
        <div class="_wrapper_buttons">
            <button class="btn">Edit</button>
            <a class="btn-primary" href="#">Save</a>
            <span class="btn-secondary">Delete</span>
            <div class="btn-success">Copy</div>
            <button class="btn-danger">Remove</button>
            <div class="btn-warning">Download</div>
            <span class="btn-info">Share</span>
            <a class="btn-light">Read more...</a>
            <span class="btn-dark">Learn more!</span>
            <div class="btn-muted">View more?</div>
            <span class="btn-xl">See more…</span>
            <div class="btn-lg">More ...</div>
            <span class="btn-md">Open.</span>
            <div class="btn-sm">Close!</div>
            <span class="btn-xs">Submit?</span>
            <div class="btn-tiny">Cancel…</div>
            <span class="btn-block">OK</span>
            <div class="btn-group">Yes</div>
            <span class="btn-toolbar">No</span>
            <a>Apply</a>
            <button>Reset</button>
            <button>Save</button>
            <div>Edit</div>
            <button>Delete</button>
            <button>Remove</button>
            <button>Add</button>
            <button>Create</button>
            <button>Update</button>
            <button>Change</button>
            <button>Select</button>
            <button>Choose</button>
            <button>Like</button>
            <button>Dislike</button>
            <button>Upvote</button>
            <button>Downvote</button>
            <button>Vote</button>
            <button>Rate</button>
            <button>Review</button>
            <button>Comment</button>
            <button>+1</button>
            <button>-1</button>
            <button>Copy to clipboard</button>
            <button>Copy link</button>
            <button>copy…</button>
            <button>copy to clipboard!</button>
            <button>copy link?</button>
        </div>
        
        <!-- Button-like text but not a button -->
        <div class="not-a-button">This is not a button, just text: Save the whales!</div>
        <span class="not-a-button">Don't remove this: "Edit your profile to add info."</span>

        <!-- Custom filter pod test -->
        <div class="custom-filter" data-remove="true">Should be removed by custom filter</div>
        <div class="custom-filter" data-remove="false">Should NOT be removed by custom filter</div>

        <!-- Scripts and styles -->
        <script>
            // Another script to remove
            alert('Remove me!');
        </script>
        <style>
            /* Style to remove */
            .remove-me { color: red; }
        </style>
    '''


@pytest.fixture(autouse=True)
def machine(html: str) -> HTMLWashingMachine:
    """Fixture to create an HTMLWashingMachine instance."""
    return HTMLWashingMachine.create(html)

"""
Tests are setup around `with_...` methods per class since many have quite a few combinations to test.
Each test checks that the expected transformations worked as expected, AND that no other side effects occurred.
  - A combination of assertive and negative tests used to do this.
"""


class TestWithPossibleButtonsRemoved:
    
    def test_that_buttons_of_all_types_are_removed(self, machine: HTMLWashingMachine):
        """Test that buttons with known shortcut characters are removed."""
        
        dom = machine.dom
        
        _wrapper_buttons_div = dom.find('div', class_='_wrapper_buttons')
        assert isinstance(_wrapper_buttons_div, Tag), "Expected div._wrapper_buttons to be a Tag"
        
        assert len(_wrapper_buttons_div.find_all(True)) > 0, "Expected _wrapper_buttons to contain elements"
        
        washed = machine.with_possible_buttons_removed().wash()
        
        assert len(_wrapper_buttons_div.find_all(True)) <= 0, "Expected _wrapper_buttons to be empty after washing"
        
        



class TestWithScriptsRemoved:
    def test_with_scripts_removed(self, machine: HTMLWashingMachine):
        """Test that scripts are removed."""
        # Before: script tags should exist
        before = [tag for tag in machine.dom.find_all('script')]
        assert len(before) > 0
        # After: script tags should be gone in washed output
        from bs4 import BeautifulSoup
        washed = machine.with_script_tags_removed().wash()
        after = BeautifulSoup(washed, 'html.parser').find_all('script')
        assert len(after) == 0


class TestWithCustomFilterPod:
    def test_with_custom_filter_pod_selector_only(self, machine: HTMLWashingMachine):
        """
        Given: An HTML document with elements matching a selector
        When: with_custom_filter_pod is called with only the selector
        Then: No elements are removed unless the default filter returns True
        """
        # Before: custom-filter elements should exist
        before = [tag for tag in machine.dom.select('.custom-filter')]
        assert len(before) == 2
        # Use a filter that always returns False (should remove nothing)
        washed = machine.with_custom_filter_pod('.custom-filter', lambda tag: False).wash()
        # After: both custom-filter elements should still exist
        from bs4 import BeautifulSoup
        after = BeautifulSoup(washed, 'html.parser').select('.custom-filter')
        assert len(after) == 2
        # Use a filter that removes only those with data-remove="true"
        washed2 = machine.with_custom_filter_pod('.custom-filter', lambda tag: tag.get('data-remove') == 'true').wash()
        after2 = BeautifulSoup(washed2, 'html.parser').select('.custom-filter')
        assert len(after2) == 1
        assert after2[0].get('data-remove') == 'false'

    def test_with_custom_filter_pod_selector_and_filter_func(self, machine: HTMLWashingMachine):
        """
        Given: An HTML document with elements matching a selector
        When: with_custom_filter_pod is called with a selector and a custom filter function
        Then: Only elements for which the filter returns True are removed
        """
        from bs4 import BeautifulSoup

        # Before: both custom-filter elements should exist
        before = [tag for tag in machine.dom.select('.custom-filter')]
        assert len(before) == 2
        # Custom filter: remove elements whose text contains 'NOT'
        washed = machine.with_custom_filter_pod('.custom-filter', lambda tag: 'NOT' in tag.text).wash()
        after = BeautifulSoup(washed, 'html.parser').select('.custom-filter')
        assert len(after) == 1
        assert 'NOT' not in after[0].text

class TestWithExistingHeadingTextReplaced:
    def test_default_options(self, machine: HTMLWashingMachine):
        """
        Given: Headings followed by various tags
        When: with_existing_heading_text_replaced is called with default options
        Then: Each heading's text is replaced with the closest qualified sibling's text
        """
        from bs4 import BeautifulSoup

        # Before: get original heading texts
        headings = [h for h in machine.dom.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        before_texts = [h.get_text(strip=True) for h in headings]
        assert before_texts == [
            'Main Heading', 'Subheading', 'Another Heading', 'Short', 'WithNewline', 'Long Heading'
        ]
        # After: apply transformation and check new heading texts
        washed = machine.with_existing_heading_text_replaced().wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after_headings = [h for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        after_texts = [h.get_text(strip=True) for h in after_headings]
        # According to the HTML, the closest qualified siblings are:
        # h1 -> 'This is a paragraph after h1.'
        # h2 -> 'Span after h2'
        # h3 -> 'Div after h3'
        # h4 -> 'List item after h4'
        # h5 -> 'Anchor after h5'
        # h6 -> 'This is a strong tag after h6'
        assert after_texts == [
            'This is a paragraph after h1.',
            'Span after h2',
            'Div after h3',
            'List item after h4',
            'Anchor after h5',
            'This is a strong tag after h6'
        ]

    def test_custom_allowed_tags(self, machine: HTMLWashingMachine):
        """
        Given: Headings followed by various tags
        When: with_existing_heading_text_replaced is called with a custom allowed_tags list
        Then: Only siblings with tag names in allowed_tags are considered for replacement
        """
        from bs4 import BeautifulSoup

        # Only allow 'div' as a replacement
        washed = machine.with_existing_heading_text_replaced(allowed_tags=['div']).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after_headings = [h for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        after_texts = [h.get_text(strip=True) for h in after_headings]
        # With the logic: look at the next max_distance siblings (default 4), regardless of qualification, and use the first qualified one (div) if found
        # h1: next 4 siblings: p, h2, span, h3 (none are div) -> unchanged
        # h2: next 4 siblings: span, h3, div, h4 (div is within window) -> replaced with 'Div after h3'
        # h3: next 4 siblings: div, h4, li, h5 (div is immediate) -> replaced with 'Div after h3'
        # h4: next 4 siblings: li, h5, a, h6 (none are div) -> unchanged
        # h5: next 4 siblings: a, h6, strong, pre (none are div) -> unchanged
        # h6: next 4 siblings: strong, pre, code, div (div is 4th) -> replaced with 'not in pre'
        assert after_texts == [
            'Main Heading',
            'Div after h3',
            'Div after h3',
            'Short',
            'WithNewline',
            'not in pre'
        ]

    def test_custom_max_distance(self, machine: HTMLWashingMachine):
        """
        Given: Headings with siblings at varying distances
        When: with_existing_heading_text_replaced is called with a custom max_distance
        Then: Only siblings within max_distance are considered for replacement
        """
        from bs4 import BeautifulSoup

        # Set max_distance to 1, so only immediate sibling is considered
        washed = machine.with_existing_heading_text_replaced(max_distance=1).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after_headings = [h for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        after_texts = [h.get_text(strip=True) for h in after_headings]
        # With the logic: only the immediate next sibling is considered for each heading
        assert after_texts == [
            'This is a paragraph after h1.',
            'Span after h2',
            'Div after h3',
            'List item after h4',
            'Anchor after h5',
            'This is a strong tag after h6'
        ]

    def test_custom_max_length(self, machine: HTMLWashingMachine):
        """
        Given: Headings followed by siblings with varying text lengths
        When: with_existing_heading_text_replaced is called with a custom max_length
        Then: Only siblings with text length <= max_length are considered for replacement
        """
        from bs4 import BeautifulSoup

        # Set max_length to 5, so only very short siblings are considered
        washed = machine.with_existing_heading_text_replaced(max_length=5).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after_headings = [h for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        after_texts = [h.get_text(strip=True) for h in after_headings]
        # None of the default siblings are <= 5 chars, so all headings remain unchanged
        assert after_texts == [
            'Main Heading',
            'Subheading',
            'Another Heading',
            'Short',
            'WithNewline',
            'Long Heading'
        ]

    def test_allow_newlines_true(self, machine: HTMLWashingMachine):
        """
        Given: Headings followed by siblings containing newlines
        When: with_existing_heading_text_replaced is called with allow_newlines=True
        Then: Siblings with newlines in their text are considered for replacement
        """
        from bs4 import BeautifulSoup

        # The sibling after h5 contains a <br> (newline), so it should be considered
        washed = machine.with_existing_heading_text_replaced(allow_newlines=True).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after_headings = [h for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        after_texts = [h.get_text(strip=True) for h in after_headings]
        # h5 should now be replaced with 'Anchor after h5' (since <a> is next, not the <br>)
        assert after_texts[4] == 'Anchor after h5'

class TestWithNonPreCodeTagsReplacedWithBackticks:
    def test_default(self, machine: HTMLWashingMachine):
        """
        Given: Inline <code> tags not inside <pre>
        When: with_non_pre_code_tags_replaced_with_backticks is called
        Then: Those code tags are replaced with backtick-wrapped text
        """
        from bs4 import BeautifulSoup, Tag
        washed = machine.with_non_pre_code_tags_replaced_with_backticks().wash()
        soup = BeautifulSoup(washed, 'html.parser')
        # Inline code not in pre should be replaced
        inline_code = soup.find('code', string='inline_code')
        assert inline_code is None
        # The text should now be wrapped in backticks
        assert '`inline_code`' in soup.get_text()
        # <code> inside <pre> should remain as <code>
        pre = soup.find('pre')
        assert pre is not None and isinstance(pre, Tag)
        pre_codes = pre.find_all('code') if isinstance(pre, Tag) else []
        assert any(isinstance(c, Tag) and c.get_text() == 'def foo():\n    return "bar"' for c in pre_codes)
        # <code> inside <div> but not in <pre> should be replaced
        divs = soup.find_all('div')
        found = False
        for div in divs:
            if isinstance(div, Tag) and div.get_text() and 'not in pre' in div.get_text():
                assert '`not in pre`' in div.get_text()
                found = True
        assert found
        # <code> inside <span> inside <pre> should remain as <code>
        nested_code_found = False
        for pre in soup.find_all('pre'):
            if not isinstance(pre, Tag):
                continue
            for span in pre.find_all('span') if isinstance(pre, Tag) else []:
                if not isinstance(span, Tag):
                    continue
                for code in span.find_all('code') if isinstance(span, Tag) else []:
                    if isinstance(code, Tag) and code.get_text() == 'nested code in pre':
                        nested_code_found = True
        assert nested_code_found

class TestWithDashesEncoded:
    def test_default(self, machine: HTMLWashingMachine):
        """
        Given: Text containing various dash and hyphen characters
        When: with_dashes_encoded is called
        Then: All dash and hyphen characters are replaced with their HTML entity codes
        """
        from bs4 import BeautifulSoup
        washed = machine.with_dashes_encoded().wash()
        soup = BeautifulSoup(washed, 'html.parser')
        # Map of original dash/hyphen to expected HTML entity
        dash_map = {
            '-': '&#45;',
            '‐': '&#8208;',
            '‑': '&#8209;',
            '‒': '&#8210;',
            '–': '&#8211;',
            '—': '&#8212;',
            '―': '&#8213;',
            '⁃': '&#8259;',
            '−': '&#8722;',
            '﹘': '&#65118;',
            '－': '&#65293;',
            '⁻': '&#8315;',
            '₋': '&#8331;',
            '﹣': '&#65121;',
        }
        text = soup.get_text()
        for orig, entity in dash_map.items():
            assert entity in text, f"Expected {entity} in output for {orig}"
            assert orig not in text, f"Did not expect {orig} in output"

class TestWithEmptyTagsRemoved:
    def test_default_tags(self, machine: HTMLWashingMachine):
        """
        Given: Empty tags of default types (br, hr, p, div, span)
        When: with_empty_tags_removed is called with no arguments
        Then: All empty tags of those types are removed
        """
        from bs4 import BeautifulSoup
        washed = machine.with_empty_tags_removed().wash()
        soup = BeautifulSoup(washed, 'html.parser')
        # All empty <br>, <hr>, <p>, <div>, <span> should be removed
        assert not soup.find('br')
        assert not soup.find('hr')
        # Only non-empty <p>, <div>, <span> should remain
        for tag in ['p', 'div', 'span']:
            for el in soup.find_all(tag):
                assert el.get_text(strip=True), f"Found empty <{tag}> that should have been removed"

    def test_custom_tags(self, machine: HTMLWashingMachine):
        """
        Given: Empty tags of custom types
        When: with_empty_tags_removed is called with a custom tags list
        Then: Only empty tags of those types are removed
        """
        from bs4 import BeautifulSoup

        # Add a custom empty <section> and <article> to the fixture for this test
        html = machine.html + '<section></section><article></article>'
        custom_machine = HTMLWashingMachine.create(html)
        washed = custom_machine.with_empty_tags_removed(tags=['section', 'article']).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        # Both should be removed
        assert not soup.find('section')
        assert not soup.find('article')
        # But default empty tags should remain since not in custom list
        assert soup.find('br')
        assert soup.find('hr')

class TestWithTagsConvertedToHeading:
    def test_selector_and_level(self, machine: HTMLWashingMachine):
        """
        Given: Tags matching a selector
        When: with_tags_converted_to_heading is called with a selector and level
        Then: Those tags are converted to heading tags of the specified level
        """
        from bs4 import BeautifulSoup, Tag
        washed = machine.with_tags_converted_to_heading('.convert-to-h2', 2).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        h2s = soup.find_all('h2')
        # Should find the converted div as h2
        assert any('Should become h2' in h2.get_text() for h2 in h2s)
        # Should not find any div with class convert-to-h2
        assert not soup.find('div', class_='convert-to-h2')

    def test_keep_attrs_true(self, machine: HTMLWashingMachine):
        """
        Given: Tags with attributes matching a selector
        When: with_tags_converted_to_heading is called with keep_attrs=True
        Then: Converted heading tags retain their original attributes
        """
        from bs4 import BeautifulSoup, Tag
        washed = machine.with_tags_converted_to_heading('.convert-to-h3', 3, keep_attrs=True).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        h3s = soup.find_all('h3')
        found = False
        for h3 in h3s:
            if not isinstance(h3, Tag):
                continue
            if 'Should become h3' in h3.get_text():
                cls = h3.get('class')
                if cls:
                    if isinstance(cls, str):
                        found = 'convert-to-h3' == cls
                    elif isinstance(cls, list):
                        found = 'convert-to-h3' in cls
            if found:
                break
        assert found

    def test_level_callable(self, machine: HTMLWashingMachine):
        """
        Given: Tags matching a selector
        When: with_tags_converted_to_heading is called with level as a callable
        Then: The callable determines the heading level for each tag
        """
        from bs4 import BeautifulSoup, Tag
        def level_fn(tag):
            return 2 if tag.name == 'div' else 3
        washed = machine.with_tags_converted_to_heading('.convert-to-h2, .convert-to-h3', level_fn, keep_attrs=True).wash()
        soup = BeautifulSoup(washed, 'html.parser')
        h2s = soup.find_all('h2')
        h3s = soup.find_all('h3')
        assert any(isinstance(h2, Tag) and 'Should become h2' in h2.get_text() for h2 in h2s)
        assert any(isinstance(h3, Tag) and 'Should become h3' in h3.get_text() for h3 in h3s)

class TestWithTagsRemoved:
    def test_selector(self, machine: HTMLWashingMachine):
        """
        Given: Tags matching a selector
        When: with_tags_removed is called with the selector
        Then: All matching tags are removed from the document
        """
        from bs4 import BeautifulSoup

        # Before: .remove-me elements should exist
        before_divs = [tag for tag in machine.dom.select('div.remove-me')]
        before_spans = [tag for tag in machine.dom.select('span.remove-me')]
        assert len(before_divs) > 0
        assert len(before_spans) > 0
        # After: all .remove-me elements should be gone
        washed = machine.with_tags_removed('.remove-me').wash()
        soup = BeautifulSoup(washed, 'html.parser')
        assert not soup.select('div.remove-me')
        assert not soup.select('span.remove-me')

class TestWithStylesRemoved:
    def test_default(self, machine: HTMLWashingMachine):
        """
        Given: <style> tags in the document
        When: with_styles_removed is called
        Then: All <style> tags are removed
        """
        from bs4 import BeautifulSoup

        # Before: style tags should exist
        before = [tag for tag in machine.dom.find_all('style')]
        assert len(before) > 0
        # After: style tags should be gone
        washed = machine.with_style_tags_removed().wash()
        soup = BeautifulSoup(washed, 'html.parser')
        after = soup.find_all('style')
        assert len(after) == 0
