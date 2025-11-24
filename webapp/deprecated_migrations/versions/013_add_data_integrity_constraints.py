"""
Migration 013: Add data integrity constraints

Created: 2025-10-29
Description: Adds check constraints for data validation
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Note: SQLite has limited support for adding constraints after table creation
    # We'll create validation views instead that can be checked

    # Create a view for data validation
    db.session.execute(text("""
        CREATE VIEW IF NOT EXISTS data_integrity_checks AS
        SELECT
            'users' as table_name,
            COUNT(*) as total_records,
            SUM(CASE WHEN username IS NULL OR username = '' THEN 1 ELSE 0 END) as invalid_username,
            SUM(CASE WHEN role NOT IN ('user', 'admin') THEN 1 ELSE 0 END) as invalid_role
        FROM users

        UNION ALL

        SELECT
            'page_size_presets' as table_name,
            COUNT(*) as total_records,
            SUM(CASE WHEN width <= 0 OR height <= 0 THEN 1 ELSE 0 END) as invalid_dimensions,
            SUM(CASE WHEN unit NOT IN ('mm', 'cm', 'in', 'px') THEN 1 ELSE 0 END) as invalid_unit
        FROM page_size_presets

        UNION ALL

        SELECT
            'template_presets' as table_name,
            COUNT(*) as total_records,
            SUM(CASE WHEN line_height <= 0 THEN 1 ELSE 0 END) as invalid_line_height,
            SUM(CASE WHEN global_scale <= 0 THEN 1 ELSE 0 END) as invalid_scale
        FROM template_presets
    """))

    db.session.commit()
    print("[OK] Created data integrity validation views")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP VIEW IF EXISTS data_integrity_checks"))
    db.session.commit()
    print("[OK] Dropped data integrity validation views")
