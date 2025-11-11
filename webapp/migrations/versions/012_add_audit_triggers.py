"""
Migration 012: Add audit triggers

Created: 2025-10-29
Description: Adds SQLite triggers to automatically update 'updated_at' timestamps
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    # Tables that need updated_at triggers
    tables_with_updated_at = [
        'page_size_presets',
        'template_presets',
        'character_override_collections',
        'character_overrides',
        'usage_statistics',
    ]

    trigger_count = 0
    for table_name in tables_with_updated_at:
        trigger_name = f"update_{table_name}_timestamp"

        db.session.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            BEGIN
                UPDATE {table_name}
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """))
        trigger_count += 1

    db.session.commit()
    print(f"[OK] Created {trigger_count} audit triggers for automatic timestamp updates")


def downgrade(db):
    """Revert migration changes"""

    tables_with_updated_at = [
        'page_size_presets',
        'template_presets',
        'character_override_collections',
        'character_overrides',
        'usage_statistics',
    ]

    for table_name in tables_with_updated_at:
        trigger_name = f"update_{table_name}_timestamp"
        db.session.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))

    db.session.commit()
    print(f"[OK] Dropped audit triggers")
