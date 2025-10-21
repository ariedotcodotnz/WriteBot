#!/usr/bin/env python3
"""
Test script for chunk-based text generation.

This tests the new write_chunked() method which:
1. Generates text in small chunks (a few words at a time)
2. Measures actual stroke width of each chunk
3. Stitches chunks together into lines based on actual measurements

This approach solves the long-range dependency problem and allows
better line filling compared to the traditional line-by-line approach.
"""

from handwriting_synthesis.hand.Hand import Hand

def test_chunked_generation():
    """Test basic chunk-based generation."""
    print("Initializing Hand model...")
    hand = Hand()

    # Test text with multiple sentences
    test_text = "This is a test of the new chunk based text generation system. It generates a few words at a time and then stitches them together. This solves the long range dependency problem."

    print(f"\nTest text: {test_text}")
    print(f"Text length: {len(test_text)} characters")

    # Test with different parameters
    test_configs = [
        {
            "name": "Default (4 words per chunk)",
            "words_per_chunk": 4,
            "max_line_width": 550.0,
            "chunk_spacing": 8.0
        },
        {
            "name": "Smaller chunks (3 words)",
            "words_per_chunk": 3,
            "max_line_width": 550.0,
            "chunk_spacing": 8.0
        },
        {
            "name": "Larger chunks (5 words)",
            "words_per_chunk": 5,
            "max_line_width": 550.0,
            "chunk_spacing": 8.0
        },
    ]

    for i, config in enumerate(test_configs):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {config['name']}")
        print(f"{'='*60}")

        output_file = f"test_chunked_output_{i+1}.svg"

        try:
            print(f"Generating with:")
            print(f"  - words_per_chunk: {config['words_per_chunk']}")
            print(f"  - max_line_width: {config['max_line_width']}")
            print(f"  - chunk_spacing: {config['chunk_spacing']}")

            hand.write_chunked(
                filename=output_file,
                text=test_text,
                max_line_width=config['max_line_width'],
                words_per_chunk=config['words_per_chunk'],
                chunk_spacing=config['chunk_spacing'],
                biases=0.5,
                page_size='A4',
                units='mm',
                margins=20,
                align='left',
                global_scale=1.0,
                orientation='portrait',
                denoise=True,
            )

            print(f"✓ Successfully generated: {output_file}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All tests completed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_chunked_generation()
