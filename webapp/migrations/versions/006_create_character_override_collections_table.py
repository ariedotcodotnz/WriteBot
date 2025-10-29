"""
Migration 006: Create character_override_collections table

Created: 2025-10-29
Description: Creates the character_override_collections table for grouping custom character SVGs
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS character_override_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1 NOT NULL,

            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
        )
    """))

    # Create index on name for fast lookups
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_char_override_collections_name
        ON character_override_collections (name)
    """))

    db.session.commit()
    print("✓ Created character_override_collections table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_char_override_collections_name"))
    db.session.execute(text("DROP TABLE IF EXISTS character_override_collections"))
    db.session.commit()
    print("✓ Dropped character_override_collections table and indexes")
