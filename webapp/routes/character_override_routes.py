"""
Admin routes for managing character override collections.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from webapp.models import db, CharacterOverrideCollection, CharacterOverride
from webapp.utils.auth_utils import admin_required, log_activity
from datetime import datetime
from sqlalchemy import func, desc
import xml.etree.ElementTree as ET
import re
import random

character_override_bp = Blueprint('character_overrides', __name__, url_prefix='/admin/character-overrides')


def parse_svg_viewbox(svg_content):
    """
    Parse SVG content and extract viewBox dimensions.
    Returns tuple: (viewbox_x, viewbox_y, viewbox_width, viewbox_height)
    """
    try:
        # Parse SVG
        root = ET.fromstring(svg_content)

        # Get viewBox attribute
        viewbox = root.get('viewBox')
        if viewbox:
            parts = viewbox.strip().split()
            if len(parts) == 4:
                return tuple(float(x) for x in parts)

        # Fallback to width and height attributes
        width = root.get('width')
        height = root.get('height')
        if width and height:
            # Remove units if present
            width = re.sub(r'[a-zA-Z]+$', '', width)
            height = re.sub(r'[a-zA-Z]+$', '', height)
            return (0.0, 0.0, float(width), float(height))

        return None
    except Exception as e:
        print(f"Error parsing SVG: {e}")
        return None


def validate_svg(svg_content):
    """
    Validate SVG content and check if it meets requirements.
    Returns (is_valid, error_message, viewbox_data)
    """
    try:
        # Try to parse as XML
        root = ET.fromstring(svg_content)

        # Check if root element is svg
        if not root.tag.endswith('svg'):
            return False, "Invalid SVG: Root element must be <svg>", None

        # Get viewbox dimensions
        viewbox_data = parse_svg_viewbox(svg_content)
        if not viewbox_data:
            return False, "SVG must have a viewBox or width/height attributes", None

        return True, None, viewbox_data
    except ET.ParseError as e:
        return False, f"Invalid XML: {str(e)}", None
    except Exception as e:
        return False, f"Error validating SVG: {str(e)}", None


@character_override_bp.route('/')
@login_required
@admin_required
def list_collections():
    """List all character override collections."""
    collections = CharacterOverrideCollection.query.order_by(desc(CharacterOverrideCollection.created_at)).all()

    # Get character counts for each collection
    collection_stats = []
    for collection in collections:
        char_count = collection.get_character_count()
        unique_chars = len(collection.get_unique_characters())
        collection_stats.append({
            'collection': collection,
            'total_variants': char_count,
            'unique_characters': unique_chars
        })

    log_activity('admin_action', 'Viewed character override collections')
    return render_template('admin/character_overrides/list.html', collection_stats=collection_stats)


@character_override_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_collection():
    """Create a new character override collection."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Collection name is required.', 'error')
            return render_template('admin/character_overrides/collection_form.html', collection=None, action='create')

        if CharacterOverrideCollection.query.filter_by(name=name).first():
            flash(f'Collection "{name}" already exists.', 'error')
            return render_template('admin/character_overrides/collection_form.html', collection=None, action='create')

        # Create collection
        new_collection = CharacterOverrideCollection(
            name=name,
            description=description,
            created_by=current_user.id,
            is_active=is_active
        )

        db.session.add(new_collection)
        db.session.commit()

        log_activity('admin_action', f'Created character override collection: {name}')
        flash(f'Collection "{name}" created successfully.', 'success')
        return redirect(url_for('character_overrides.view_collection', collection_id=new_collection.id))

    return render_template('admin/character_overrides/collection_form.html', collection=None, action='create')


@character_override_bp.route('/<int:collection_id>')
@login_required
@admin_required
def view_collection(collection_id):
    """View collection details and manage character overrides."""
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    # Get all character overrides grouped by character
    overrides = CharacterOverride.query.filter_by(collection_id=collection_id).order_by(CharacterOverride.character).all()

    # Group by character
    grouped_overrides = {}
    for override in overrides:
        if override.character not in grouped_overrides:
            grouped_overrides[override.character] = []
        grouped_overrides[override.character].append(override)

    log_activity('admin_action', f'Viewed character override collection: {collection.name} (ID: {collection_id})')

    return render_template('admin/character_overrides/view.html',
                           collection=collection,
                           grouped_overrides=grouped_overrides)


