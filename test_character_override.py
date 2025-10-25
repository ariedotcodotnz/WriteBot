#!/usr/bin/env python3
"""
Test script for character override functionality.

This script helps test character overrides by:
1. Creating a test collection
2. Uploading a character override (@ symbol)
3. Generating a test output with the override
4. Verifying the scaling matches AI-generated text
"""

import sys
import os

# Add parent directory to path to import webapp modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_character_override():
    """Test character override upload and rendering."""
    from webapp.app import create_app, db
    from webapp.models import CharacterOverrideCollection, CharacterOverride

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("Character Override Test Script")
        print("=" * 60)

        # Step 1: Check if test collection exists
        collection_name = "Test Collection (@)"
        collection = CharacterOverrideCollection.query.filter_by(name=collection_name).first()

        if collection:
            print(f"\n✓ Test collection '{collection_name}' already exists (ID: {collection.id})")
        else:
            print(f"\n➤ Creating test collection: '{collection_name}'")
            collection = CharacterOverrideCollection(
                name=collection_name,
                description="Test collection for @ symbol override",
                created_by=1,  # Assuming admin user ID is 1
                is_active=True
            )
            db.session.add(collection)
            db.session.commit()
            print(f"✓ Created collection (ID: {collection.id})")

        # Step 2: Check if @ override exists
        at_override = CharacterOverride.query.filter_by(
            collection_id=collection.id,
            character='@'
        ).first()

        if at_override:
            print(f"\n✓ @ symbol override already exists")
            print(f"  - Viewbox: {at_override.viewbox_width} x {at_override.viewbox_height}")
            print(f"  - SVG length: {len(at_override.svg_data)} characters")
        else:
            # Read the test SVG file
            svg_path = os.path.join(os.path.dirname(__file__), 'test_at_symbol.svg')

            if not os.path.exists(svg_path):
                print(f"\n✗ ERROR: Test SVG file not found at: {svg_path}")
                print("  Please ensure test_at_symbol.svg exists")
                return False

            with open(svg_path, 'r') as f:
                svg_content = f.read()

            print(f"\n➤ Uploading @ symbol override...")
            print(f"  - SVG file: {svg_path}")

            # Parse viewBox from SVG
            import xml.etree.ElementTree as ET
            root = ET.fromstring(svg_content)
            viewbox = root.get('viewBox')

            if viewbox:
                parts = [float(x) for x in viewbox.strip().split()]
                vb_x, vb_y, vb_width, vb_height = parts
            else:
                print("  ✗ ERROR: SVG must have a viewBox attribute")
                return False

            at_override = CharacterOverride(
                collection_id=collection.id,
                character='@',
                svg_data=svg_content,
                viewbox_x=vb_x,
                viewbox_y=vb_y,
                viewbox_width=vb_width,
                viewbox_height=vb_height,
                baseline_offset=0.0
            )

            db.session.add(at_override)
            db.session.commit()

            print(f"✓ Successfully uploaded @ symbol override")
            print(f"  - Viewbox: {vb_width} x {vb_height}")

        # Step 3: Show all overrides in collection
        all_overrides = CharacterOverride.query.filter_by(collection_id=collection.id).all()
        unique_chars = set(o.character for o in all_overrides)

        print(f"\n{'='*60}")
        print(f"Collection Summary")
        print(f"{'='*60}")
        print(f"  Collection ID: {collection.id}")
        print(f"  Total variants: {len(all_overrides)}")
        print(f"  Unique characters: {len(unique_chars)}")
        print(f"  Characters: {', '.join(sorted(unique_chars))}")

        # Step 4: Usage instructions
        print(f"\n{'='*60}")
        print(f"How to Test")
        print(f"{'='*60}")
        print(f"1. Start the webapp:")
        print(f"   python run.py")
        print(f"")
        print(f"2. Log in to the admin panel")
        print(f"")
        print(f"3. Navigate to Character Overrides")
        print(f"")
        print(f"4. In the main generation form:")
        print(f"   - Select collection: '{collection_name}' (ID: {collection.id})")
        print(f"   - Enter text containing @: 'test@example.com'")
        print(f"   - Click Generate")
        print(f"")
        print(f"5. The @ symbol should render at the same height as AI-generated text")
        print(f"")
        print(f"Expected behavior:")
        print(f"  - @ symbol appears as uploaded SVG (not as a gap)")
        print(f"  - @ symbol matches the vertical height of other letters")
        print(f"  - No 'red dashed box' or missing character placeholder")

        print(f"\n{'='*60}")
        print(f"✓ Test setup complete!")
        print(f"{'='*60}\n")

        return True


if __name__ == '__main__':
    try:
        success = test_character_override()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
