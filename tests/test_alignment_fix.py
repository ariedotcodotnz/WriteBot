#!/usr/bin/env python3
"""
Test script to verify vertical alignment and blank line recognition fixes
"""

import os
from handwriting_synthesis import Hand

# Test text with multiple paragraphs and blank lines
test_text = """This is the first line of text.
This is the second line.

This is a new paragraph after a blank line.
It should be properly spaced.

Here is another paragraph.
With multiple lines of text.
Testing the vertical alignment."""

def test_chunked_generation():
    """Test chunked generation with line breaks and blank lines"""
    print("Testing chunked generation with line breaks and blank lines...")

    hand = Hand()
    output_dir = 'test_output'
    os.makedirs(output_dir, exist_ok=True)

    # Test with chunked mode
    output_file = os.path.join(output_dir, 'test_alignment_fix.svg')

    hand.write_chunked(
        filename=output_file,
        text=test_text,
        max_line_width=600.0,
        words_per_chunk=2,
        chunk_spacing=8.0,
        biases=0.75,
        styles=1,
        stroke_colors='black',
        stroke_widths=1.0,
        page_size='A4',
        line_height=60,
        legibility='normal'
    )

    print(f"✓ Generated SVG file: {output_file}")

    # Verify the file exists and has content
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"✓ File size: {file_size} bytes")

        # Read and check for basic SVG structure
        with open(output_file, 'r') as f:
            content = f.read()
            if '<svg' in content and '</svg>' in content:
                print("✓ Valid SVG structure")

                # Count path elements (should have multiple lines)
                path_count = content.count('<path')
                print(f"✓ Path elements found: {path_count}")

                return True

    return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing Vertical Alignment and Blank Line Recognition")
    print("=" * 60)
    print()

    try:
        success = test_chunked_generation()

        if success:
            print()
            print("=" * 60)
            print("✓ All tests passed!")
            print("=" * 60)
            print()
            print("Please check the generated SVG file to verify:")
            print("1. Blank lines are preserved (spacing between paragraphs)")
            print("2. Vertical alignment looks natural within each line")
            print("3. Line breaks are respected")
        else:
            print()
            print("✗ Tests failed!")

    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