@character_override_bp.route('/<int:collection_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_collection(collection_id):
    """Edit an existing collection."""
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Collection name is required.', 'error')
            return render_template('admin/character_overrides/collection_form.html', collection=collection, action='edit')

        # Check if name is taken by another collection
        existing_collection = CharacterOverrideCollection.query.filter_by(name=name).first()
        if existing_collection and existing_collection.id != collection_id:
            flash(f'Collection "{name}" already exists.', 'error')
            return render_template('admin/character_overrides/collection_form.html', collection=collection, action='edit')

        # Update collection
        collection.name = name
        collection.description = description
        collection.is_active = is_active
        collection.updated_at = datetime.utcnow()

        db.session.commit()

        log_activity('admin_action', f'Updated character override collection: {name} (ID: {collection_id})')
        flash(f'Collection "{name}" updated successfully.', 'success')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    return render_template('admin/character_overrides/collection_form.html', collection=collection, action='edit')


@character_override_bp.route('/<int:collection_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_collection(collection_id):
    """Delete a collection and all its character overrides."""
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    name = collection.name
    db.session.delete(collection)
    db.session.commit()

    log_activity('admin_action', f'Deleted character override collection: {name} (ID: {collection_id})')
    flash(f'Collection "{name}" deleted successfully.', 'success')
    return redirect(url_for('character_overrides.list_collections'))


@character_override_bp.route('/<int:collection_id>/upload', methods=['POST'])
@login_required
@admin_required
def upload_character(collection_id):
    """Upload a character SVG to the collection."""
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    character = request.form.get('character', '').strip()
    baseline_offset = request.form.get('baseline_offset', 0.0, type=float)

    # Validation
    if not character or len(character) != 1:
        flash('You must specify exactly one character.', 'error')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    # Check if file was uploaded
    if 'svg_file' not in request.files:
        flash('No SVG file uploaded.', 'error')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    svg_file = request.files['svg_file']

    if svg_file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    # Read SVG content
    svg_content = svg_file.read().decode('utf-8')

    # Validate SVG
    is_valid, error_message, viewbox_data = validate_svg(svg_content)
    if not is_valid:
        flash(f'Invalid SVG: {error_message}', 'error')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    # Create character override
    new_override = CharacterOverride(
        collection_id=collection_id,
        character=character,
        svg_data=svg_content,
        viewbox_x=viewbox_data[0],
        viewbox_y=viewbox_data[1],
        viewbox_width=viewbox_data[2],
        viewbox_height=viewbox_data[3],
        baseline_offset=baseline_offset
    )

    db.session.add(new_override)
    collection.updated_at = datetime.utcnow()
    db.session.commit()

    log_activity('admin_action', f'Uploaded character "{character}" to collection: {collection.name}')
    flash(f'Character "{character}" variant uploaded successfully.', 'success')
    return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))


@character_override_bp.route('/<int:collection_id>/upload-batch', methods=['POST'])
@login_required
@admin_required
def upload_batch(collection_id):
    """Upload multiple character SVGs at once."""
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    # Check if files were uploaded
    if 'svg_files' not in request.files:
        flash('No SVG files uploaded.', 'error')
        return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))

    files = request.files.getlist('svg_files')
    baseline_offset = request.form.get('baseline_offset', 0.0, type=float)

    success_count = 0
    error_count = 0
    errors = []

    for svg_file in files:
        if svg_file.filename == '':
            continue

        # Extract character from filename (first character of filename)
        # Expected format: a.svg, a_1.svg, etc.
        filename = svg_file.filename
        if not filename.endswith('.svg'):
            errors.append(f'{filename}: Not an SVG file')
            error_count += 1
            continue

        # Get character from filename
        character = filename[0]

        # Read SVG content
        try:
            svg_content = svg_file.read().decode('utf-8')
        except Exception as e:
            errors.append(f'{filename}: Could not read file - {str(e)}')
            error_count += 1
            continue

        # Validate SVG
        is_valid, error_message, viewbox_data = validate_svg(svg_content)
        if not is_valid:
            errors.append(f'{filename}: {error_message}')
            error_count += 1
            continue

        # Create character override
        new_override = CharacterOverride(
            collection_id=collection_id,
            character=character,
            svg_data=svg_content,
            viewbox_x=viewbox_data[0],
            viewbox_y=viewbox_data[1],
            viewbox_width=viewbox_data[2],
            viewbox_height=viewbox_data[3],
            baseline_offset=baseline_offset
        )

        db.session.add(new_override)
        success_count += 1

    collection.updated_at = datetime.utcnow()
    db.session.commit()

    # Show results
    if success_count > 0:
        flash(f'Successfully uploaded {success_count} character variant(s).', 'success')
        log_activity('admin_action', f'Batch uploaded {success_count} characters to collection: {collection.name}')

    if error_count > 0:
        flash(f'{error_count} file(s) failed to upload. Errors: {"; ".join(errors[:5])}', 'error')

    return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))


