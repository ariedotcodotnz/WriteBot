"""
Migration 009: Seed default page sizes

Created: 2025-10-29
Description: Adds default page size presets (A5, A4, Letter, Legal)
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Check if we already have default page sizes
    result = db.session.execute(text("SELECT COUNT(*) FROM page_size_presets"))
    count = result.scalar()

    if count > 0:
        print("[OK] Page size presets already exist, skipping seed")
        return

    # Insert default page sizes
    default_page_sizes = [
        ('A5', 148.0, 210.0, 'mm', 1, 0),
        ('A4', 210.0, 297.0, 'mm', 1, 1),  # A4 is default
        ('Letter', 215.9, 279.4, 'mm', 1, 0),
        ('Legal', 215.9, 355.6, 'mm', 1, 0),
    ]

    for name, width, height, unit, is_active, is_default in default_page_sizes:
        db.session.execute(text("""
            INSERT INTO page_size_presets (name, width, height, unit, is_active, is_default)
            VALUES (:name, :width, :height, :unit, :is_active, :is_default)
        """), {
            'name': name,
            'width': width,
            'height': height,
            'unit': unit,
            'is_active': is_active,
            'is_default': is_default
        })

    db.session.commit()
    print(f"[OK] Seeded {len(default_page_sizes)} default page sizes")


def downgrade(db):
    """Revert migration changes"""
    # Delete the default page sizes we added
    db.session.execute(text("""
        DELETE FROM page_size_presets
        WHERE name IN ('A5', 'A4', 'Letter', 'Legal')
        AND created_by IS NULL
    """))
    db.session.commit()
    print("[OK] Removed default page sizes")
