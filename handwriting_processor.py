"""
Handwriting Processor - Integration layer between text processing and handwriting synthesis.

This module combines the enhanced text processor with the handwriting synthesis
engine to provide a complete solution for converting text to handwritten pages.
It handles text cleaning, formatting, pagination, and delegation to the handwriting
synthesis model.
"""

import os
from typing import List, Optional, Dict, Any, Tuple
from handwriting_synthesis import Hand
from text_processor import (
    TextProcessor,
    TextProcessingConfig,
    ParagraphStyle,
    create_alphabet_set
)


class HandwritingProcessor:
    """
    High-level interface for converting text to handwriting with intelligent
    text processing (line wrapping, paragraph handling, pagination).
    """

    def __init__(self, text_config: Optional[TextProcessingConfig] = None):
        """
        Initialize the handwriting processor.

        Args:
            text_config: Configuration for text processing. If None, default
                         configuration is used.
        """
        self.text_processor = TextProcessor(text_config or TextProcessingConfig())
        self.hand = Hand()

    def process_and_write(
        self,
        input_text: str,
        output_dir: str,
        alphabet: Optional[List[str]] = None,
        biases: Optional[float] = 0.95,
        styles: Optional[int] = 1,
        stroke_colors: Optional[str] = "Black",
        stroke_widths: Optional[float] = 1.0,
        page_params: Optional[List[Any]] = None,
        file_prefix: str = "result_page",
    ) -> Dict[str, Any]:
        """
        Process text and generate handwriting SVG files.

        This method takes raw input text, processes it into pages and lines using
        the TextProcessor, and then generates handwriting SVG files for each page
        using the Hand model.

        Args:
            input_text: The text to convert to handwriting.
            output_dir: Directory to save generated SVG files.
            alphabet: List of allowed characters.
            biases: Handwriting consistency (0.0 to 1.0). Higher values usually
                    mean more legible but less variable handwriting.
            styles: Handwriting style ID (1-12).
            stroke_colors: Color name (e.g., "Black", "Blue") or hex code.
            stroke_widths: Pen thickness in pixels/units.
            page_params: Page layout parameters list:
                         [line_height, total_lines, height, width, margin_left,
                          margin_top, page_color, margin_color, line_color].
            file_prefix: Prefix for output filenames (e.g., "result_page").

        Returns:
            Dictionary with processing metadata including:
            - output_dir: Directory where files were saved.
            - generated_files: List of paths to generated files.
            - settings: Dictionary of settings used.
            - num_pages: Number of pages generated.
            - num_lines: Total lines processed.
            - num_paragraphs: Total paragraphs processed.
        """
        # Create alphabet set
        alphabet_set = create_alphabet_set(alphabet) if alphabet else None

        # Process text into pages
        pages, metadata = self.text_processor.get_pages(input_text, alphabet_set)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Convert color names to hex
        color_map = {
            "Black": "#000000",
            "Blue": "#0000FF",
            "Red": "#FF0000",
            "Green": "#008000"
        }
        stroke_color_hex = color_map.get(stroke_colors, stroke_colors)

        # Generate handwriting for each page
        generated_files = []
        for page_num, page_lines in enumerate(pages):
            if not page_lines:  # Skip empty pages
                continue

            filename = os.path.join(output_dir, f"{file_prefix}_{page_num + 1}.svg")

            # Prepare parameters for hand.write()
            num_lines = len(page_lines)
            line_biases = [biases] * num_lines
            line_styles = [styles] * num_lines
            line_colors = [stroke_color_hex] * num_lines
            line_widths = [stroke_widths] * num_lines

            # Write the page
            self.hand.write(
                filename=filename,
                lines=page_lines,
                biases=line_biases,
                styles=line_styles,
                stroke_colors=line_colors,
                stroke_widths=line_widths,
                page=page_params
            )

            generated_files.append(filename)
            print(f"Page {page_num + 1} written to {filename}")

        # Update metadata with generation info
        metadata['output_dir'] = output_dir
        metadata['generated_files'] = generated_files
        metadata['settings'] = {
            'biases': biases,
            'styles': styles,
            'stroke_colors': stroke_colors,
            'stroke_widths': stroke_widths,
        }

        return metadata


