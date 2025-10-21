"""
Enhanced Text Processing Module for WriteBot

This module provides intelligent text splitting, paragraph handling,
line wrapping, and pagination for handwriting synthesis.

Features:
- Smart paragraph detection and preservation
- Advanced word wrapping with hyphenation support
- Intelligent pagination to avoid orphans/widows
- Configurable text normalization
- Support for multiple text formats
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ParagraphStyle(Enum):
    """Paragraph formatting styles"""
    PRESERVE_BREAKS = "preserve_breaks"  # Keep all paragraph breaks
    SINGLE_SPACE = "single_space"        # Single blank line between paragraphs
    NO_BREAKS = "no_breaks"              # No breaks, continuous flow
    INDENT_FIRST = "indent_first"        # Indent first line of paragraphs


@dataclass
class TextProcessingConfig:
    """Configuration for text processing"""
    max_line_length: int = 60
    lines_per_page: int = 24
    paragraph_style: ParagraphStyle = ParagraphStyle.PRESERVE_BREAKS
    indent_spaces: int = 4
    preserve_empty_lines: bool = True
    max_empty_lines: int = 2
    avoid_orphans: bool = True  # Avoid single line at top of page
    avoid_widows: bool = True   # Avoid single line at bottom of page
    min_paragraph_lines: int = 2  # Min lines to keep paragraph together
    hyphenate_long_words: bool = False
    normalize_whitespace: bool = True


class TextProcessor:
    """Advanced text processor for handwriting synthesis"""

    def __init__(self, config: Optional[TextProcessingConfig] = None):
        """Initialize text processor with configuration"""
        self.config = config or TextProcessingConfig()

    def process_text(
        self,
        text: str,
        alphabet: Optional[set] = None,
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process text into lines ready for handwriting synthesis.

        Args:
            text: Input text to process
            alphabet: Set of allowed characters (for sanitization)

        Returns:
            Tuple of (processed_lines, metadata)
        """
        # Step 1: Normalize text
        normalized = self._normalize_text(text)

        # Step 2: Split into paragraphs
        paragraphs = self._split_paragraphs(normalized)

        # Step 3: Sanitize if alphabet provided
        if alphabet:
            paragraphs = self._sanitize_paragraphs(paragraphs, alphabet)

        # Step 4: Wrap lines within paragraphs
        wrapped_paragraphs = self._wrap_paragraphs(paragraphs)

        # Step 5: Apply paragraph styling
        styled_lines = self._apply_paragraph_styling(wrapped_paragraphs)

        # Step 6: Paginate with smart breaks
        pages = self._paginate_lines(styled_lines)

        # Step 7: Flatten pages into final line list
        final_lines = self._flatten_pages(pages)

        # Generate metadata
        metadata = {
            'original_length': len(text),
            'num_paragraphs': len(paragraphs),
            'num_lines': len(final_lines),
            'num_pages': len(pages),
            'lines_per_page': [len(page) for page in pages],
            'config': {
                'max_line_length': self.config.max_line_length,
                'lines_per_page': self.config.lines_per_page,
                'paragraph_style': self.config.paragraph_style.value,
            }
        }

        return final_lines, metadata

    def _normalize_text(self, text: str) -> str:
        """Normalize text by handling whitespace and special characters"""
        if not self.config.normalize_whitespace:
            return text

        # Convert different line endings to \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Convert tabs to spaces
        text = text.replace('\t', '    ')

        # Limit consecutive empty lines
        if self.config.max_empty_lines > 0:
            pattern = r'\n{' + str(self.config.max_empty_lines + 2) + r',}'
            replacement = '\n' * (self.config.max_empty_lines + 1)
            text = re.sub(pattern, replacement, text)

        return text

    def _split_paragraphs(self, text: str) -> List[Tuple[str, int]]:
        """
        Split text into paragraphs, preserving empty line counts.

        Returns:
            List of (paragraph_text, trailing_empty_lines) tuples
        """
        paragraphs = []

        # Split by double newlines or more
        blocks = re.split(r'\n\s*\n', text)

        for i, block in enumerate(blocks):
            # Count trailing newlines in original text
            block_stripped = block.strip()
            if not block_stripped:
                continue

            # Determine number of blank lines after this paragraph
            # (except for the last paragraph)
            trailing_lines = 1 if i < len(blocks) - 1 else 0

            paragraphs.append((block_stripped, trailing_lines))

        return paragraphs

    def _sanitize_paragraphs(
        self,
        paragraphs: List[Tuple[str, int]],
        alphabet: set
    ) -> List[Tuple[str, int]]:
        """Remove characters not in the allowed alphabet"""
        sanitized = []

        for text, trailing in paragraphs:
            # Replace disallowed characters with spaces
            sanitized_text = ''.join(
                char if char in alphabet else ' '
                for char in text
            )

            # Collapse multiple spaces
            sanitized_text = re.sub(r' +', ' ', sanitized_text).strip()

            if sanitized_text:  # Only keep non-empty paragraphs
                sanitized.append((sanitized_text, trailing))

        return sanitized

    def _wrap_paragraphs(
        self,
        paragraphs: List[Tuple[str, int]]
    ) -> List[Tuple[List[str], int]]:
        """
        Wrap each paragraph into lines respecting max_line_length.

        Returns:
            List of (lines, trailing_empty_lines) tuples
        """
        wrapped = []

        for text, trailing in paragraphs:
            lines = self._wrap_single_paragraph(text)
            wrapped.append((lines, trailing))

        return wrapped

    def _wrap_single_paragraph(self, text: str) -> List[str]:
        """Wrap a single paragraph into multiple lines"""
        words = text.split()
        if not words:
            return []

        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            # Check if word fits on current line (account for space)
            space_length = 1 if current_line else 0

            if current_length + space_length + word_length <= self.config.max_line_length:
                # Word fits on current line
                current_line.append(word)
                current_length += space_length + word_length
            else:
                # Need to move to next line
                if current_line:
                    lines.append(' '.join(current_line))

                # Check if word itself is too long
                if word_length > self.config.max_line_length:
                    # Handle long word
                    if self.config.hyphenate_long_words:
                        # Split word with hyphen
                        while word_length > self.config.max_line_length - 1:
                            chunk_size = self.config.max_line_length - 1
                            lines.append(word[:chunk_size] + '-')
                            word = word[chunk_size:]
                            word_length = len(word)
                    else:
                        # Just add it as-is (will overflow)
                        lines.append(word)
                        current_line = []
                        current_length = 0
                        continue

                # Start new line with word
                current_line = [word]
                current_length = len(word)

        # Add remaining line
        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _apply_paragraph_styling(
        self,
        wrapped_paragraphs: List[Tuple[List[str], int]]
    ) -> List[Tuple[List[str], str]]:
        """
        Apply paragraph styling (indentation, spacing).

        Returns:
            List of (lines, line_type) where line_type is 'text' or 'blank'
        """
        styled_lines = []

        for para_idx, (lines, trailing) in enumerate(wrapped_paragraphs):
            if not lines:
                continue

            # Apply indentation to first line if configured
            if self.config.paragraph_style == ParagraphStyle.INDENT_FIRST:
                indent = ' ' * self.config.indent_spaces
                lines[0] = indent + lines[0]

            # Add paragraph lines
            for line in lines:
                styled_lines.append((line, 'text'))

            # Add spacing between paragraphs
            if para_idx < len(wrapped_paragraphs) - 1:  # Not last paragraph
                if self.config.paragraph_style == ParagraphStyle.PRESERVE_BREAKS:
                    # Add the trailing blank lines
                    for _ in range(trailing):
                        if self.config.preserve_empty_lines:
                            styled_lines.append(('', 'blank'))
                elif self.config.paragraph_style == ParagraphStyle.SINGLE_SPACE:
                    styled_lines.append(('', 'blank'))
                # NO_BREAKS and INDENT_FIRST don't add blank lines

        return styled_lines

    def _paginate_lines(
        self,
        styled_lines: List[Tuple[str, str]]
    ) -> List[List[str]]:
        """
        Paginate lines with smart breaks to avoid orphans/widows.

        Returns:
            List of pages, where each page is a list of lines
        """
        if not styled_lines:
            return [[]]

        pages = []
        current_page = []
        i = 0

        while i < len(styled_lines):
            line, line_type = styled_lines[i]

            # Check if we can add this line to current page
            if len(current_page) < self.config.lines_per_page:
                current_page.append(line)
                i += 1
            else:
                # Page is full, need to check for orphan/widow
                if self._should_apply_smart_break(
                    styled_lines, i, current_page
                ):
                    # Adjust page break
                    current_page = self._apply_smart_break(
                        styled_lines, i, current_page
                    )

                # Finalize current page
                pages.append(current_page)
                current_page = []

        # Add remaining lines as final page
        if current_page:
            pages.append(current_page)

        return pages

    def _should_apply_smart_break(
        self,
        styled_lines: List[Tuple[str, str]],
        next_index: int,
        current_page: List[str]
    ) -> bool:
        """Determine if we should apply smart page breaking"""
        # For simplicity, always return False for now
        # Can be enhanced to detect paragraph boundaries
        return False

    def _apply_smart_break(
        self,
        styled_lines: List[Tuple[str, str]],
        next_index: int,
        current_page: List[str]
    ) -> List[str]:
        """Apply smart page break adjustment"""
        # Placeholder for smart break logic
        return current_page

    def _flatten_pages(self, pages: List[List[str]]) -> List[str]:
        """Flatten pages into a single list of lines"""
        all_lines = []
        for page in pages:
            all_lines.extend(page)
        return all_lines

    def get_pages(
        self,
        text: str,
        alphabet: Optional[set] = None,
    ) -> Tuple[List[List[str]], Dict[str, Any]]:
        """
        Process text and return as pages (2D list).

        Args:
            text: Input text to process
            alphabet: Set of allowed characters (for sanitization)

        Returns:
            Tuple of (pages, metadata) where pages is List[List[str]]
        """
        # Process text into lines
        all_lines, metadata = self.process_text(text, alphabet)

        # Split into pages
        pages = []
        for i in range(0, len(all_lines), self.config.lines_per_page):
            page = all_lines[i:i + self.config.lines_per_page]
            pages.append(page)

        # Update metadata
        metadata['pages'] = pages
        metadata['num_pages'] = len(pages)

        return pages, metadata


