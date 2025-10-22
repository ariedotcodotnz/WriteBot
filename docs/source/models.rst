Database Models
===============

WriteBot uses SQLAlchemy for database management. All models are defined in ``webapp/models.py``.

.. module:: webapp.models

User Model
----------

.. autoclass:: User
   :members:
   :undoc-members:
   :show-inheritance:

   User account model with authentication and role management.

   **Attributes:**

   * ``id`` - Unique user ID
   * ``username`` - Unique username
   * ``password_hash`` - Hashed password
   * ``full_name`` - User's full name
   * ``role`` - User role ("user" or "admin")
   * ``is_active`` - Active status
   * ``created_at`` - Account creation timestamp
   * ``last_login`` - Last login timestamp

   **Methods:**

   * ``set_password(password)`` - Hash and set password
   * ``check_password(password)`` - Verify password
   * ``is_admin()`` - Check if user has admin role

User Activity Model
-------------------

.. autoclass:: UserActivity
   :members:
   :undoc-members:
   :show-inheritance:

   Tracks user actions for auditing and analytics.

   **Activity Types:**

   * ``login`` - User login
   * ``logout`` - User logout
   * ``generate`` - Single generation
   * ``batch`` - Batch generation
   * ``admin_action`` - Admin action
   * ``page_view`` - Page view

Usage Statistics Model
----------------------

.. autoclass:: UsageStatistics
   :members:
   :undoc-members:
   :show-inheritance:

   Daily usage statistics per user.

   **Metrics:**

   * ``svg_generations`` - Number of single generations
   * ``batch_generations`` - Number of batch jobs
   * ``total_lines_generated`` - Total lines generated
   * ``total_characters_generated`` - Total characters generated
   * ``total_processing_time`` - Total processing time (seconds)

Character Override Collection Model
-----------------------------------

.. autoclass:: CharacterOverrideCollection
   :members:
   :undoc-members:
   :show-inheritance:

   Collection of custom hand-drawn character variants.

   **Methods:**

   * ``get_character_count()`` - Get total number of variants
   * ``get_unique_characters()`` - Get list of unique characters

Character Override Model
------------------------

.. autoclass:: CharacterOverride
   :members:
   :undoc-members:
   :show-inheritance:

   Individual character variant with SVG data.

   **Attributes:**

   * ``character`` - The character (single letter/symbol)
   * ``svg_data`` - SVG content
   * ``viewbox_x`` - ViewBox X coordinate
   * ``viewbox_y`` - ViewBox Y coordinate
   * ``viewbox_width`` - ViewBox width
   * ``viewbox_height`` - ViewBox height
   * ``baseline_offset`` - Vertical offset adjustment

Database Schema
---------------

Entity Relationship Diagram
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    User
    ├── UserActivity (one-to-many)
    ├── UsageStatistics (one-to-many)
    └── CharacterOverrideCollection (one-to-many, via created_by)

    CharacterOverrideCollection
    └── CharacterOverride (one-to-many)

Indexes
~~~~~~~

* ``User.username`` - Unique index
* ``UserActivity.user_id`` - Index for faster queries
* ``UserActivity.timestamp`` - Index for date-based queries
* ``UsageStatistics.(user_id, date)`` - Composite unique index
* ``CharacterOverride.(collection_id, character)`` - Composite index

Migrations
----------

Database migrations are handled using SQLAlchemy's ``create_all()`` method. To initialize the database:

.. code-block:: python

   from webapp.app import app, db
   with app.app_context():
       db.create_all()

Or run the initialization script:

.. code-block:: bash

   python -m webapp.init_db
