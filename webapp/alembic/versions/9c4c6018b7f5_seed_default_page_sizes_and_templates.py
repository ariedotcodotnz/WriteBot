"""Seed default page sizes and templates

Revision ID: 9c4c6018b7f5
Revises: 9f1bcb925634
Create Date: 2025-11-24 15:14:55.665362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '9c4c6018b7f5'
down_revision: Union[str, Sequence[str], None] = '9f1bcb925634'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default page sizes and templates."""
    conn = op.get_bind()

    # Check if we already have page sizes
    result = conn.execute(text("SELECT COUNT(*) FROM page_size_presets"))
    count = result.scalar()

    if count == 0:
        # Insert default page sizes
        page_sizes = [
            {'name': 'A5', 'width': 148.0, 'height': 210.0, 'unit': 'mm', 'is_active': 1, 'is_default': 0},
            {'name': 'A4', 'width': 210.0, 'height': 297.0, 'unit': 'mm', 'is_active': 1, 'is_default': 1},
            {'name': 'Letter', 'width': 215.9, 'height': 279.4, 'unit': 'mm', 'is_active': 1, 'is_default': 0},
            {'name': 'Legal', 'width': 215.9, 'height': 355.6, 'unit': 'mm', 'is_active': 1, 'is_default': 0},
        ]

        for ps in page_sizes:
            conn.execute(text("""
                INSERT INTO page_size_presets (name, width, height, unit, is_active, is_default, created_at, updated_at)
                VALUES (:name, :width, :height, :unit, :is_active, :is_default, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), ps)

        print(f"[OK] Seeded {len(page_sizes)} default page sizes")
    else:
        print("[OK] Page size presets already exist, skipping seed")

    # Check if we already have templates
    result = conn.execute(text("SELECT COUNT(*) FROM template_presets"))
    count = result.scalar()

    if count == 0:
        # Get A4 page size ID
        result = conn.execute(text("SELECT id FROM page_size_presets WHERE name = 'A4' LIMIT 1"))
        a4_id = result.scalar()

        if a4_id:
            # Insert default templates
            templates = [
                {
                    'name': 'Standard Handwriting',
                    'description': 'Default handwriting style with standard spacing',
                    'page_size_preset_id': a4_id,
                    'orientation': 'portrait',
                    'margin_top': 15.0,
                    'margin_right': 15.0,
                    'margin_bottom': 15.0,
                    'margin_left': 15.0,
                    'margin_unit': 'mm',
                    'line_height': 8.0,
                    'line_height_unit': 'mm',
                    'text_alignment': 'left',
                    'global_scale': 1.0,
                    'horizontal_stretch': 1.0,
                    'auto_size': 0,
                    'denoise': 0,
                    'is_active': 1,
                    'use_chunked_generation': 0,
                    'adaptive_chunking': 0,
                },
                {
                    'name': 'Compact Notes',
                    'description': 'Smaller text with tighter spacing for note-taking',
                    'page_size_preset_id': a4_id,
                    'orientation': 'portrait',
                    'margin_top': 10.0,
                    'margin_right': 10.0,
                    'margin_bottom': 10.0,
                    'margin_left': 10.0,
                    'margin_unit': 'mm',
                    'line_height': 6.0,
                    'line_height_unit': 'mm',
                    'text_alignment': 'left',
                    'global_scale': 0.8,
                    'horizontal_stretch': 1.0,
                    'auto_size': 0,
                    'denoise': 0,
                    'is_active': 1,
                    'use_chunked_generation': 0,
                    'adaptive_chunking': 0,
                },
                {
                    'name': 'Large Print',
                    'description': 'Larger, more readable text with generous spacing',
                    'page_size_preset_id': a4_id,
                    'orientation': 'portrait',
                    'margin_top': 20.0,
                    'margin_right': 20.0,
                    'margin_bottom': 20.0,
                    'margin_left': 20.0,
                    'margin_unit': 'mm',
                    'line_height': 10.0,
                    'line_height_unit': 'mm',
                    'text_alignment': 'left',
                    'global_scale': 1.2,
                    'horizontal_stretch': 1.0,
                    'auto_size': 0,
                    'denoise': 0,
                    'is_active': 1,
                    'use_chunked_generation': 0,
                    'adaptive_chunking': 0,
                },
            ]

            # Note: created_by is NULL for system defaults
            for template in templates:
                columns = ', '.join(template.keys()) + ', created_at, updated_at'
                placeholders = ', '.join([f':{key}' for key in template.keys()]) + ', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP'

                conn.execute(
                    text(f"INSERT INTO template_presets ({columns}) VALUES ({placeholders})"),
                    template
                )

            print(f"[OK] Seeded {len(templates)} default templates")
        else:
            print("⚠ Warning: A4 page size not found, skipping template seed")
    else:
        print("[OK] Template presets already exist, skipping seed")


def downgrade() -> None:
    """Remove default page sizes and templates."""
    conn = op.get_bind()

    # Delete the default templates
    conn.execute(text("""
        DELETE FROM template_presets
        WHERE name IN ('Standard Handwriting', 'Compact Notes', 'Large Print')
        AND created_by IS NULL
    """))

    # Delete the default page sizes
    conn.execute(text("""
        DELETE FROM page_size_presets
        WHERE name IN ('A5', 'A4', 'Letter', 'Legal')
        AND created_by IS NULL
    """))

    print("[OK] Removed default page sizes and templates")
