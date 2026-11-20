import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
from core.doc_selector import UPLOAD_DIR


class TestAppEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_doc_name = "__ci_test_api_doc__"
        cls.test_doc_path = UPLOAD_DIR / f"{cls.test_doc_name}.pdf"
        cls.test_doc_path.write_bytes(b"%PDF-1.4 mock pdf data")

    @classmethod
    def tearDownClass(cls):
        if cls.test_doc_path.exists():
            cls.test_doc_path.unlink()

    def test_health_check(self):
        """GET / returns 200 with server status string."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bud's Backend is 200", response.text)

    def test_list_files(self):
        """GET /list_files returns JSON with files list."""
        response = self.client.get("/list_files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("files", data)
        self.assertIsInstance(data["files"], list)
        self.assertIn(self.test_doc_name, data["files"])

    def test_get_file_success(self):
        """GET /files/{filename} returns the PDF content."""
        response = self.client.get(f"/files/{self.test_doc_name}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-1.4 mock pdf data")

    def test_get_file_not_found(self):
        """GET /files/{filename} returns 404 for missing file."""
        response = self.client.get("/files/non_existent_file_abc")
        self.assertEqual(response.status_code, 404)

    def test_get_file_traversal_blocked(self):
        """GET /files/{filename} returns 400 when path traversal is attempted."""
        response = self.client.get("/files/..invalid_traversal")
        self.assertEqual(response.status_code, 400)

    def test_upload_rejects_non_pdf(self):
        """POST /upload rejects files without .pdf extension."""
        files = {"file": ("malicious.txt", b"plain text", "text/plain")}
        response = self.client.post("/upload", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only PDF files are accepted", response.text)

    def test_upload_rejects_empty_file(self):
        """POST /upload rejects empty files."""
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        response = self.client.post("/upload", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("File is empty", response.text)


if __name__ == "__main__":
    unittest.main()
