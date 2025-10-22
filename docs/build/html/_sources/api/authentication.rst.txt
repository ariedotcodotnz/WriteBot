Authentication
==============

The authentication system uses Flask-Login for session management. Users must log in to access protected endpoints.

Login
-----

.. http:post:: /auth/login

   Authenticate a user and create a session.

   **Example Request:**

   .. sourcecode:: http

      POST /auth/login HTTP/1.1
      Host: localhost:5000
      Content-Type: application/x-www-form-urlencoded

      username=johndoe&password=secretpass&remember=on

   **Form Parameters:**

   * ``username`` (string, required) - The username
   * ``password`` (string, required) - The password
   * ``remember`` (boolean, optional) - Remember me checkbox

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 302 FOUND
      Location: /
      Set-Cookie: session=...; HttpOnly

   **Status Codes:**

   * ``302 Found`` - Login successful, redirects to home
   * ``200 OK`` - Login failed, returns login page with error
   * ``400 Bad Request`` - Missing required parameters

Logout
------

.. http:get:: /auth/logout

   End the current user session.

   **Example Request:**

   .. sourcecode:: http

      GET /auth/logout HTTP/1.1
      Host: localhost:5000
      Cookie: session=...

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 302 FOUND
      Location: /auth/login

   **Status Codes:**

   * ``302 Found`` - Logout successful, redirects to login

Session Management
------------------

Sessions are managed automatically by Flask-Login. The session cookie is:

* **HttpOnly**: Cannot be accessed via JavaScript
* **Secure**: Only transmitted over HTTPS in production
* **SameSite**: Set to ``Lax`` for CSRF protection
* **Duration**: 30 days if "Remember Me" is checked

Checking Authentication Status
-------------------------------

To check if a user is authenticated, you can access any protected endpoint. If the session is invalid or expired, you'll receive a ``401 Unauthorized`` response or be redirected to the login page.

.. code-block:: python

   # Example: Check authentication
   import requests

   session = requests.Session()

   # Login
   response = session.post('http://localhost:5000/auth/login', data={
       'username': 'johndoe',
       'password': 'secretpass'
   })

   # Now authenticated, can access protected endpoints
   health = session.get('http://localhost:5000/api/health')
   print(health.json())
