Utilities
=========

Helper functions and utilities used throughout WriteBot.

Authentication Utilities
------------------------

.. module:: webapp.utils.auth_utils

.. autofunction:: admin_required

   Decorator to require admin role for a route.

   Usage:

   .. code-block:: python

      @app.route('/admin/dashboard')
      @login_required
      @admin_required
      def admin_dashboard():
          return render_template('admin/dashboard.html')

.. autofunction:: log_activity

   Log user activity to the database.

   :param activity_type: Type of activity ('login', 'logout', 'generate', etc.)
   :param description: Optional description of the activity
   :param metadata: Optional dictionary of additional metadata

.. autofunction:: track_generation

   Track generation statistics for the current user.

   :param lines_count: Number of lines generated
   :param chars_count: Number of characters generated
   :param processing_time: Processing time in seconds
   :param is_batch: Whether this is a batch generation

Text Processing Utilities
--------------------------

.. module:: webapp.utils.text_utils

Text processing utilities for handwriting generation.

**Functions:**

* ``sanitize_text(text)`` - Remove problematic characters
* ``split_into_lines(text, max_width)`` - Split text into lines
* ``estimate_width(text, style)`` - Estimate text width

Page Utilities
--------------

.. module:: webapp.utils.page_utils

Utilities for pagination and page management.

**Functions:**

* ``paginate(query, page, per_page)`` - Paginate database query
* ``get_page_range(current_page, total_pages)`` - Get page number range

Character Override Utilities
-----------------------------

.. module:: handwriting_synthesis.hand.character_override_utils

Utilities for applying character overrides to generated handwriting.

**Functions:**

* ``apply_character_overrides(svg_data, overrides)`` - Replace characters with custom SVG
* ``parse_character_svg(svg_content)`` - Parse and validate character SVG
* ``merge_character_into_svg(target_svg, char_svg, position)`` - Merge character SVG

Example Usage
-------------

Activity Logging
~~~~~~~~~~~~~~~~

.. code-block:: python

   from webapp.utils.auth_utils import log_activity

   # Log a generation
   log_activity(
       'generate',
       f'Generated text: {text[:50]}...',
       metadata={'text_length': len(text), 'style_id': style_id}
   )

Generation Tracking
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from webapp.utils.auth_utils import track_generation
   import time

   start_time = time.time()
   # ... perform generation ...
   processing_time = time.time() - start_time

   track_generation(
       lines_count=5,
       chars_count=len(text),
       processing_time=processing_time,
       is_batch=False
   )

Custom Decorators
-----------------

Admin Required
~~~~~~~~~~~~~~

The ``@admin_required`` decorator checks if the current user has admin privileges:

.. code-block:: python

   from functools import wraps
   from flask_login import current_user
   from flask import abort

   def admin_required(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           if not current_user.is_authenticated:
               abort(401)
           if not current_user.is_admin():
               abort(403)
           return f(*args, **kwargs)
       return decorated_function

Rate Limiting
~~~~~~~~~~~~~

While not currently implemented, rate limiting can be added using decorators:

.. code-block:: python

   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address

   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["200 per day", "50 per hour"]
   )

   @app.route("/api/generate")
   @limiter.limit("10 per minute")
   def generate():
       pass
