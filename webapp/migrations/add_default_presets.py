#!/usr/bin/env python3
"""
Migration script to add default page size presets and template presets.

This script populates the database with default page sizes (A4, A5, Letter, Legal)
and some common template presets.
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.app import app
from webapp.models import db, PageSizePreset, TemplatePreset


def add_default_page_sizes():
    """Add default page size presets to the database."""
    print("Adding default page size presets...")

    default_sizes = [
        {
            'name': 'A5',
            'description': 'A5 paper size (148 x 210 mm)',
            'width': 148.0,
            'height': 210.0,
            'is_default': True,
        },
        {
            'name': 'A4',
            'description': 'A4 paper size (210 x 297 mm)',
            'width': 210.0,
            'height': 297.0,
            'is_default': True,
        },
        {
            'name': 'Letter',
            'description': 'US Letter size (8.5 x 11 inches)',
            'width': 215.9,
            'height': 279.4,
            'is_default': True,
        },
        {
            'name': 'Legal',
            'description': 'US Legal size (8.5 x 14 inches)',
            'width': 215.9,
            'height': 355.6,
            'is_default': True,
        },
    ]

    added_count = 0
    for size_data in default_sizes:
        # Check if already exists
        existing = PageSizePreset.query.filter_by(name=size_data['name']).first()
        if existing:
            print(f"  ⊘ Page size '{size_data['name']}' already exists, skipping...")
            continue

        preset = PageSizePreset(**size_data)
        db.session.add(preset)
        added_count += 1
        print(f"  ✓ Added page size: {size_data['name']} ({size_data['width']}x{size_data['height']} mm)")

    db.session.commit()
    print(f"Added {added_count} page size presets.\n")
    return added_count


def add_default_templates():
    """Add default template presets to the database."""
    print("Adding default template presets...")

    # Get the page size presets
    a4 = PageSizePreset.query.filter_by(name='A4').first()
    letter = PageSizePreset.query.filter_by(name='Letter').first()

    if not a4 or not letter:
        print("  ⚠ Warning: A4 or Letter page sizes not found. Skipping template creation.")
        return 0

    default_templates = [
        {
            'name': 'A4 Portrait - Standard',
            'description': 'A4 portrait with 20mm margins, standard settings',
            'page_size_id': a4.id,
            'orientation': 'portrait',
            'margin_top': 20.0,
            'margin_right': 20.0,
            'margin_bottom': 20.0,
            'margin_left': 20.0,
            'line_height': 60.0,
            'alignment': 'left',
            'background': 'white',
            'global_scale': 1.0,
            'default_style': 9,
            'default_bias': 0.75,
            'legibility': 0.0,
            'stroke_color': 'black',
            'stroke_width': 2,
            'x_stretch': 1.0,
            'denoise': False,
            'use_chunked': False,
            'is_default': True,
        },
        {
            'name': 'A4 Landscape - Wide',
            'description': 'A4 landscape with 15mm margins for wider content',
            'page_size_id': a4.id,
            'orientation': 'landscape',
            'margin_top': 15.0,
            'margin_right': 15.0,
            'margin_bottom': 15.0,
            'margin_left': 15.0,
            'line_height': 60.0,
            'alignment': 'left',
            'background': 'white',
            'global_scale': 1.0,
            'default_style': 9,
            'default_bias': 0.75,
            'legibility': 0.0,
            'stroke_color': 'black',
            'stroke_width': 2,
            'x_stretch': 1.0,
            'denoise': False,
            'use_chunked': False,
            'is_default': True,
        },
        {
            'name': 'Letter Portrait - Standard',
            'description': 'US Letter portrait with 20mm margins',
            'page_size_id': letter.id,
            'orientation': 'portrait',
            'margin_top': 20.0,
            'margin_right': 20.0,
            'margin_bottom': 20.0,
            'margin_left': 20.0,
            'line_height': 60.0,
            'alignment': 'left',
            'background': 'white',
            'global_scale': 1.0,
            'default_style': 9,
            'default_bias': 0.75,
            'legibility': 0.0,
            'stroke_color': 'black',
            'stroke_width': 2,
            'x_stretch': 1.0,
            'denoise': False,
            'use_chunked': False,
            'is_default': True,
        },
        {
            'name': 'Letter Landscape - Wide',
            'description': 'US Letter landscape with 15mm margins',
            'page_size_id': letter.id,
            'orientation': 'landscape',
            'margin_top': 15.0,
            'margin_right': 15.0,
            'margin_bottom': 15.0,
            'margin_left': 15.0,
            'line_height': 60.0,
            'alignment': 'left',
            'background': 'white',
            'global_scale': 1.0,
            'default_style': 9,
            'default_bias': 0.75,
            'legibility': 0.0,
            'stroke_color': 'black',
            'stroke_width': 2,
            'x_stretch': 1.0,
            'denoise': False,
            'use_chunked': False,
            'is_default': True,
        },
    ]

    added_count = 0
    for template_data in default_templates:
        # Check if already exists
        existing = TemplatePreset.query.filter_by(name=template_data['name']).first()
        if existing:
            print(f"  ⊘ Template '{template_data['name']}' already exists, skipping...")
            continue

        template = TemplatePreset(**template_data)
        db.session.add(template)
        added_count += 1
        print(f"  ✓ Added template: {template_data['name']}")

    db.session.commit()
    print(f"Added {added_count} template presets.\n")
    return added_count


def main():
    """Main migration routine."""
    print("=" * 70)
    print("WriteBot - Add Default Presets Migration")
    print("=" * 70)
    print()

    with app.app_context():
        # Ensure tables exist
        db.create_all()

        # Add default page sizes
        page_count = add_default_page_sizes()

        # Add default templates
        template_count = add_default_templates()

        print("=" * 70)
        print(f"Migration complete! Added {page_count} page sizes and {template_count} templates.")
        print("=" * 70)


if __name__ == '__main__':
    main()
