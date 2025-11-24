"""
Text processing module for handling paragraphs, word wrapping, and pagination.

This module provides the `TextProcessor` class and related configuration and
utility functions. It handles the complexities of formatting text for
handwriting synthesis, including breaking text into pages, preserving
paragraph structure, and wrapping text within line limits.
"""

from enum import Enum
from typing import List, Dict, Any, Tuple, Optional, Set
import re


class ParagraphStyle(Enum):
    """Enumeration of paragraph handling styles."""
    PRESERVE_BREAKS = "preserve_breaks"
    SINGLE_SPACE = "single_space"
    NO_BREAKS = "no_breaks"
    INDENT_FIRST = "indent_first"


class TextProcessingConfig:
    """Configuration for the text processor."""

    def __init__(
        self,
        max_line_length: int = 75,
        lines_per_page: int = 24,
        paragraph_style: ParagraphStyle = ParagraphStyle.PRESERVE_BREAKS,
        preserve_empty_lines: bool = True,
        hyphenate_long_words: bool = False,
        normalize_whitespace: bool = True,
    ):
        """
        Initialize the text processing configuration.

        Args:
            max_line_length: Maximum characters per line.
            lines_per_page: Maximum lines per page.
            paragraph_style: Style for handling paragraphs.
            preserve_empty_lines: Whether to keep empty lines from input.
            hyphenate_long_words: Whether to split long words (basic implementation).
            normalize_whitespace: Whether to collapse multiple spaces.
        """
        self.max_line_length = max_line_length
        self.lines_per_page = lines_per_page
        self.paragraph_style = paragraph_style
        self.preserve_empty_lines = preserve_empty_lines
        self.hyphenate_long_words = hyphenate_long_words
        self.normalize_whitespace = normalize_whitespace


def create_alphabet_set(alphabet_list: Optional[List[str]]) -> Optional[Set[str]]:
    """
    Create a set of allowed characters from a list.

    Args:
        alphabet_list: List of allowed characters.

    Returns:
        Set of allowed characters, or None if list is None.
    """
    if alphabet_list is None:
        return None
    return set(alphabet_list)


class TextProcessor:
    """
    Handles text cleaning, wrapping, pagination, and formatting.
    """

    def __init__(self, config: TextProcessingConfig):
        """
        Initialize the TextProcessor.

        Args:
            config: TextProcessingConfig object.
        """
        self.config = config

    def process_text(
        self,
        text: str,
        alphabet: Optional[Set[str]] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process raw text into a list of formatted lines.

        Args:
            text: Input text string.
            alphabet: Optional set of allowed characters for validation/filtering.

        Returns:
            Tuple containing:
            - List of formatted string lines.
            - Metadata dictionary with processing stats.
        """
        if not text:
            return [], {"num_lines": 0, "num_paragraphs": 0}

        # Step 1: Normalize text and split into paragraphs
        paragraphs = self._split_into_paragraphs(text)

        # Step 2: Process each paragraph
        processed_lines = []
        for i, para in enumerate(paragraphs):
            # Handle empty paragraphs (from preserved empty lines)
            if not para.strip():
                if self.config.preserve_empty_lines:
                    processed_lines.append("")
                continue

            # Filter characters if alphabet is provided
            cleaned_para = self._clean_text(para, alphabet)

            # Wrap paragraph into lines
            wrapped_lines = self._wrap_paragraph(cleaned_para)

            # Add paragraph spacing/formatting based on style
            if i > 0:  # Only add spacing between paragraphs
                if self.config.paragraph_style == ParagraphStyle.PRESERVE_BREAKS:
                    processed_lines.append("")  # Empty line between paragraphs
                # Other styles might just append directly

            # Handle indentation
            if self.config.paragraph_style == ParagraphStyle.INDENT_FIRST and wrapped_lines:
                wrapped_lines[0] = "    " + wrapped_lines[0]

            processed_lines.extend(wrapped_lines)

        return processed_lines, {
            "num_lines": len(processed_lines),
            "num_paragraphs": len(paragraphs)
        }

    def get_pages(
        self,
        text: str,
        alphabet: Optional[Set[str]] = None
    ) -> Tuple[List[List[str]], Dict[str, Any]]:
        """
        Process text and split it into pages.

        Args:
            text: Input text string.
            alphabet: Optional set of allowed characters.

        Returns:
            Tuple containing:
            - List of pages, where each page is a list of line strings.
            - Metadata dictionary.
        """
        lines, metadata = self.process_text(text, alphabet)

        pages = []
        current_page = []

        for line in lines:
            if len(current_page) >= self.config.lines_per_page:
                pages.append(current_page)
                current_page = []
            current_page.append(line)

        if current_page:
            pages.append(current_page)

        metadata["num_pages"] = len(pages)
        return pages, metadata

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs based on newlines.
        """
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Split by double newline to find paragraphs
        # If preserving single line breaks is not desired, we treat single newlines as spaces
        if self.config.paragraph_style == ParagraphStyle.SINGLE_SPACE:
             # Collapse single newlines into spaces, split on double newlines
             paragraphs = [p.replace('\n', ' ') for p in re.split(r'\n\s*\n', text)]
        else:
             # Respect explicitly provided structure
             paragraphs = text.split('\n')

        if self.config.normalize_whitespace:
            paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in paragraphs]
        else:
            paragraphs = [p.strip() for p in paragraphs]

        return paragraphs

    def _clean_text(self, text: str, alphabet: Optional[Set[str]]) -> str:
        """
        Filter text to include only allowed characters.
        """
        if alphabet is None:
            return text

        return "".join(c for c in text if c in alphabet or c.isspace())

    def _wrap_paragraph(self, text: str) -> List[str]:
        """
        Wrap a single paragraph into lines of max_line_length.
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_len = len(word)

            # Check if word fits in current line
            # +1 for space if line is not empty
            space_len = 1 if current_length > 0 else 0

            if current_length + space_len + word_len <= self.config.max_line_length:
                current_line.append(word)
                current_length += space_len + word_len
            else:
                # Word doesn't fit
                if current_line:
                    lines.append(" ".join(current_line))

                # Handle very long words (basic hyphenation or forced break)
                if word_len > self.config.max_line_length:
                    # Force break the word
                    remaining = word
                    while len(remaining) > self.config.max_line_length:
                        chunk = remaining[:self.config.max_line_length]
                        lines.append(chunk)
                        remaining = remaining[self.config.max_line_length:]
                    current_line = [remaining]
                    current_length = len(remaining)
                else:
                    current_line = [word]
                    current_length = word_len

        if current_line:
            lines.append(" ".join(current_line))

        return lines
