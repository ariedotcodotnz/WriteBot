#!/usr/bin/env python3
"""
Test script to reproduce spacing issues with override characters adjacent to spaces.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath('.'))

from handwriting_synthesis.hand import Hand

def main():
    # Create a hand instance
    hand = Hand()

    # Create an override collection for the @ symbol
    collection_id = hand.create_override_collection("Test Collection")
    print(f"Created override collection: {collection_id}")

    # Upload a simple @ symbol SVG
    at_symbol_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M 50,20 A 25,25 0 1,1 50,70 A 25,25 0 1,1 50,20 M 65,45 A 15,15 0 1,0 65,55"
        stroke="black" stroke-width="3" fill="none"/>
</svg>'''

    hand.upload_override_character(collection_id, "@", at_symbol_svg)
    print("Uploaded @ symbol override")

    # Set the override collection
    hand.set_override_collection(collection_id)

    # Test different spacing scenarios
    test_cases = [
        "test@example",           # No spaces
        "test @example",          # Space before @
        "test@ example",          # Space after @
        "test @ example",         # Spaces on both sides
        "a @",                    # Space before at end
        "@ a",                    # Space after at start
        " @ ",                    # Spaces on both sides with single chars
        "word @word",             # Space before only
        "word@ word",             # Space after only
        "word @ word",            # Spaces on both sides
    ]

    for i, test_text in enumerate(test_cases):
        print(f"\nTest case {i+1}: '{test_text}'")
        output_file = f"test_space_spacing_{i+1}.svg"

        lines = hand.write(
            test_text,
            stroke_colors=['blue'],
            stroke_widths=[2],
            line_height=60,
            view_width=800,
            view_height=120
        )

        hand.draw(
            lines=lines,
            out_path=output_file,
            stroke_colors=['blue'],
            stroke_widths=[2],
            line_height=60,
            view_width=800,
            view_height=120
        )

        print(f"  Generated: {output_file}")

    print("\nAll test cases completed!")
    print("Please review the generated SVG files to check spacing.")

if __name__ == "__main__":
    main()
