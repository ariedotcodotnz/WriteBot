"""
Demonstration of Improved Text Processing

This script demonstrates the improvements in text processing for WriteBot,
including better paragraph handling, line wrapping, and pagination.
"""

from text_processor import (
    TextProcessor,
    TextProcessingConfig,
    ParagraphStyle,
    create_alphabet_set,
    process_text_simple
)


def demo_basic_processing():
    """Demonstrate basic text processing"""
    print("=" * 70)
    print("DEMO 1: Basic Text Processing")
    print("=" * 70)

    text = """This is a sample paragraph that will be wrapped across multiple lines based on the maximum line length setting.

This is a second paragraph. It should be separated from the first paragraph by a blank line, demonstrating proper paragraph detection and preservation.

Finally, this is a third paragraph that shows how the system handles multiple paragraphs in sequence."""

    pages, metadata = process_text_simple(
        text,
        max_line_length=50,
        lines_per_page=15
    )

    print(f"\nInput text length: {metadata['original_length']} characters")
    print(f"Paragraphs detected: {metadata['num_paragraphs']}")
    print(f"Total lines: {metadata['num_lines']}")
    print(f"Pages generated: {metadata['num_pages']}")
    print(f"Lines per page: {metadata['lines_per_page']}")

    for page_num, page in enumerate(pages, 1):
        print(f"\n--- Page {page_num} ({len(page)} lines) ---")
        for i, line in enumerate(page, 1):
            print(f"{i:2d}: '{line}'")


def demo_paragraph_styles():
    """Demonstrate different paragraph styles"""
    print("\n\n" + "=" * 70)
    print("DEMO 2: Paragraph Styling Options")
    print("=" * 70)

    text = """First paragraph here.

Second paragraph here.

Third paragraph here."""

    styles = [
        (ParagraphStyle.PRESERVE_BREAKS, "Preserve Breaks (default)"),
        (ParagraphStyle.SINGLE_SPACE, "Single Space Between Paragraphs"),
        (ParagraphStyle.NO_BREAKS, "No Breaks (continuous flow)"),
        (ParagraphStyle.INDENT_FIRST, "Indent First Line"),
    ]

    for style, description in styles:
        print(f"\n--- {description} ---")
        config = TextProcessingConfig(
            max_line_length=40,
            lines_per_page=20,
            paragraph_style=style,
            indent_spaces=4
        )
        processor = TextProcessor(config)
        lines, _ = processor.process_text(text)

        for i, line in enumerate(lines[:10], 1):  # Show first 10 lines
            print(f"{i:2d}: '{line}'")


def demo_long_words():
    """Demonstrate handling of long words"""
    print("\n\n" + "=" * 70)
    print("DEMO 3: Long Word Handling")
    print("=" * 70)

    text = "This text contains supercalifragilisticexpialidocious and other extraordinarily long words that exceed the maximum line length."

    print("\n--- Without Hyphenation ---")
    config1 = TextProcessingConfig(
        max_line_length=30,
        hyphenate_long_words=False
    )
    processor1 = TextProcessor(config1)
    lines1, _ = processor1.process_text(text)

    for i, line in enumerate(lines1, 1):
        print(f"{i}: '{line}' ({len(line)} chars)")

    print("\n--- With Hyphenation ---")
    config2 = TextProcessingConfig(
        max_line_length=30,
        hyphenate_long_words=True
    )
    processor2 = TextProcessor(config2)
    lines2, _ = processor2.process_text(text)

    for i, line in enumerate(lines2, 1):
        print(f"{i}: '{line}' ({len(line)} chars)")


