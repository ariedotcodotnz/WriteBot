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
