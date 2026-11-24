import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import app
from core.orchestrator import save


class TestUploadSave(unittest.TestCase):
    class ChunkedUpload:
        filename = "sample.pdf"

        def __init__(self, content):
            self.content = content
            self.read_sizes = []

        async def read(self, size=-1):
            self.read_sizes.append(size)
            if size < 0:
                size = len(self.content)
            chunk, self.content = self.content[:size], self.content[size:]
            return chunk

    def test_oversized_upload_is_read_only_to_limit_and_removed(self):
        """413 is raised and staging dir is cleaned up when file exceeds the limit."""
        upload = self.ChunkedUpload(b"x" * 12)

        with patch("core.orchestrator.MAX_UPLOAD_SIZE", 8), \
             patch("core.orchestrator.create_staging_area") as mock_create:
            # Build a fake StagingContext backed by a real temp dir
            import tempfile, shutil
            tmp = Path(tempfile.mkdtemp())
            from core.staging_manager import StagingContext
            fake_ctx = StagingContext(
                doc_id="test-id",
                filename="sample.pdf",
                dir=tmp,
                state_path=tmp / "state.json",
                pdf_path=tmp / "sample.pdf",
                md_path=tmp / "sample.md",
                pages_path=tmp / "sample.pages.json",
                chunks_path=tmp / "sample.chunks.json",
            )
            # Write a minimal state.json so update_state doesn't fail
            fake_ctx.state_path.write_text('{"synced_assets": {}}', encoding="utf-8")
            mock_create.return_value = fake_ctx

            try:
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(save(upload))
                self.assertEqual(ctx.exception.status_code, 413)
                # Staging dir must be removed on oversized upload
                self.assertFalse(tmp.exists())
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_upload_at_size_limit_is_saved(self):
        """save() streams the file into the staging dir and returns a StagingContext."""
        upload = self.ChunkedUpload(b"12345678")

        with patch("core.orchestrator.MAX_UPLOAD_SIZE", 8), \
             patch("core.orchestrator.create_staging_area") as mock_create, \
             patch("core.orchestrator.update_state") as mock_state:
            import tempfile, shutil
            tmp = Path(tempfile.mkdtemp())
            from core.staging_manager import StagingContext
            fake_ctx = StagingContext(
                doc_id="test-id",
                filename="sample.pdf",
                dir=tmp,
                state_path=tmp / "state.json",
                pdf_path=tmp / "sample.pdf",
                md_path=tmp / "sample.md",
                pages_path=tmp / "sample.pages.json",
                chunks_path=tmp / "sample.chunks.json",
            )
            mock_create.return_value = fake_ctx

            try:
                result = asyncio.run(save(upload))
                self.assertIs(result, fake_ctx)
                self.assertEqual(fake_ctx.pdf_path.read_bytes(), b"12345678")
                mock_state.assert_called_once()
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


class TestAppEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_doc_name = "__ci_test_api_doc__"

    def test_health_check(self):
        """GET / returns 200 with server status string."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bud's Backend is 200", response.text)

    @patch("core.get_uploaded_files.list_document_filenames")
    def test_list_files(self, mock_list):
        """GET /list_files returns JSON with files list from Supabase."""
        mock_list.return_value = [self.test_doc_name]
        response = self.client.get("/list_files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("files", data)
        self.assertIsInstance(data["files"], list)
        self.assertIn(self.test_doc_name, data["files"])

    @patch("core.doc_selector.download_bytes")
    def test_get_file_success(self, mock_download):
        """GET /files/{filename} returns the PDF content from Supabase Storage."""
        mock_download.return_value = b"%PDF-1.4 mock pdf data"
        response = self.client.get(f"/files/{self.test_doc_name}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-1.4 mock pdf data")
        mock_download.assert_called_once_with(f"pdfs/{self.test_doc_name}.pdf")

    @patch("core.doc_selector.download_bytes", return_value=None)
    def test_get_file_not_found(self, mock_download):
        """GET /files/{filename} returns 404 for missing file in Supabase Storage."""
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

    @patch("app.download_bytes", return_value=None)
    def test_markdown_endpoint_not_found(self, mock_download):
        """GET /markdown/{filename} returns 404 for missing markdown file."""
        response = self.client.get("/markdown/non_existent_doc")
        self.assertEqual(response.status_code, 404)

    def test_markdown_endpoint_traversal_blocked(self):
        """GET /markdown/{filename} returns 400 when traversal is attempted."""
        response = self.client.get("/markdown/..invalid")
        self.assertEqual(response.status_code, 400)

    @patch("app.download_bytes")
    def test_markdown_endpoint_success(self, mock_download):
        """GET /markdown/{filename} returns structured pages list from Supabase Storage."""
        mock_download.return_value = json.dumps(
            [{"page_number": 1, "text": "# Test Markdown Header\nSome content"}]
        ).encode("utf-8")

        response = self.client.get("/markdown/__test_sample__")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pages", data)
        self.assertEqual(data["pages"][0]["page_number"], 1)
        self.assertIn("# Test Markdown Header", data["pages"][0]["text"])

    @patch("app.orchestrator.query")
    def test_ask_endpoint_success(self, mock_query):
        """POST /ask returns 200 with answer from orchestrator."""
        mock_query.return_value = {
            "query": "hello",
            "results": "mock answer",
            "sources": [{"page": 1}],
        }
        response = self.client.post("/ask", json={"query": "hello"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], "mock answer")

    @patch("app.orchestrator.query")
    def test_ask_endpoint_propagates_http_exception(self, mock_query):
        """POST /ask propagates HTTPException raised by orchestrator."""
        mock_query.side_effect = HTTPException(status_code=404, detail="No documents")
        response = self.client.post("/ask", json={"query": "hello"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("No documents", response.text)


class TestGenerateModelConfig(unittest.TestCase):
    @patch("core.generate.get_client")
    def test_generate_response_uses_env_llm(self, mock_get_client):
        """generate_response uses model configured in environment variable."""
        from core.generate import generate_response

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mock response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch.dict("os.environ", {"LLM": "custom/test-model"}):
            result = generate_response("Test prompt")
            self.assertEqual(result, "Mock response")
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "custom/test-model")

    @patch("core.generate.get_client")
    def test_stream_response_uses_env_llm(self, mock_get_client):
        """stream_response uses model configured in environment variable."""
        from core.generate import stream_response

        mock_client = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="chunk"))]
        mock_client.chat.completions.create.return_value = [mock_chunk]
        mock_get_client.return_value = mock_client

        with patch.dict("os.environ", {"LLM": "custom/stream-model"}):
            tokens = list(stream_response("Test prompt"))
            self.assertEqual(tokens, ["chunk"])
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "custom/stream-model")


if __name__ == "__main__":
    unittest.main()
