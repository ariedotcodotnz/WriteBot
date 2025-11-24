"""
Migration 011: Add performance indexes

Created: 2025-10-29
Description: Adds additional indexes for improved query performance
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""

    indexes_to_add = [
        # Users table indexes
        ("idx_users_role", "users", "role"),
        ("idx_users_is_active", "users", "is_active"),
        ("idx_users_created_at", "users", "created_at"),

        # Template presets indexes
        ("idx_template_presets_active", "template_presets", "is_active"),
        ("idx_template_presets_created_by", "template_presets", "created_by"),

        # Page size presets indexes
        ("idx_page_size_presets_active", "page_size_presets", "is_active"),
        ("idx_page_size_presets_default", "page_size_presets", "is_default"),

        # Character override collections indexes
        ("idx_char_collections_active", "character_override_collections", "is_active"),
        ("idx_char_collections_created_by", "character_override_collections", "created_by"),
    ]

    added_count = 0
    for index_name, table_name, column_name in indexes_to_add:
        try:
            db.session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table_name} ({column_name})
            """))
            added_count += 1
        except Exception as e:
            print(f"⚠ Warning: Could not create index {index_name}: {str(e)}")

    db.session.commit()
    print(f"[OK] Added {added_count} performance indexes")


def downgrade(db):
    """Revert migration changes"""

    indexes_to_drop = [
        "idx_users_role",
        "idx_users_is_active",
        "idx_users_created_at",
        "idx_template_presets_active",
        "idx_template_presets_created_by",
        "idx_page_size_presets_active",
        "idx_page_size_presets_default",
        "idx_char_collections_active",
        "idx_char_collections_created_by",
    ]

    for index_name in indexes_to_drop:
        db.session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))

    db.session.commit()
    print(f"[OK] Dropped {len(indexes_to_drop)} performance indexes")