def demo_character_sanitization():
    """Demonstrate character sanitization"""
    print("\n\n" + "=" * 70)
    print("DEMO 4: Character Sanitization")
    print("=" * 70)

    text = "Hello! This text has ñ, é, ü and other spëcial çharacters that might not be in the alphabet. Also numbers: 123 and symbols: @#$%"

    # Define a limited alphabet
    alphabet = [
        ' ', '!', '.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
        'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
    ]

    print(f"\nOriginal text:")
    print(f"  {text}")

    alphabet_set = create_alphabet_set(alphabet)
    processor = TextProcessor(TextProcessingConfig(max_line_length=60))
    lines, _ = processor.process_text(text, alphabet_set)

    print(f"\nSanitized text:")
    for line in lines:
        print(f"  {line}")


def demo_pagination():
    """Demonstrate pagination with multiple pages"""
    print("\n\n" + "=" * 70)
    print("DEMO 5: Multi-Page Pagination")
    print("=" * 70)

    # Generate a longer text
    paragraphs = [
        "This is the first paragraph of a longer document. It contains enough text to demonstrate how the pagination system works across multiple pages.",
        "The second paragraph continues with more content. The system intelligently splits content into pages while respecting paragraph boundaries where possible.",
        "Here's a third paragraph that adds even more content to ensure we get multiple pages in the output.",
        "A fourth paragraph provides additional text for demonstration purposes.",
        "And finally, a fifth paragraph rounds out our sample document and ensures we have enough content for proper pagination testing."
    ]

    text = "\n\n".join(paragraphs)

    pages, metadata = process_text_simple(
        text,
        max_line_length=40,
        lines_per_page=8  # Small page size to force multiple pages
    )

    print(f"\nTotal pages: {metadata['num_pages']}")
    print(f"Total lines: {metadata['num_lines']}")
    print(f"Lines distribution: {metadata['lines_per_page']}")

    for page_num, page in enumerate(pages, 1):
        print(f"\n┌─ Page {page_num}/{metadata['num_pages']} " + "─" * 45 + "┐")
        for i, line in enumerate(page, 1):
            print(f"│ {i:2d}: {line:<45} │")
        print("└" + "─" * 54 + "┘")


def demo_comparison():
    """Compare old vs new text processing"""
    print("\n\n" + "=" * 70)
    print("DEMO 6: Old vs New Implementation Comparison")
    print("=" * 70)

    text = """First paragraph.

Second paragraph.

Third paragraph."""

    print("\n--- OLD IMPLEMENTATION (Basic) ---")
    # Simulate old implementation
    lines = [line.strip() if line.strip() else '.' for line in text.split("\n")]
    print("Issues:")
    print("  - Empty lines converted to '.'")
    print("  - Poor paragraph preservation")
    print("  - Basic wrapping logic")
    print("\nOutput:")
    for i, line in enumerate(lines, 1):
        print(f"  {i}: '{line}'")

    print("\n--- NEW IMPLEMENTATION (Enhanced) ---")
    processor = TextProcessor(TextProcessingConfig(max_line_length=50))
    new_lines, meta = processor.process_text(text)
    print("Improvements:")
    print("  ✓ Proper paragraph detection")
    print("  ✓ Empty lines preserved correctly")
    print("  ✓ Smart word wrapping")
    print("  ✓ Configurable styling options")
    print(f"\nOutput ({meta['num_paragraphs']} paragraphs, {meta['num_lines']} lines):")
    for i, line in enumerate(new_lines, 1):
        print(f"  {i}: '{line}'")


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "WriteBot - Enhanced Text Processing Demo" + " " * 16 + "║")
    print("╚" + "=" * 68 + "╝")

    demo_basic_processing()
    demo_paragraph_styles()
    demo_long_words()
    demo_character_sanitization()
    demo_pagination()
    demo_comparison()

    print("\n\n" + "=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)
    print("\nKey Improvements:")
    print("  ✓ Intelligent paragraph detection and preservation")
    print("  ✓ Multiple paragraph styling options")
    print("  ✓ Advanced word wrapping with hyphenation support")
    print("  ✓ Smart pagination")
    print("  ✓ Character sanitization with alphabet support")
    print("  ✓ Comprehensive metadata tracking")
    print("  ✓ Flexible configuration options")
    print()


if __name__ == '__main__':
    main()
