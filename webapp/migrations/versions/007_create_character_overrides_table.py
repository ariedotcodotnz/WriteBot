"""
Migration 007: Create character_overrides table

Created: 2025-10-29
Description: Creates the character_overrides table for storing custom SVG data for individual characters
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS character_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL,
            character VARCHAR(10) NOT NULL,
            svg_data TEXT NOT NULL,
            viewbox_x FLOAT DEFAULT 0.0,
            viewbox_y FLOAT DEFAULT 0.0,
            viewbox_width FLOAT DEFAULT 100.0,
            viewbox_height FLOAT DEFAULT 100.0,
            baseline_offset FLOAT DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (collection_id) REFERENCES character_override_collections (id) ON DELETE CASCADE,
            UNIQUE (collection_id, character)
        )
    """))

    # Create compound index on collection_id and character for fast lookups
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_char_overrides_collection_char
        ON character_overrides (collection_id, character)
    """))

    # Create index on collection_id for listing all characters in a collection
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_char_overrides_collection_id
        ON character_overrides (collection_id)
    """))

    db.session.commit()
    print("[OK] Created character_overrides table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_char_overrides_collection_id"))
    db.session.execute(text("DROP INDEX IF EXISTS idx_char_overrides_collection_char"))
    db.session.execute(text("DROP TABLE IF EXISTS character_overrides"))
    db.session.commit()
    print("[OK] Dropped character_overrides table and indexes")
