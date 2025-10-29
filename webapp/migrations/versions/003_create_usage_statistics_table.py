"""
Migration 003: Create usage_statistics table

Created: 2025-10-29
Description: Creates the usage_statistics table for tracking daily user metrics
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS usage_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            svg_generations INTEGER DEFAULT 0,
            batch_generations INTEGER DEFAULT 0,
            total_lines_generated INTEGER DEFAULT 0,
            total_characters_generated INTEGER DEFAULT 0,
            total_processing_time FLOAT DEFAULT 0.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, date)
        )
    """))

    # Create indexes for performance
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_usage_statistics_user_id
        ON usage_statistics (user_id)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_usage_statistics_date
        ON usage_statistics (date)
    """))

    db.session.commit()
    print("✓ Created usage_statistics table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_usage_statistics_date"))
    db.session.execute(text("DROP INDEX IF EXISTS idx_usage_statistics_user_id"))
    db.session.execute(text("DROP TABLE IF EXISTS usage_statistics"))
    db.session.commit()
    print("✓ Dropped usage_statistics table and indexes")
