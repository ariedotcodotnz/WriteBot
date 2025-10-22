Styles
======

Manage and retrieve handwriting styles.

List Styles
-----------

.. http:get:: /api/styles

   Get all available handwriting styles.

   **Example Request:**

   .. sourcecode:: http

      GET /api/styles HTTP/1.1
      Host: localhost:5000
      Cookie: session=...

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "styles": [
              {
                  "id": 1,
                  "name": "Style 1",
                  "description": "Default handwriting style",
                  "preview_url": "/api/style-preview/1"
              },
              {
                  "id": 2,
                  "name": "Style 2",
                  "description": "Cursive style",
                  "preview_url": "/api/style-preview/2"
              }
          ]
      }

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated

Style Preview
-------------

.. http:get:: /api/style-preview/(int:style_id)

   Get a preview image for a specific style.

   **Parameters:**

   * ``style_id`` - The style ID

   **Example Request:**

   .. sourcecode:: http

      GET /api/style-preview/1 HTTP/1.1
      Host: localhost:5000
      Cookie: session=...

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/svg+xml

      <svg xmlns="http://www.w3.org/2000/svg"...>
        <!-- Preview SVG content -->
      </svg>

   **Status Codes:**

   * ``200 OK`` - Success
   * ``404 Not Found`` - Style not found
   * ``401 Unauthorized`` - Not authenticated