def batch_process_texts(
    texts: List[str],
    output_base_dir: str,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Process multiple texts in batch.

    Iterates through a list of text strings and processes each one using
    the handwriting synthesis engine. Each text is saved in its own subdirectory.

    Args:
        texts: List of text strings to process.
        output_base_dir: Base directory for outputs (subdirs 'text_1', 'text_2', etc.
                         will be created here).
        **kwargs: Additional arguments passed to process_and_write().
                  (e.g., styles, biases, page_params).

    Returns:
        List of metadata dictionaries for each processed text.
    """
    processor = HandwritingProcessor(kwargs.get('text_config'))
    results = []

    for i, text in enumerate(texts):
        output_dir = os.path.join(output_base_dir, f"text_{i + 1}")
        kwargs_copy = dict(kwargs)
        kwargs_copy.pop('text_config', None)

        result = processor.process_and_write(
            input_text=text,
            output_dir=output_dir,
            **kwargs_copy
        )
        results.append(result)

    return results


def process_from_file(
    input_file: str,
    output_dir: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Process text from a file.

    Reads the content of the specified file and converts it to handwriting.

    Args:
        input_file: Path to input text file.
        output_dir: Directory to save SVG files.
        **kwargs: Additional arguments passed to process_and_write().

    Returns:
        Processing metadata dictionary.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    processor = HandwritingProcessor(kwargs.get('text_config'))
    kwargs_copy = dict(kwargs)
    kwargs_copy.pop('text_config', None)

    return processor.process_and_write(
        input_text=text,
        output_dir=output_dir,
        **kwargs_copy
    )


# Example usage
if __name__ == '__main__':
    # Sample text with multiple paragraphs
    sample_text = """Hello there! This is a test of the improved text processing system.

This system can handle multiple paragraphs intelligently. It wraps text at word boundaries, preserves paragraph breaks, and creates proper pagination.

The old system had issues with:
- Poor paragraph detection
- Basic word wrapping that didn't handle edge cases
- No smart pagination

This new system solves all of those problems! It provides:
- Intelligent paragraph detection and preservation
- Advanced word wrapping with configurable options
- Smart pagination to avoid orphans and widows
- Flexible configuration for different use cases

Try it out with your own text and see the difference!"""

    # Configure text processing
    config = TextProcessingConfig(
        max_line_length=60,
        lines_per_page=24,
        paragraph_style=ParagraphStyle.PRESERVE_BREAKS,
        preserve_empty_lines=True,
    )

    # Default alphabet (from the original code)
    alphabet = [
        '\x00', ' ', '!', '"', '@' ,'#', "'", '(', ')', ',', '-', '.',
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';',
        '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
        'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'Y',
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
        'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
        'y', 'z'
    ]

    # Page parameters (A4-like dimensions)
    page = [
        32,      # line_height
        24,      # total_lines_per_page
        896,     # view_height
        633.472, # view_width
        -64,     # margin_left
        -96,     # margin_top
        "white", # page_color
        "red",   # margin_color
        "lightgray"  # line_color
    ]

    # Process the text
    processor = HandwritingProcessor(text_config=config)

    try:
        result = processor.process_and_write(
            input_text=sample_text,
            output_dir='img',
            alphabet=alphabet,
            biases=0.95,
            styles=1,
            stroke_colors="Black",
            stroke_widths=1.0,
            page_params=page,
            file_prefix="sample_page"
        )

        print("\n=== Processing Complete ===")
        print(f"Pages generated: {result['num_pages']}")
        print(f"Total lines: {result['num_lines']}")
        print(f"Paragraphs processed: {result['num_paragraphs']}")
        print(f"\nFiles created:")
        for file in result['generated_files']:
            print(f"  - {file}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
