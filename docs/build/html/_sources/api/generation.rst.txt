Generation
==========

Generate handwritten text from input strings. The API supports both single and batch generation.

Generate SVG
------------

.. http:post:: /api/v1/generate/svg

   Generate handwritten text and return as SVG.

   **Example Request:**

   .. sourcecode:: http

      POST /api/v1/generate/svg HTTP/1.1
      Host: localhost:5000
      Content-Type: application/json
      Cookie: session=...

      {
          "text": "Hello, World!",
          "style_id": 1,
          "bias": 0.75,
          "color": "#000000",
          "line_height": 60,
          "view_width": 800,
          "view_height": 600,
          "character_override_collection_id": null
      }

   **JSON Parameters:**

   * ``text`` (string, required) - The text to generate
   * ``style_id`` (integer, optional) - Handwriting style ID (default: 1)
   * ``bias`` (float, optional) - Bias value 0.0-1.0 (default: 0.75)
   * ``color`` (string, optional) - Stroke color hex code (default: "#000000")
   * ``line_height`` (integer, optional) - Line height in pixels (default: 60)
   * ``view_width`` (integer, optional) - SVG viewport width (default: 800)
   * ``view_height`` (integer, optional) - SVG viewport height (default: 600)
   * ``character_override_collection_id`` (integer, optional) - Character override collection ID

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\"...",
          "metadata": {
              "processing_time": 1.234,
              "num_lines": 1,
              "num_characters": 13,
              "style_id": 1,
              "bias": 0.75
          }
      }

   **Status Codes:**

   * ``200 OK`` - Generation successful
   * ``400 Bad Request`` - Invalid parameters
   * ``401 Unauthorized`` - Not authenticated
   * ``500 Internal Server Error`` - Generation failed

Generate (Legacy)
-----------------

.. http:post:: /api/generate

   Legacy generation endpoint. Returns SVG content directly.

   **Example Request:**

   .. sourcecode:: http

      POST /api/generate HTTP/1.1
      Host: localhost:5000
      Content-Type: application/json
      Cookie: session=...

      {
          "text": "WriteBot",
          "style_id": 2,
          "bias": 0.8
      }

   **JSON Parameters:**

   Same as ``/api/v1/generate/svg``

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/svg+xml

      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
        <path d="M 10,50 L 20,55 ..." stroke="#000" fill="none"/>
      </svg>

   **Status Codes:**

   * ``200 OK`` - Generation successful
   * ``400 Bad Request`` - Invalid parameters
   * ``401 Unauthorized`` - Not authenticated

Generate with Metadata
----------------------

.. http:post:: /api/v1/generate

   Generate handwritten text with detailed metadata.

   **Example Request:**

   .. sourcecode:: http

      POST /api/v1/generate HTTP/1.1
      Host: localhost:5000
      Content-Type: application/json
      Cookie: session=...

      {
          "text": "Handwriting synthesis",
          "style_id": 1
      }

   **JSON Parameters:**

   Same as ``/api/v1/generate/svg``

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "success": true,
          "svg": "<svg...",
          "metadata": {
              "text_length": 21,
              "num_strokes": 145,
              "bounding_box": {
                  "width": 650,
                  "height": 80
              },
              "generation_params": {
                  "style_id": 1,
                  "bias": 0.75,
                  "color": "#000000"
              }
          }
      }

   **Status Codes:**

   * ``200 OK`` - Generation successful
   * ``400 Bad Request`` - Invalid parameters
   * ``401 Unauthorized`` - Not authenticated

Parameter Details
-----------------

Bias Parameter
~~~~~~~~~~~~~~

The ``bias`` parameter controls the randomness of the generated handwriting:

* ``0.0`` - Most random, less like training data
* ``0.5`` - Balanced randomness
* ``0.75`` - Recommended default
* ``1.0`` - Least random, most like training data

**Recommendation**: Use values between 0.7 and 0.9 for best results.

Color Parameter
~~~~~~~~~~~~~~~

The ``color`` parameter accepts:

* Hex codes: ``#000000``, ``#FF5733``
* Named colors: ``black``, ``blue``, ``red``
* RGB: ``rgb(255, 0, 0)``

Line Height
~~~~~~~~~~~

The ``line_height`` parameter determines:

* Vertical spacing between lines
* Recommended: 50-80 pixels
* Smaller values create tighter line spacing
* Larger values create looser line spacing

Character Overrides
~~~~~~~~~~~~~~~~~~~

When ``character_override_collection_id`` is provided:

* AI-generated characters are replaced with custom hand-drawn variants
* The system randomly selects from available variants for each character
* Only characters with overrides are replaced
* Other characters use AI generation

Error Handling
--------------

**Empty Text Error:**

.. sourcecode:: json

   {
       "error": "Text parameter is required and cannot be empty"
   }

**Invalid Style Error:**

.. sourcecode:: json

   {
       "error": "Invalid style_id. Available styles: 1-10"
   }

**Generation Error:**

.. sourcecode:: json

   {
       "error": "Failed to generate handwriting",
       "details": "Model error: ..."
   }