@character_override_bp.route('/<int:collection_id>/draw', methods=['POST'])
@login_required
@admin_required
def save_drawn_character(collection_id):
    """
    Save a character drawn in the browser's canvas interface.
    This endpoint receives SVG data generated from canvas strokes.
    """
    collection = CharacterOverrideCollection.query.get_or_404(collection_id)

    try:
        character = request.form.get('character', '').strip()
        baseline_offset = request.form.get('baseline_offset', 0.0, type=float)

        # Validation
        if not character or len(character) != 1:
            return jsonify({'error': 'You must specify exactly one character.'}), 400

        # Check if SVG data was provided
        if 'svg_data' not in request.files:
            return jsonify({'error': 'No SVG data provided.'}), 400

        svg_file = request.files['svg_data']
        svg_content = svg_file.read().decode('utf-8')

        # Validate SVG
        is_valid, error_message, viewbox_data = validate_svg(svg_content)
        if not is_valid:
            return jsonify({'error': f'Invalid SVG: {error_message}'}), 400

        # Validate that it's stroke-based (pen plotter compatible)
        # This is a warning, not an error - we still allow it
        try:
            root = ET.fromstring(svg_content)
            has_strokes = False
            has_fills = False

            for elem in root.iter():
                if elem.tag.endswith('path'):
                    stroke = elem.get('stroke')
                    fill = elem.get('fill')

                    if stroke and stroke.lower() not in ('none', 'transparent'):
                        has_strokes = True
                    if not fill or fill.lower() not in ('none', 'transparent'):
                        has_fills = True

            # If it has fills but no strokes, warn (but still save)
            if has_fills and not has_strokes:
                print(f"Warning: Character '{character}' uses fills instead of strokes - may not be pen plotter compatible")

        except Exception as e:
            print(f"Warning: Could not validate stroke vs fill: {e}")

        # Create character override
        new_override = CharacterOverride(
            collection_id=collection_id,
            character=character,
            svg_data=svg_content,
            viewbox_x=viewbox_data[0],
            viewbox_y=viewbox_data[1],
            viewbox_width=viewbox_data[2],
            viewbox_height=viewbox_data[3],
            baseline_offset=baseline_offset
        )

        db.session.add(new_override)
        collection.updated_at = datetime.utcnow()
        db.session.commit()

        log_activity('admin_action', f'Drew and saved character "{character}" to collection: {collection.name}')
        return jsonify({'success': True, 'message': f'Character "{character}" saved successfully.'}), 200

    except Exception as e:
        print(f"Error saving drawn character: {e}")
        return jsonify({'error': str(e)}), 500


@character_override_bp.route('/character/<int:override_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_character(override_id):
    """Delete a character override variant."""
    override = CharacterOverride.query.get_or_404(override_id)
    collection_id = override.collection_id
    character = override.character

    db.session.delete(override)
    db.session.commit()

    log_activity('admin_action', f'Deleted character "{character}" variant (ID: {override_id})')
    flash(f'Character "{character}" variant deleted successfully.', 'success')
    return redirect(url_for('character_overrides.view_collection', collection_id=collection_id))


@character_override_bp.route('/character/<int:override_id>/preview')
@login_required
@admin_required
def preview_character(override_id):
    """Preview a character override SVG."""
    override = CharacterOverride.query.get_or_404(override_id)
    return override.svg_data, 200, {'Content-Type': 'image/svg+xml'}


# Public API endpoint (not under admin prefix)
# This will be registered separately in app.py


def get_character_override(collection_id, character):
    """
    Get a random character override from the collection for the given character.
    Returns CharacterOverride object or None if not found.
    """
    overrides = CharacterOverride.query.filter_by(
        collection_id=collection_id,
        character=character
    ).all()

    if overrides:
        return random.choice(overrides)
    return None
