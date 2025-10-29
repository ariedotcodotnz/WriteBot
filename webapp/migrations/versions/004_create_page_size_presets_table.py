"""
Migration 004: Create page_size_presets table

Created: 2025-10-29
Description: Creates the page_size_presets table for storing page dimensions
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS page_size_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            width FLOAT NOT NULL,
            height FLOAT NOT NULL,
            unit VARCHAR(10) DEFAULT 'mm' NOT NULL,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            is_default BOOLEAN DEFAULT 0 NOT NULL,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
        )
    """))

    # Create index on name for fast lookups
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_page_size_presets_name
        ON page_size_presets (name)
    """))

    db.session.commit()
    print("✓ Created page_size_presets table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_page_size_presets_name"))
    db.session.execute(text("DROP TABLE IF EXISTS page_size_presets"))
    db.session.commit()
    print("✓ Dropped page_size_presets table and indexes")
