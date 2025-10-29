"""
Database migration script to add enhanced template preset fields.
Run this script to add all the advanced configuration options to existing templates.
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.app import app
from webapp.models import db


def migrate_database():
    """Add new columns to template_presets table."""
    with app.app_context():
        print("Starting database migration for enhanced template options...")

        # Get database connection
        connection = db.engine.connect()

        # List of columns to add with their definitions
        new_columns = [
            # Line settings
            ('empty_line_spacing', 'FLOAT'),

            # Text alignment and scaling
            ('text_alignment', "VARCHAR(20) DEFAULT 'left' NOT NULL"),
            ('global_scale', 'FLOAT DEFAULT 1.0'),
            ('auto_size', 'BOOLEAN DEFAULT 0'),
            ('manual_size_scale', 'FLOAT'),

            # Style control
            ('biases', 'TEXT'),
            ('per_line_styles', 'TEXT'),
            ('stroke_colors', 'TEXT'),
            ('stroke_widths', 'TEXT'),
            ('horizontal_stretch', 'FLOAT DEFAULT 1.0'),
            ('denoise', 'BOOLEAN DEFAULT 0'),

            # Text wrapping
            ('character_width', 'FLOAT'),
            ('wrap_ratio', 'FLOAT'),
            ('wrap_utilization', 'FLOAT'),

            # Advanced generation
            ('use_chunked_generation', 'BOOLEAN DEFAULT 0'),
            ('adaptive_chunking', 'BOOLEAN DEFAULT 0'),
            ('adaptive_strategy', 'VARCHAR(50)'),
            ('words_per_chunk', 'INTEGER'),
            ('chunk_spacing', 'FLOAT'),
            ('max_line_width', 'FLOAT'),
        ]

        print("\nAdding new columns to template_presets table...")

        # Check which columns already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('template_presets')]

        added_count = 0
        skipped_count = 0

        for column_name, column_type in new_columns:
            if column_name in existing_columns:
                print(f"  ⊘ Column '{column_name}' already exists, skipping...")
                skipped_count += 1
                continue

            try:
                # SQLite syntax for ALTER TABLE
                sql = f"ALTER TABLE template_presets ADD COLUMN {column_name} {column_type}"
                connection.execute(db.text(sql))
                connection.commit()
                print(f"  ✓ Added column: {column_name}")
                added_count += 1
            except Exception as e:
                print(f"  ✗ Error adding column '{column_name}': {e}")
                connection.rollback()

        connection.close()

        print(f"\nMigration completed!")
        print(f"  - Added: {added_count} columns")
        print(f"  - Skipped: {skipped_count} columns (already exist)")

        if added_count > 0:
            print("\n" + "="*60)
            print("New template options available:")
            print("  • Text Alignment (left/center/right)")
            print("  • Global Scale (overall sizing)")
            print("  • Auto Size & Manual Size Scale")
            print("  • Empty Line Spacing")
            print("  • Style Control (biases, per-line styles)")
            print("  • Stroke Colors & Widths (per-line)")
            print("  • Horizontal Stretch")
            print("  • Denoise toggle")
            print("  • Text Wrapping (character width, ratios)")
            print("  • Chunked Generation options")
            print("  • Adaptive Chunking strategies")
            print("="*60)


if __name__ == '__main__':
    migrate_database()
