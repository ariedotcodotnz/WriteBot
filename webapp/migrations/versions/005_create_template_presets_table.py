"""
Migration 005: Create template_presets table

Created: 2025-10-29
Description: Creates the template_presets table for storing template configurations
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS template_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,

            -- Page and layout settings
            page_size_preset_id INTEGER,
            orientation VARCHAR(20) DEFAULT 'portrait',
            margin_top FLOAT DEFAULT 10.0,
            margin_right FLOAT DEFAULT 10.0,
            margin_bottom FLOAT DEFAULT 10.0,
            margin_left FLOAT DEFAULT 10.0,

            -- Line settings
            line_height FLOAT DEFAULT 7.0,
            line_height_unit VARCHAR(10) DEFAULT 'mm',
            empty_line_spacing FLOAT DEFAULT 0.0,

            -- Text formatting
            text_alignment VARCHAR(20) DEFAULT 'left',
            global_scale FLOAT DEFAULT 1.0,
            auto_size BOOLEAN DEFAULT 0,
            manual_size_scale FLOAT DEFAULT 1.0,
            background_color VARCHAR(20) DEFAULT '#ffffff',

            -- Style control
            biases TEXT,
            per_line_styles TEXT,
            stroke_colors TEXT,
            stroke_widths TEXT,
            horizontal_stretch FLOAT DEFAULT 1.0,
            denoise FLOAT DEFAULT 0.0,

            -- Text wrapping
            character_width FLOAT DEFAULT 5.0,
            wrap_ratio FLOAT DEFAULT 0.0,
            wrap_utilization FLOAT DEFAULT 0.9,

            -- Metadata
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (page_size_preset_id) REFERENCES page_size_presets (id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
        )
    """))

    # Create index on name for fast lookups
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_template_presets_name
        ON template_presets (name)
    """))

    db.session.commit()
    print("[OK] Created template_presets table with indexes")


def downgrade(db):
    """Revert migration changes"""
    db.session.execute(text("DROP INDEX IF EXISTS idx_template_presets_name"))
    db.session.execute(text("DROP TABLE IF EXISTS template_presets"))
    db.session.commit()
    print("[OK] Dropped template_presets table and indexes")
