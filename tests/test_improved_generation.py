#!/usr/bin/env python3
"""
Test script to verify improved text generation with chunked method
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from handwriting_synthesis.hand import Hand
from handwriting_synthesis.drawing import operations

def test_improved_limits():
    """Test that the new limits are in place"""
    print("Testing improved limits...")
    print(f"MAX_CHAR_LEN: {operations.MAX_CHAR_LEN} (should be 120)")
    print(f"MAX_STROKE_LEN: {operations.MAX_STROKE_LEN} (should be 2400)")

    assert operations.MAX_CHAR_LEN == 120, f"Expected MAX_CHAR_LEN=120, got {operations.MAX_CHAR_LEN}"
    assert operations.MAX_STROKE_LEN == 2400, f"Expected MAX_STROKE_LEN=2400, got {operations.MAX_STROKE_LEN}"
    print("✓ Limits test passed!\n")

def test_chunked_generation():
    """Test chunked generation with improved parameters"""
    print("Testing chunked generation...")

    hand = Hand()

    # Test text - longer than before to test new limits
    test_text = "The quick brown fox jumps over the lazy dog. This is a longer line to test the improved text generation capabilities with chunked processing."

    output_file = "/tmp/test_chunked_output.svg"

    try:
        # Use new defaults: words_per_chunk=2, max_line_width=800.0
        hand.write_chunked(
            filename=output_file,
            text=test_text,
            max_line_width=800.0,
            words_per_chunk=2,
            chunk_spacing=8.0,
        )

        # Check if output file was created
        assert os.path.exists(output_file), "Output file was not created"

        # Check file size
        file_size = os.path.getsize(output_file)
        assert file_size > 0, "Output file is empty"

        print(f"✓ Chunked generation test passed! Output file size: {file_size} bytes\n")

        # Read and show first few lines
        with open(output_file, 'r') as f:
            lines = f.readlines()
            print(f"Generated SVG has {len(lines)} lines")
            print("First 5 lines:")
            for line in lines[:5]:
                print(line.rstrip())

        return True

    except Exception as e:
        print(f"✗ Chunked generation test failed: {e}")
        return False

    finally:
        # Cleanup
        if os.path.exists(output_file):
            os.remove(output_file)

def test_longer_line():
    """Test that longer lines (up to 120 chars) are now supported"""
    print("\nTesting longer line support...")

    hand = Hand()

    # Create a line with exactly 100 characters (within new 120 limit)
    long_line = "A" * 100

    output_file = "/tmp/test_long_line.svg"

    try:
        # This should work now with MAX_CHAR_LEN=120
        hand.write(
            filename=output_file,
            lines=[long_line],
        )

        assert os.path.exists(output_file), "Output file was not created"
        print(f"✓ Long line test passed! Successfully generated line with {len(long_line)} characters\n")
        return True

    except ValueError as e:
        if "must be at most" in str(e):
            print(f"✗ Long line test failed: {e}")
            return False
        raise

    finally:
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Improved Text Generation")
    print("=" * 60 + "\n")

    all_passed = True

    # Run tests
    try:
        test_improved_limits()
    except AssertionError as e:
        print(f"✗ {e}\n")
        all_passed = False

    all_passed = test_chunked_generation() and all_passed
    all_passed = test_longer_line() and all_passed

    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
