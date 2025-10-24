"""
Database migration script to add page size and template preset tables.
Run this script to migrate the database and populate default page sizes.
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.app import app
from webapp.models import db, PageSizePreset, TemplatePreset

# Default page sizes from page_utils.py
DEFAULT_PAGE_SIZES = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
}


def migrate_database():
    """Create tables and populate default page sizes."""
    with app.app_context():
        print("Starting database migration...")

        # Create tables
        print("Creating tables...")
        db.create_all()
        print("Tables created successfully!")

        # Check if default page sizes already exist
        existing_defaults = PageSizePreset.query.filter_by(is_default=True).count()
        if existing_defaults > 0:
            print(f"Found {existing_defaults} existing default page sizes. Skipping population.")
            print("Migration completed!")
            return

        # Populate default page sizes
        print("Populating default page sizes...")
        for name, (width, height) in DEFAULT_PAGE_SIZES.items():
            page_size = PageSizePreset(
                name=name,
                width=width,
                height=height,
                unit='mm',
                is_active=True,
                is_default=True,
                created_by=None  # System defaults have no creator
            )
            db.session.add(page_size)
            print(f"  Added {name}: {width} x {height} mm")

        db.session.commit()
        print("Default page sizes populated successfully!")

        print("\nMigration completed successfully!")
        print("\nDefault page sizes added:")
        for name, (width, height) in DEFAULT_PAGE_SIZES.items():
            print(f"  - {name}: {width} x {height} mm")


if __name__ == '__main__':
    migrate_database()
