# Custom Page Size and Template Presets Feature

This document describes the new custom page size and template presets feature added to WriteBot.

## Overview

Administrators can now create custom page size presets and template presets that combine page sizes with layout settings. These presets are then available to all users through the frontend interface and API.

## Features

### 1. Page Size Presets

- Create custom page sizes with specific dimensions (in mm or px)
- System default page sizes (A4, A5, Letter, Legal) are protected and cannot be edited or deleted
- Custom page sizes can be activated/deactivated
- Available through both admin panel and API

### 2. Template Presets

- Combine page size, orientation, margins, line height, and background color
- Templates reference page size presets
- Descriptions and names for easy identification
- Can be activated/deactivated

## Database Models

### PageSizePreset
- `name`: Unique name for the page size
- `width`, `height`: Dimensions
- `unit`: 'mm' or 'px'
- `is_active`: Whether the preset is active
- `is_default`: System defaults (A4, Letter, etc.)
- `created_by`: User who created it (null for system defaults)

### TemplatePreset
- `name`: Unique template name
- `description`: Optional description
- `page_size_preset_id`: Reference to PageSizePreset
- `orientation`: 'portrait' or 'landscape'
- `margin_top`, `margin_right`, `margin_bottom`, `margin_left`: Margin values
- `margin_unit`: 'mm' or 'px'
- `line_height`, `line_height_unit`: Optional line height
- `background_color`: Optional background color
- `is_active`: Whether the template is active
- `created_by`: User who created it

## Admin Interface

### Navigation
New menu items in admin panel:
- **Page Sizes**: `/admin/page-sizes`
- **Templates**: `/admin/templates`

### Page Size Management
- List all page sizes (system defaults shown separately)
- Create new custom page sizes
- Edit custom page sizes (system defaults cannot be edited)
- Delete custom page sizes (only if not used in templates)

### Template Management
- List all templates
- Create new templates
- Edit existing templates
- Delete templates

## API Endpoints

### GET /api/page-sizes
Returns all active page size presets.

**Response:**
```json
{
  "page_sizes": [
    {
      "id": 1,
      "name": "A4",
      "width": 210.0,
      "height": 297.0,
      "unit": "mm",
      "is_active": true,
      "is_default": true,
      "created_at": "2025-01-01T00:00:00"
    }
  ]
}
```

### GET /api/templates
Returns all active template presets.

**Response:**
```json
{
  "templates": [
    {
      "id": 1,
      "name": "Standard A4",
      "description": "A4 with standard margins",
      "page_size_preset_id": 1,
      "page_size_name": "A4",
      "orientation": "portrait",
      "margins": {
        "top": 10.0,
        "right": 10.0,
        "bottom": 10.0,
        "left": 10.0,
        "unit": "mm"
      },
      "line_height": null,
      "line_height_unit": "mm",
      "background_color": "white",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00"
    }
  ]
}
```

### GET /api/templates/{id}
Returns a specific template preset by ID.

## Frontend Integration

### Template Preset Selector
A new dropdown has been added to the "Page Settings" card that allows users to:
1. Select a template preset
2. Automatically populate all page settings (page size, orientation, margins, etc.)
3. Override individual settings after applying a template

### Page Size Selector
The page size dropdown now:
1. Loads page sizes dynamically from the API
2. Shows custom page sizes created by admins
3. Includes system defaults (A4, A5, Letter, Legal)
4. Allows custom size entry

## Database Migration

To set up the database with the new tables and default page sizes:

```bash
python webapp/migrate_presets.py
```

This will:
1. Create the `page_size_presets` and `template_presets` tables
2. Populate default page sizes (A4, A5, Letter, Legal)

## Usage Example

### For Administrators

1. Go to `/admin/page-sizes`
2. Click "Create New Page Size"
3. Enter name, width, height, unit
4. Save

Then create a template:
1. Go to `/admin/templates`
2. Click "Create New Template"
3. Enter name, description
4. Select a page size
5. Set orientation and margins
6. Save

### For Users

1. Open the main application
2. Go to "Page Settings" card
3. Select a template from the "Template Preset" dropdown
4. All settings will be automatically populated
5. Generate handwriting with the preset settings

## Files Modified/Created

### Models
- `webapp/models.py`: Added `PageSizePreset` and `TemplatePreset` models

### Routes
- `webapp/routes/admin_routes.py`: Added routes for managing presets
- `webapp/routes/presets_routes.py`: New file with API endpoints
- `webapp/routes/__init__.py`: Registered presets blueprint

### Templates
- `webapp/templates/admin/base.html`: Added navigation links
- `webapp/templates/admin/page_sizes.html`: List page sizes
- `webapp/templates/admin/page_size_form.html`: Create/edit page size
- `webapp/templates/admin/templates.html`: List templates
- `webapp/templates/admin/template_form.html`: Create/edit template
- `webapp/templates/index.html`: Added template preset selector

### Frontend
- `webapp/static/js/main.js`: Added preset loading and application functions

### Application
- `webapp/app.py`: Registered presets blueprint

### Migration
- `webapp/migrate_presets.py`: Database migration script

## Security Considerations

- Only authenticated users can access the API endpoints
- Only admins can manage presets through the admin panel
- System default page sizes are protected from modification/deletion
- Page sizes in use by templates cannot be deleted

## Future Enhancements

Potential improvements:
- Import/export templates
- Template categories
- User-specific templates
- Template preview functionality
- Batch template application
