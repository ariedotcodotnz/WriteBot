API Reference
=============

This section provides detailed documentation for all WriteBot API endpoints.

.. toctree::
   :maxdepth: 2

   authentication
   generation
   batch
   styles
   admin
   character_overrides

API Overview
------------

Base URL
~~~~~~~~

All API endpoints are relative to the base URL:

* Development: ``http://localhost:5000``
* Production: ``https://your-domain.com``

Authentication
~~~~~~~~~~~~~~

Most endpoints require authentication via Flask-Login session cookies. After logging in, the session cookie is automatically included in subsequent requests.

Response Format
~~~~~~~~~~~~~~~

All API responses are in JSON format with the following structure:

**Success Response:**

.. code-block:: json

    {
        "status": "success",
        "data": { ... },
        "message": "Operation completed successfully"
    }

**Error Response:**

.. code-block:: json

    {
        "error": "Error message",
        "details": "Additional error details"
    }

HTTP Status Codes
~~~~~~~~~~~~~~~~~

The API uses standard HTTP status codes:

* ``200 OK``: Request successful
* ``201 Created``: Resource created successfully
* ``400 Bad Request``: Invalid request parameters
* ``401 Unauthorized``: Authentication required
* ``403 Forbidden``: Insufficient permissions
* ``404 Not Found``: Resource not found
* ``500 Internal Server Error``: Server error

Rate Limiting
~~~~~~~~~~~~~

Currently, there are no rate limits. However, it's recommended to:

* Limit concurrent requests to 5 per session
* Use batch endpoints for multiple generations
* Implement exponential backoff for retries

Common Headers
~~~~~~~~~~~~~~

**Request Headers:**

.. code-block:: http

    Content-Type: application/json
    Accept: application/json

**Response Headers:**

.. code-block:: http

    Content-Type: application/json
    X-Content-Type-Options: nosniff
