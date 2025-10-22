# WriteBot Web Application Structure

## Directory Organization

This Flask application follows best practices for template and static file organization:

```
webapp/
├── app.py                          # Main Flask application entry point
├── routes/                         # Blueprint routes (modular endpoints)
│   ├── __init__.py
│   ├── generation_routes.py       # Handwriting generation endpoints
│   ├── batch_routes.py             # Batch processing endpoints
│   └── style_routes.py             # Style management endpoints
├── templates/                      # Jinja2 templates (Flask templating)
│   ├── base.html                   # Base template with common structure
│   ├── index.html                  # Main page (extends base.html)
│   └── components/                 # Reusable template components
│       ├── header.html             # Site header
│       └── footer.html             # Site footer
├── static/                         # Static assets
│   ├── css/
│   │   └── main.css                # Application styles
│   ├── js/
│   │   └── main.js                 # Application JavaScript
│   └── index.html.bak              # Backup of original monolithic file
└── utils/                          # Utility modules
    ├── page_utils.py               # Page layout utilities
    └── text_utils.py               # Text processing utilities
```

## Template System

### Base Template (`base.html`)
The base template provides the core HTML structure including:
- HTML head with meta tags and CSS links
- Header inclusion via component
- Main content block (overridden by child templates)
- Footer inclusion via component
- Common JavaScript libraries and scripts
- Lightbox, loading overlay, and notification containers

**Jinja2 Blocks:**
- `{% block title %}` - Page title (defaults to "WriteBot - Handwriting Synthesis")
- `{% block extra_css %}` - Additional CSS for specific pages
- `{% block content %}` - Main page content (required)
- `{% block extra_js %}` - Additional JavaScript for specific pages

### Components
Reusable template fragments included in base template:
- `header.html` - Application header with branding
- `footer.html` - Application footer with credits

### Page Templates
- `index.html` - Main application page (extends base, implements content block)

## Static Assets

### CSS (`static/css/main.css`)
Organized sections:
1. CSS Variables (Carbon Design System theme)
2. Base styles and resets
3. Layout components (header, content, footer)
4. UI components (cards, forms, buttons)
5. Preview and code display
6. Batch processing UI
7. Modals and overlays
8. Responsive design
9. Utility classes

### JavaScript (`static/js/main.js`)
Modular functions organized by responsibility:
1. State management (SVG data, styles, CSV files)
2. UI functions (lightbox, notifications, loading states)
3. API communication (generation, batch processing)
4. Style management (loading and selecting styles)
5. File handling (CSV drag-and-drop)
6. Event listeners and initialization

## Best Practices Implemented

### 1. Separation of Concerns
- **Templates**: HTML structure and presentation
- **Static CSS**: Styling and visual design
- **Static JS**: Client-side behavior and interactivity
- **Routes**: Server-side logic and API endpoints

### 2. DRY (Don't Repeat Yourself)
- Base template eliminates duplicate HTML (head, header, footer)
- Components allow reuse across multiple pages
- CSS organized with variables and utility classes

### 3. Maintainability
- Clear directory structure
- Components are small and focused
- External CSS/JS files enable caching
- Jinja2 inheritance provides flexibility

### 4. Performance
- Static assets can be cached by browsers
- External files enable CDN deployment
- Minification-ready structure

### 5. Scalability
- Easy to add new pages (extend base.html)
- New components can be created in components/
- Blueprint architecture for routes

## Adding New Pages

To create a new page:

1. Create template in `templates/`:
```html
{% extends "base.html" %}

{% block title %}My New Page - WriteBot{% endblock %}

{% block content %}
  <div class="bx--grid">
    <!-- Your content here -->
  </div>
{% endblock %}
```

2. Add route in appropriate blueprint or `app.py`:
```python
@app.route("/new-page")
def new_page():
    return render_template('new_page.html')
```

## Adding New Components

1. Create file in `templates/components/`:
```html
<!-- components/my_component.html -->
<div class="my-component">
  {{ content }}
</div>
```

2. Include in templates:
```html
{% include 'components/my_component.html' %}
```

## Development Guidelines

1. **Templates**: Use Jinja2 syntax for dynamic content and inheritance
2. **CSS**: Add new styles to `main.css`, organized by section
3. **JavaScript**: Add new functions to `main.js`, with clear comments
4. **Routes**: Keep routes modular in blueprint files
5. **Testing**: Test template rendering and static asset loading

## Migration Notes

The application was refactored from a monolithic `index.html` to this modular structure:
- Original file backed up as `static/index.html.bak`
- All inline styles moved to `static/css/main.css`
- All inline scripts moved to `static/js/main.js`
- HTML split into base template, components, and page template
- Flask route updated to use `render_template()`

This structure maintains all functionality while improving maintainability and following Flask best practices.
