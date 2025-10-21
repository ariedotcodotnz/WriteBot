#!/usr/bin/env python3
"""
Test script to verify the rotation correction fixes cumulative slant issues.

This script tests:
1. Rotation correction when stitching chunks
2. Dynamic chunk sizing based on word length
3. Long text sequences to ensure slant doesn't accumulate
"""

import numpy as np
from handwriting_synthesis import Hand

def test_rotation_correction():
    """Test rotation correction with a long text sequence."""
    hand = Hand()

    # Test text with mix of short and long words
    long_text = """
    The quick brown fox jumps over the lazy dog. This is a test of the emergency broadcast system.
    If this had been an actual emergency, you would have been instructed where to tune in your area for news and official information.
    This concludes this test of the emergency broadcast system. We now return you to your regularly scheduled programming.
    """

    print("Testing with rotation correction enabled...")
    hand.write_chunked(
        filename='img/test_rotation_on.svg',
        text=long_text,
        max_line_width=800.0,
        words_per_chunk=3,
        chunk_spacing=8.0,
        rotate_chunks=True,  # Enable rotation
        min_words_per_chunk=2,
        max_words_per_chunk=8,
        target_chars_per_chunk=25,
        biases=0.75,
        styles=9,
    )
    print("✓ Generated with rotation correction: img/test_rotation_on.svg")

    print("\nTesting without rotation correction for comparison...")
    hand.write_chunked(
        filename='img/test_rotation_off.svg',
        text=long_text,
        max_line_width=800.0,
        words_per_chunk=3,
        chunk_spacing=8.0,
        rotate_chunks=False,  # Disable rotation
        min_words_per_chunk=2,
        max_words_per_chunk=8,
        target_chars_per_chunk=25,
        biases=0.75,
        styles=9,
    )
    print("✓ Generated without rotation correction: img/test_rotation_off.svg")

    print("\n" + "="*60)
    print("Test completed!")
    print("Compare the two files to see the difference:")
    print("  - test_rotation_on.svg  : With rotation correction (should be straight)")
    print("  - test_rotation_off.svg : Without rotation correction (may show slant)")
    print("="*60)

def test_dynamic_chunking():
    """Test dynamic chunk sizing with different word lengths."""
    hand = Hand()

    # Text with short words
    short_words = "I am at a do or we go to it in an as of be"

    # Text with long words
    long_words = "Extraordinarily magnificent hippopotamus rhinoceros interchangeable"

    # Text with mixed words
    mixed_words = "The extraordinarily quick brown hippopotamus jumps"

    print("\nTesting dynamic chunking...")
    print(f"Short words: {short_words}")
    print(f"Long words: {long_words}")
    print(f"Mixed words: {mixed_words}")

    hand.write_chunked(
        filename='img/test_dynamic_chunks.svg',
        text=f"{short_words}\n{long_words}\n{mixed_words}",
        max_line_width=800.0,
        words_per_chunk=3,
        chunk_spacing=8.0,
        rotate_chunks=True,
        min_words_per_chunk=2,
        max_words_per_chunk=8,
        target_chars_per_chunk=25,
        biases=0.75,
        styles=9,
    )
    print("✓ Generated with dynamic chunking: img/test_dynamic_chunks.svg")

if __name__ == '__main__':
    print("Testing rotation correction and dynamic chunking...")
    print("This may take a few minutes...\n")

    test_rotation_correction()
    test_dynamic_chunking()

    print("\n✓ All tests completed successfully!")
