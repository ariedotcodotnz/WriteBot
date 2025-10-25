#!/usr/bin/env python3
"""
Quick test script to verify character override alignment and scaling.
This will generate a test SVG with both AI-generated text and override characters.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_alignment():
    """Test character override alignment and scaling."""
    from webapp.app import app, db
    from webapp.models import CharacterOverrideCollection, CharacterOverride
    from handwriting_synthesis.hand.Hand import Hand

    with app.app_context():
        print("Testing character override alignment and scaling...")

        # Find or create test collection
        collection = CharacterOverrideCollection.query.filter_by(
            name="Test Collection (@)"
        ).first()

        if not collection:
            print("ERROR: Test collection not found. Run test_character_override.py first.")
            return False

        # Verify @ override exists
        at_override = CharacterOverride.query.filter_by(
            collection_id=collection.id,
            character='@'
        ).first()

        if not at_override:
            print("ERROR: @ symbol override not found. Run test_character_override.py first.")
            return False

        print(f"Using collection: {collection.name} (ID: {collection.id})")
        print(f"Override viewbox: {at_override.viewbox_width} x {at_override.viewbox_height}")

        # Generate test output with mixed text
        hand = Hand()

        test_text = [
            "test@example.com",
            "@@ aligned @@",
            "before @ after"
        ]

        output_file = "test_alignment_output.svg"

        print(f"\nGenerating test output: {output_file}")
        print(f"Test text: {test_text}")

        hand.write(
            filename=output_file,
            lines=test_text,
            biases=[0.5] * len(test_text),
            stroke_colors=['black'] * len(test_text),
            stroke_widths=[2] * len(test_text),
            character_override_collection_id=collection.id,
            page_size='A4',
            align='left',
            line_height=80
        )

        print(f"\n✓ Successfully generated {output_file}")
        print("\nVerification checklist:")
        print("  1. Open test_alignment_output.svg in a browser")
        print("  2. Check that @ symbols are vertically aligned with adjacent text")
        print("  3. Check that @ symbols are scaled to match the height of letters")
        print("  4. Check that @ symbols don't appear too high or too low")

        return True

if __name__ == '__main__':
    try:
        success = test_alignment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