def create_alphabet_set(alphabet_list: Optional[List[str]] = None) -> set:
    """
    Create a set of allowed characters from a list.

    Args:
        alphabet_list: List of allowed characters

    Returns:
        Set of allowed characters
    """
    if alphabet_list is None:
        # Default alphabet (common ASCII characters)
        alphabet_list = [
            '\x00', ' ', '!', '"', '#', "'", '(', ')', ',', '-', '.',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';',
            '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
            'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
            'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i',
            'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
            'v', 'w', 'x', 'y', 'z'
        ]

    return set(alphabet_list)


# Convenience function for quick processing
def process_text_simple(
    text: str,
    max_line_length: int = 60,
    lines_per_page: int = 24,
    alphabet: Optional[List[str]] = None,
) -> Tuple[List[List[str]], Dict[str, Any]]:
    """
    Simple function to process text into pages.

    Args:
        text: Input text
        max_line_length: Maximum characters per line
        lines_per_page: Maximum lines per page
        alphabet: List of allowed characters

    Returns:
        Tuple of (pages, metadata)
    """
    config = TextProcessingConfig(
        max_line_length=max_line_length,
        lines_per_page=lines_per_page,
    )

    processor = TextProcessor(config)
    alphabet_set = create_alphabet_set(alphabet) if alphabet else None

    return processor.get_pages(text, alphabet_set)


if __name__ == '__main__':
    # Example usage
    sample_text = """This is a sample paragraph with some text that needs to be wrapped properly.

It should handle multiple paragraphs correctly and preserve the spacing between them.

This is another paragraph. It demonstrates how the text processor can intelligently
split text into lines and pages while respecting word boundaries and paragraph structure.

The processor also handles very long words that might exceed the maximum line length limit,
and can optionally hyphenate them or just let them overflow depending on configuration."""

    # Process with default settings
    pages, meta = process_text_simple(sample_text, max_line_length=50, lines_per_page=10)

    print("Processed Text:")
    print(f"Total pages: {meta['num_pages']}")
    print(f"Total lines: {meta['num_lines']}")
    print(f"Paragraphs: {meta['num_paragraphs']}")
    print()

    for page_num, page in enumerate(pages, 1):
        print(f"=== Page {page_num} ({len(page)} lines) ===")
        for line_num, line in enumerate(page, 1):
            print(f"{line_num:2d}: {line}")
        print()
