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

   View details of a specific collection.

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
