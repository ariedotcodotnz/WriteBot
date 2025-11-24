"""
Migration 010: Seed default templates

Created: 2025-10-29
Description: Adds default template presets for common use cases
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Check if we already have templates
    result = db.session.execute(text("SELECT COUNT(*) FROM template_presets"))
    count = result.scalar()

    if count > 0:
        print("[OK] Template presets already exist, skipping seed")
        return

    # Get A4 page size ID
    result = db.session.execute(text("SELECT id FROM page_size_presets WHERE name = 'A4' LIMIT 1"))
    a4_id = result.scalar()

    if not a4_id:
        print("⚠ Warning: A4 page size not found, skipping template seed")
        return

    # Insert default templates
    default_templates = [
        {
            'name': 'Standard Handwriting',
            'description': 'Default handwriting style with standard spacing',
            'page_size_preset_id': a4_id,
            'orientation': 'portrait',
            'margin_top': 15.0,
            'margin_right': 15.0,
            'margin_bottom': 15.0,
            'margin_left': 15.0,
            'line_height': 8.0,
            'text_alignment': 'left',
            'global_scale': 1.0,
            'horizontal_stretch': 1.0,
        },
        {
            'name': 'Compact Notes',
            'description': 'Smaller text with tighter spacing for note-taking',
            'page_size_preset_id': a4_id,
            'orientation': 'portrait',
            'margin_top': 10.0,
            'margin_right': 10.0,
            'margin_bottom': 10.0,
            'margin_left': 10.0,
            'line_height': 6.0,
            'text_alignment': 'left',
            'global_scale': 0.8,
            'horizontal_stretch': 1.0,
        },
        {
            'name': 'Large Print',
            'description': 'Larger, more readable text with generous spacing',
            'page_size_preset_id': a4_id,
            'orientation': 'portrait',
            'margin_top': 20.0,
            'margin_right': 20.0,
            'margin_bottom': 20.0,
            'margin_left': 20.0,
            'line_height': 10.0,
            'text_alignment': 'left',
            'global_scale': 1.2,
            'horizontal_stretch': 1.0,
        },
    ]

    for template in default_templates:
        columns = ', '.join(template.keys())
        placeholders = ', '.join([f':{key}' for key in template.keys()])

        db.session.execute(
            text(f"INSERT INTO template_presets ({columns}) VALUES ({placeholders})"),
            template
        )

    db.session.commit()
    print(f"[OK] Seeded {len(default_templates)} default templates")


def downgrade(db):
    """Revert migration changes"""
    # Delete the default templates we added
    db.session.execute(text("""
        DELETE FROM template_presets
        WHERE name IN ('Standard Handwriting', 'Compact Notes', 'Large Print')
        AND created_by IS NULL
    """))
    db.session.commit()
    print("[OK] Removed default templates")
