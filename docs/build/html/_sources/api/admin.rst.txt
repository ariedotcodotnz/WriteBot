Admin API
=========

Administrative endpoints for user management and system monitoring. All endpoints require admin role.

.. note::
   All admin endpoints require authentication with an admin user account.

Dashboard
---------

Admin Dashboard
~~~~~~~~~~~~~~~

.. http:get:: /admin/

   View the admin dashboard with overview statistics and recent activities.

   **Example Response:**

   Returns an HTML page with:

   * Total users, active users, and admin users
   * Statistics for the last 7 days
   * Recent user activities (last 50)
   * Quick links to user management and system monitoring

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin

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

View User
~~~~~~~~~

.. http:get:: /admin/users/(int:user_id)

   View detailed information about a specific user.

   **Parameters:**

   * ``user_id`` (integer) - The user ID

   **Example Response:**

   Returns an HTML page with:

   * User profile information (username, full name, email, role)
   * Account status (active/inactive)
   * User statistics (total generations, last login, registration date)
   * Recent activity history
   * Edit and delete actions

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - User not found

Update User
~~~~~~~~~~~

.. http:post:: /admin/users/(int:user_id)/edit

   Update an existing user account.

   **Parameters:**

   * ``user_id`` (integer) - The user ID

   **Form Parameters:**

   * ``username`` (string, optional) - Update username
   * ``password`` (string, optional) - New password (leave blank to keep current)
   * ``full_name`` (string, optional) - Update full name
   * ``email`` (string, optional) - Update email address
   * ``role`` (string, required) - "user" or "admin"
   * ``is_active`` (boolean, optional) - Active status

   **Status Codes:**

   * ``302 Found`` - Update successful, redirects to user list
   * ``200 OK`` - Validation errors, returns form with errors
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - User not found

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
