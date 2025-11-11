"""
Migration 002: Create user_activities table

Created: 2025-10-29
Description: Creates the user_activities table for tracking user actions and audit trail
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS user_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type VARCHAR(50) NOT NULL,
            description TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            extra_data TEXT,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """))

    # Create indexes for performance
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_user_activities_user_id
        ON user_activities (user_id)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp
        ON user_activities (timestamp)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_user_activities_type
        ON user_activities (activity_type)
    """))

    db.session.commit()
    print("[OK] Created user_activities table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_user_activities_type"))
    db.session.execute(text("DROP INDEX IF EXISTS idx_user_activities_timestamp"))
    db.session.execute(text("DROP INDEX IF EXISTS idx_user_activities_user_id"))
    db.session.execute(text("DROP TABLE IF EXISTS user_activities"))
    db.session.commit()
    print("[OK] Dropped user_activities table and indexes")
