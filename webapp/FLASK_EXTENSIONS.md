# Flask Extensions Guide

This document explains how to use the Flask extensions integrated into WriteBot.

## Overview

The following Flask extensions have been integrated:

1. **Flask-Caching** - For caching expensive operations
2. **Flask-Limiter** - For rate limiting API endpoints
3. **Flask-Minify** - For minifying HTML, CSS, and JavaScript
4. **Flask-Assets** - For bundling and minifying static assets
5. **Flask-Compress** - For gzip compression of responses

## Flask-Caching

Flask-Caching provides caching support for expensive operations.

### Configuration

In `webapp/app.py`:
```python
app.config['CACHE_TYPE'] = 'SimpleCache'  # Use simple in-memory cache
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Default timeout: 5 minutes
```

For production, consider using Redis or Memcached:
```python
# Redis
app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'

# Memcached
app.config['CACHE_TYPE'] = 'memcached'
app.config['CACHE_MEMCACHED_SERVERS'] = ['localhost:11211']
```

### Usage

Import the cache from extensions:
```python
from webapp.extensions import cache
```

#### Decorator-based caching:
```python
@app.route('/api/expensive-operation')
@cache.cached(timeout=300, key_prefix='expensive_op')
def expensive_operation():
    # Your expensive operation here
    return result
```

#### Manual caching:
```python
def get_data():
    data = cache.get('my_key')
    if data is None:
        data = expensive_computation()
        cache.set('my_key', data, timeout=300)
    return data
```

#### Cache with dynamic keys:
```python
@cache.memoize(timeout=300)
def get_user_data(user_id):
    # Cache key will include user_id automatically
    return User.query.get(user_id)
```

#### Clear cache:
```python
cache.clear()  # Clear all cache
cache.delete('my_key')  # Delete specific key
cache.delete_memoized(get_user_data, user_id=123)  # Clear memoized function
```

## Flask-Limiter

Flask-Limiter provides rate limiting for API endpoints to prevent abuse.

### Configuration

In `webapp/app.py`:
```python
app.config['RATELIMIT_STORAGE_URL'] = 'memory://'  # Use in-memory storage
app.config['RATELIMIT_HEADERS_ENABLED'] = True  # Enable rate limit headers
```

For production, consider using Redis:
```python
app.config['RATELIMIT_STORAGE_URL'] = 'redis://localhost:6379/1'
```

Global default limits are set to:
- 200 requests per day
- 50 requests per hour

### Usage

Import the limiter from extensions:
```python
from webapp.extensions import limiter
```

#### Apply rate limit to specific endpoints:
```python
from webapp.routes.generation_routes import apply_rate_limit

@app.route('/api/generate')
@login_required
@apply_rate_limit("10 per minute")
def generate():
    # Your endpoint logic
    return result
```

#### Different rate limit strategies:
```python
# Multiple limits
@apply_rate_limit("100 per day;10 per hour;1 per minute")

# Exempt from rate limiting
@limiter.exempt
def admin_endpoint():
    pass

# Dynamic limits based on user
@limiter.limit(lambda: "10/minute" if current_user.is_premium else "5/minute")
def api_call():
    pass
```

#### Rate limit by custom key:
```python
from flask import request

@limiter.limit("5 per minute", key_func=lambda: request.headers.get('X-API-Key'))
def api_endpoint():
    pass
```

## Flask-Minify

Flask-Minify automatically minifies HTML, CSS, and JavaScript responses.

### Configuration

Configured in `webapp/app.py` with:
- HTML minification: Enabled
- JavaScript minification: Enabled
- CSS/LESS minification: Enabled

### Usage

Minification is automatic for all responses. No additional code needed.

To disable minification for specific endpoints:
```python
from flask_minify import decorators

@app.route('/api/raw')
@decorators.bypass_minification
def raw_endpoint():
    return html_content
```

## Flask-Assets

Flask-Assets helps bundle and minify static assets (CSS and JavaScript files).

### Configuration

In `webapp/app.py`, bundles are configured:
```python
css_bundle = Bundle(
    'css/*.css',
    filters='cssmin',
    output='gen/packed.css'
)

js_bundle = Bundle(
    'js/*.js',
    filters='jsmin',
    output='gen/packed.js'
)
```

### Usage in Templates

In your Jinja2 templates:
```html
{% assets "css_all" %}
    <link rel="stylesheet" href="{{ ASSET_URL }}" />
{% endassets %}

{% assets "js_all" %}
    <script src="{{ ASSET_URL }}"></script>
{% endassets %}
```

### Creating Custom Bundles

In your route or initialization code:
```python
from webapp.extensions import assets
from flask_assets import Bundle

# Create custom bundle
custom_js = Bundle(
    'js/library.js',
    'js/custom.js',
    filters='jsmin',
    output='gen/custom.js'
)
assets.register('custom_js', custom_js)
```

### Rebuilding Assets

To force rebuild of assets:
```python
from webapp.extensions import assets
assets.cache = False  # Disable cache
assets.manifest = None  # Clear manifest
```

## Flask-Compress

Flask-Compress automatically compresses responses using gzip.

### Configuration

Enabled automatically in `webapp/app.py`. No additional configuration needed.

### Usage

Compression is automatic for all responses larger than 500 bytes.

To customize compression settings:
```python
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 'text/css', 'text/xml',
    'application/json', 'application/javascript'
]
app.config['COMPRESS_LEVEL'] = 6  # Compression level (1-9)
app.config['COMPRESS_MIN_SIZE'] = 500  # Minimum size to compress
```

## Best Practices

1. **Caching**: Cache expensive database queries and computation results, but be careful with user-specific data
2. **Rate Limiting**: Apply stricter limits to expensive endpoints, looser limits to lightweight endpoints
3. **Minification**: Ensure minification doesn't break your JavaScript (test thoroughly)
4. **Assets**: Use bundles for production, but consider disabling in development for easier debugging
5. **Compression**: Works best with larger responses; small responses may have compression overhead

## Production Considerations

1. **Use Redis** for caching and rate limiting storage instead of in-memory storage
2. **Configure proper cache timeouts** based on your data update frequency
3. **Monitor rate limit violations** to detect potential abuse or legitimate high usage
4. **Pre-build asset bundles** during deployment rather than on-demand
5. **Set appropriate compression levels** (6-7 is usually optimal)

## Troubleshooting

### Cache not working
- Check that cache is properly initialized in extensions.py
- Verify cache backend is running (if using Redis/Memcached)
- Check cache timeout settings

### Rate limiting too strict
- Adjust limits in app.py or per-endpoint
- Consider different limits for authenticated vs anonymous users
- Use Redis for distributed rate limiting

### Minification breaking JavaScript
- Use `@decorators.bypass_minification` for problematic endpoints
- Check for JavaScript syntax errors
- Consider using source maps for debugging

### Assets not updating
- Clear the assets cache
- Check file permissions in the static folder
- Rebuild assets manually using Flask-Assets CLI
