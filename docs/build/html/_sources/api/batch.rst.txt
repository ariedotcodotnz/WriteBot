Batch Generation
================

Generate multiple handwritten texts from CSV files.

Batch Generate
--------------

.. http:post:: /api/batch

   Process batch generation from CSV file.

   **Example Request:**

   .. sourcecode:: http

      POST /api/batch HTTP/1.1
      Host: localhost:5000
      Content-Type: multipart/form-data
      Cookie: session=...

      --boundary
      Content-Disposition: form-data; name="csv_file"; filename="data.csv"
      Content-Type: text/csv

      text,style_id,bias
      "Hello World",1,0.75
      "Test generation",2,0.8
      --boundary--

   **Form Parameters:**

   * ``csv_file`` (file, required) - CSV file with generation data
   * ``zip_format`` (boolean, optional) - Return as ZIP file
   * ``output_format`` (string, optional) - "svg" or "png"

   **CSV Format:**

   Required columns:

   * ``text`` - Text to generate
   * ``style_id`` (optional) - Style ID, defaults to 1
   * ``bias`` (optional) - Bias value, defaults to 0.75

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip
      Content-Disposition: attachment; filename="batch_results.zip"

      [Binary ZIP content]

   **Status Codes:**

   * ``200 OK`` - Batch generation successful
   * ``400 Bad Request`` - Invalid CSV file
   * ``401 Unauthorized`` - Not authenticated

Download Template
-----------------

.. http:get:: /api/template-csv

   Download a CSV template for batch generation.

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: text/csv
      Content-Disposition: attachment; filename="batch_template.csv"

      text,style_id,bias,color
      "Sample text here",1,0.75,#000000

Streaming Batch Generation
---------------------------

.. http:post:: /api/batch/stream

   Stream batch generation progress in real-time.

   **Example Request:**

   .. sourcecode:: http

      POST /api/batch/stream HTTP/1.1
      Host: localhost:5000
      Content-Type: multipart/form-data
      Cookie: session=...

   **Example Response:**

   Server-Sent Events stream:

   .. sourcecode:: text

      data: {"progress": 0, "status": "starting"}

      data: {"progress": 25, "status": "processing", "current": 1, "total": 4}

      data: {"progress": 100, "status": "complete", "job_id": "abc123"}

   **Status Codes:**

   * ``200 OK`` - Stream started successfully
   * ``400 Bad Request`` - Invalid CSV file
   * ``401 Unauthorized`` - Not authenticated

Download Batch Results
----------------------

.. http:get:: /api/batch/result/(job_id)

   Download the complete batch generation results as a ZIP file.

   **Parameters:**

   * ``job_id`` (string) - The batch job ID returned from streaming batch generation

   **Example Request:**

   .. sourcecode:: http

      GET /api/batch/result/abc123 HTTP/1.1
      Host: localhost:5000
      Cookie: session=...

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip
      Content-Disposition: attachment; filename="writebot_batch_abc123.zip"

      [Binary ZIP content with all generated SVG files]

   **Status Codes:**

   * ``200 OK`` - Results found and returned
   * ``401 Unauthorized`` - Not authenticated
   * ``404 Not Found`` - Job ID not found or results expired

   **Notes:**

   * Results are stored temporarily and may be cleaned up after some time
   * The ZIP file contains all SVG files generated in the batch

Get Individual Batch File
--------------------------

.. http:get:: /api/batch/result/(job_id)/file/(filename)

   Retrieve a single generated file from a batch job for preview purposes.

   **Parameters:**

   * ``job_id`` (string) - The batch job ID
   * ``filename`` (string) - The filename of the individual file

   **Example Request:**

   .. sourcecode:: http

      GET /api/batch/result/abc123/file/sample_0.svg HTTP/1.1
      Host: localhost:5000
      Cookie: session=...

   **Example Response:**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/svg+xml

      <svg xmlns="http://www.w3.org/2000/svg"...>
        <!-- SVG content -->
      </svg>

   **Status Codes:**

   * ``200 OK`` - File found and returned
   * ``401 Unauthorized`` - Not authenticated
   * ``404 Not Found`` - Job or file not found

   **Security:**

   * Path traversal is prevented - only files in the job's output directory can be accessed
   * Files are served with appropriate MIME types (SVG, PNG, etc.)
