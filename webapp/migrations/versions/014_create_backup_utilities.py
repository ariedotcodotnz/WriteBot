"""
Migration 014: Create backup utilities

Created: 2025-10-29
Description: Creates views and utilities for database backup and export
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Create a view for user summary statistics
    db.session.execute(text("""
        CREATE VIEW IF NOT EXISTS user_summary_stats AS
        SELECT
            u.id,
            u.username,
            u.full_name,
            u.role,
            u.created_at,
            u.last_login,
            COUNT(DISTINCT ua.id) as total_activities,
            COUNT(DISTINCT us.id) as days_active,
            COALESCE(SUM(us.svg_generations), 0) as total_svg_generations,
            COALESCE(SUM(us.batch_generations), 0) as total_batch_generations,
            COALESCE(SUM(us.total_lines_generated), 0) as total_lines,
            COALESCE(SUM(us.total_characters_generated), 0) as total_characters
        FROM users u
        LEFT JOIN user_activities ua ON u.id = ua.user_id
        LEFT JOIN usage_statistics us ON u.id = us.user_id
        GROUP BY u.id
    """))

    # Create a view for system statistics
    db.session.execute(text("""
        CREATE VIEW IF NOT EXISTS system_statistics AS
        SELECT
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM users WHERE is_active = 1) as active_users,
            (SELECT COUNT(*) FROM users WHERE role = 'admin') as admin_users,
            (SELECT COUNT(*) FROM template_presets) as total_templates,
            (SELECT COUNT(*) FROM page_size_presets) as total_page_sizes,
            (SELECT COUNT(*) FROM character_override_collections) as total_char_collections,
            (SELECT COUNT(*) FROM character_overrides) as total_char_overrides,
            (SELECT COALESCE(SUM(svg_generations), 0) FROM usage_statistics) as all_time_svg_generations,
            (SELECT COALESCE(SUM(total_lines_generated), 0) FROM usage_statistics) as all_time_lines_generated
    """))

    # Create a view for recent activity
    db.session.execute(text("""
        CREATE VIEW IF NOT EXISTS recent_activity AS
        SELECT
            ua.id,
            ua.timestamp,
            ua.activity_type,
            ua.description,
            u.username,
            u.full_name
        FROM user_activities ua
        JOIN users u ON ua.user_id = u.id
        ORDER BY ua.timestamp DESC
        LIMIT 100
    """))

    db.session.commit()
    print("✓ Created backup and reporting views")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP VIEW IF EXISTS recent_activity"))
    db.session.execute(text("DROP VIEW IF EXISTS system_statistics"))
    db.session.execute(text("DROP VIEW IF EXISTS user_summary_stats"))
    db.session.commit()
    print("✓ Dropped backup and reporting views")
