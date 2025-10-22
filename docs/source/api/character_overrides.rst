Character Overrides
===================

Manage custom hand-drawn character variants that replace AI-generated characters.

.. note::
   All character override endpoints require admin authentication.

Collections
-----------

List Collections
~~~~~~~~~~~~~~~~

.. http:get:: /admin/character-overrides/

   Get all character override collections.

   **Example Response:**

   .. sourcecode:: json

      {
          "collections": [
              {
                  "id": 1,
                  "name": "My Custom Characters",
                  "description": "Hand-drawn letters",
                  "is_active": true,
                  "unique_characters": 26,
                  "total_variants": 78
              }
          ]
      }

Create Collection
~~~~~~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/create

   Create a new character override collection.

   **Form Parameters:**

   * ``name`` (string, required) - Collection name
   * ``description`` (string, optional) - Description
   * ``is_active`` (boolean, optional) - Active status

View Collection
~~~~~~~~~~~~~~~

.. http:get:: /admin/character-overrides/(int:collection_id)

   View details of a specific collection with all character variants.

   **Parameters:**

   * ``collection_id`` (integer) - The collection ID

   **Example Response:**

   Returns an HTML page with:

   * Collection details (name, description, active status)
   * List of all characters with their variants
   * SVG previews of each character variant
   * Upload forms for single and batch uploads
   * Edit and delete actions

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - Collection not found

Edit Collection
~~~~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/(int:collection_id)/edit

   Update an existing character override collection.

   **Parameters:**

   * ``collection_id`` (integer) - The collection ID

   **Form Parameters:**

   * ``name`` (string, required) - Collection name
   * ``description`` (string, optional) - Description
   * ``is_active`` (boolean, optional) - Active status

   **Status Codes:**

   * ``302 Found`` - Update successful, redirects to collection view
   * ``200 OK`` - Validation errors, returns form with errors
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - Collection not found

Delete Collection
~~~~~~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/(int:collection_id)/delete

   Delete a collection and all its character overrides.

   **Parameters:**

   * ``collection_id`` (integer) - The collection ID

   **Status Codes:**

   * ``302 Found`` - Deletion successful, redirects to collection list
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - Collection not found

   **Note:**

   * This action is irreversible
   * All character variants in the collection will also be deleted

Upload Character
~~~~~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/(int:collection_id)/upload

   Upload a single character variant.

   **Form Parameters:**

   * ``character`` (string, required) - Single character
   * ``svg_file`` (file, required) - SVG file
   * ``baseline_offset`` (float, optional) - Baseline offset (default: 0.0)

   **SVG Requirements:**

   * Must be valid SVG format
   * Must include viewBox or width/height attributes
   * Strokes should be converted to paths
   * Use single color (will be replaced during generation)

Batch Upload
~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/(int:collection_id)/upload-batch

   Upload multiple character variants.

   **Form Parameters:**

   * ``svg_files`` (files, required) - Multiple SVG files
   * ``baseline_offset`` (float, optional) - Baseline offset for all

   **File Naming:**

   Characters are extracted from filename:

   * ``a.svg`` → 'a'
   * ``a_1.svg`` → 'a' (variant 1)
   * ``a_2.svg`` → 'a' (variant 2)

Character Management
--------------------

Delete Character Variant
~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /admin/character-overrides/character/(int:override_id)/delete

   Delete a specific character variant.

   **Parameters:**

   * ``override_id`` (integer) - The character override ID

   **Status Codes:**

   * ``302 Found`` - Deletion successful, redirects to collection view
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - Character variant not found

Preview Character
~~~~~~~~~~~~~~~~~

.. http:get:: /admin/character-overrides/character/(int:override_id)/preview

   Preview a character override SVG.

   **Parameters:**

   * ``override_id`` (integer) - The character override ID

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/svg+xml

      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <!-- Character SVG content -->
      </svg>

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated
   * ``403 Forbidden`` - Not an admin
   * ``404 Not Found`` - Character variant not found

   **Usage:**

   * This endpoint can be used as the ``src`` attribute of an ``<img>`` tag
   * Useful for previewing characters before using them in generation

API Endpoint
------------

Get Collections (API)
~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /admin/character-overrides/api/collections

   Get active collections (for use in generation forms).

   **Example Response:**

   .. sourcecode:: json

      [
          {
              "id": 1,
              "name": "My Custom Characters",
              "description": "Hand-drawn letters",
              "character_count": 78,
              "unique_characters": 26
          }
      ]

   **Status Codes:**

   * ``200 OK`` - Success
   * ``401 Unauthorized`` - Not authenticated

Usage in Generation
-------------------

To use character overrides in generation:

.. sourcecode:: json

   {
       "text": "Hello World",
       "style_id": 1,
       "character_override_collection_id": 1
   }

When a collection is specified:

* The system looks for overrides for each character
* If multiple variants exist, one is randomly selected
* Characters without overrides use AI generation
* This creates natural variation in the output
