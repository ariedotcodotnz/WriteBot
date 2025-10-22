Admin API
=========

Administrative endpoints for user management and system monitoring. All endpoints require admin role.

.. note::
   All admin endpoints require authentication with an admin user account.

Users
-----

List Users
~~~~~~~~~~

.. http:get:: /admin/users

   Get all users in the system.

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin

Create User
~~~~~~~~~~~

.. http:post:: /admin/users/create

   Create a new user account.

   **Form Parameters:**

   * ``username`` (string, required) - Unique username
   * ``password`` (string, required) - User password
   * ``full_name`` (string, optional) - Full name
   * ``role`` (string, required) - "user" or "admin"
   * ``is_active`` (boolean, optional) - Active status

Update User
~~~~~~~~~~~

.. http:post:: /admin/users/(int:user_id)/edit

   Update an existing user.

Delete User
~~~~~~~~~~~

.. http:post:: /admin/users/(int:user_id)/delete

   Delete a user account.

Statistics
----------

View Statistics
~~~~~~~~~~~~~~~

.. http:get:: /admin/statistics

   Get system-wide statistics.

   **Example Response:**

   .. sourcecode:: json

      {
          "total_generations": 1234,
          "total_users": 45,
          "active_users_7d": 23,
          "total_characters_generated": 567890
      }

Activities
----------

View Activities
~~~~~~~~~~~~~~~

.. http:get:: /admin/activities

   Get user activity log.

   **Query Parameters:**

   * ``page`` (integer, optional) - Page number (default: 1)
   * ``per_page`` (integer, optional) - Items per page (default: 50)
   * ``user_id`` (integer, optional) - Filter by user ID
   * ``type`` (string, optional) - Filter by activity type

   **Activity Types:**

   * ``login`` - User login
   * ``logout`` - User logout
   * ``generate`` - Text generation
   * ``batch`` - Batch generation
   * ``admin_action`` - Admin action
   * ``page_view`` - Page view
