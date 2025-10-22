#!/usr/bin/env python3
"""
Database migration script to add character override tables.

Run this script to add the character override tables to an existing WriteBot database.
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.app import app
from webapp.models import db, CharacterOverrideCollection, CharacterOverride


def migrate_character_overrides():
    """Add character override tables to the database."""
    with app.app_context():
        print("Character Override Migration")
        print("=" * 50)

        try:
            # Create the new tables
            print("\nCreating character override tables...")
            db.create_all()
            print("✓ Character override tables created successfully!")

            # Verify tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            if 'character_override_collections' in tables:
                print("✓ Table 'character_override_collections' verified")
            else:
                print("⊘ Warning: Table 'character_override_collections' not found")

            if 'character_overrides' in tables:
                print("✓ Table 'character_overrides' verified")
            else:
                print("⊘ Warning: Table 'character_overrides' not found")

            print("\n" + "=" * 50)
            print("Migration complete!")
            print("=" * 50)
            print("\nYou can now use character overrides in the admin backend.")
            print("Navigate to: /admin/character-overrides")

        except Exception as e:
            print(f"\n✗ Error during migration: {e}")
            print("\nIf tables already exist, this is normal.")
            return 1

        return 0


if __name__ == '__main__':
    exit_code = migrate_character_overrides()
    sys.exit(exit_code)
