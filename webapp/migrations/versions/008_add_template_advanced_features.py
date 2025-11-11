"""
Migration 008: Add template advanced features

Created: 2025-10-29
Description: Adds advanced generation features to template_presets table
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Check if columns already exist (for SQLite compatibility)
    result = db.session.execute(text("PRAGMA table_info(template_presets)"))
    existing_columns = {row[1] for row in result}

    columns_to_add = [
        ('use_chunked_generation', 'BOOLEAN DEFAULT 0'),
        ('adaptive_chunking', 'BOOLEAN DEFAULT 0'),
        ('adaptive_strategy', 'VARCHAR(50) DEFAULT "balanced"'),
        ('words_per_chunk', 'INTEGER DEFAULT 5'),
        ('chunk_spacing', 'FLOAT DEFAULT 0.0'),
        ('max_line_width', 'FLOAT'),
    ]

    added_count = 0
    for column_name, column_def in columns_to_add:
        if column_name not in existing_columns:
            db.session.execute(text(f"""
                ALTER TABLE template_presets
                ADD COLUMN {column_name} {column_def}
            """))
            added_count += 1

    db.session.commit()

    if added_count > 0:
        print(f"[OK] Added {added_count} advanced feature columns to template_presets table")
    else:
        print("[OK] All advanced feature columns already exist")


def downgrade(db):
    """Revert migration changes"""
    # SQLite doesn't support DROP COLUMN easily, so we'd need to recreate the table
    # For now, we'll just document this limitation
    print("⚠ Warning: SQLite doesn't support DROP COLUMN. Manual intervention required.")
    print("  To rollback, you would need to:")
    print("  1. Create a new table without these columns")
    print("  2. Copy data from old table to new table")
    print("  3. Drop old table and rename new table")
