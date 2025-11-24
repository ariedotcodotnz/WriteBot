"""Script to test the batch generation API endpoint."""

import io
import os
import zipfile

from webapp.app import app


def run_batch_once():
    """
    Simulate a batch generation request to the Flask app.

    Creates a mock CSV file, sends it to the /api/batch endpoint,
    and verifies that the response contains a ZIP file with the generated SVGs.

    Returns:
        0 on success, 1 on failure.
    """
    client = app.test_client()
    csv_content = (
        "filename,text,styles\n"
        "row1.svg,Hello world!,9\n"
        "row2.svg,Second line here,9\n"
    ).encode("utf-8")
    data = {
        "file": (io.BytesIO(csv_content), "test.csv"),
    }
    resp = client.post("/api/batch", data=data, content_type="multipart/form-data")
    if resp.status_code != 200:
        print(f"/api/batch failed: {resp.status_code} {resp.data[:200]!r}")
        return 1
    # Write ZIP to disk
    out_zip = os.path.join(os.getcwd(), "test_batch.zip")
    with open(out_zip, "wb") as f:
        f.write(resp.data)
    # List contents
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
    print("OK /api/batch ->", names)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_batch_once())
