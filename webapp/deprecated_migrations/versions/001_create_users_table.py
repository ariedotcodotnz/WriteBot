"""
Migration 001: Create users table

Created: 2025-10-29
Description: Creates the main users table with authentication and profile fields
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(120),
            role VARCHAR(20) DEFAULT 'user' NOT NULL,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,

            -- User preferences/settings
            default_style INTEGER DEFAULT 0,
            default_bias FLOAT DEFAULT 0.0,
            default_stroke_color VARCHAR(20) DEFAULT '#000000',
            default_stroke_width FLOAT DEFAULT 1.0
        )
    """))
    db.session.commit()
    print("[OK] Created users table")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP TABLE IF EXISTS users"))
    db.session.commit()
    print("[OK] Dropped users table")
