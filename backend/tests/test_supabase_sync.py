"""
tests/test_supabase_sync.py
Unit tests for core/supabase_sync.py — tests checkpoint skipping, retry behavior,
DB record commit, and staging cleanup semantics.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from core.staging_manager import StagingContext, _default_state
from core.supabase_sync import sync_to_supabase, _upload_asset


def _create_test_ctx(tmp: Path, filename: str = "sample.pdf") -> StagingContext:
    """Helper to set up a populated staging directory with mock files."""
    stem = Path(filename).stem
    ctx = StagingContext(
        doc_id="test-sync-id",
        filename=filename,
        dir=tmp,
        state_path=tmp / "state.json",
        pdf_path=tmp / filename,
        md_path=tmp / f"{stem}.md",
        pages_path=tmp / f"{stem}.pages.json",
        chunks_path=tmp / f"{stem}.chunks.json",
    )
    # Write initial state
    state = _default_state("test-sync-id", filename)
    ctx.state_path.write_text(json.dumps(state), encoding="utf-8")

    # Create dummy files for all assets
    ctx.pdf_path.write_bytes(b"%PDF-1.4 dummy content")
    ctx.md_path.write_text("# Mock Markdown", encoding="utf-8")
    ctx.pages_path.write_text('[{"page_number": 1, "text": "mock"}]', encoding="utf-8")
    ctx.chunks_path.write_text('[{"text": "chunk 1"}]', encoding="utf-8")
    return ctx


class TestSupabaseSync(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctx = _create_test_ctx(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("core.supabase_sync.upload_bytes")
    @patch("core.supabase_sync.record_document")
    @patch("core.supabase_sync.cleanup_staging_area")
    def test_full_sync_uploads_all_assets_and_cleans_up(self, mock_cleanup, mock_record, mock_upload):
        """A clean sync uploads PDF, Markdown, extracts, chunks, records in DB, and cleans up."""
        sync_to_supabase(self.ctx, file_size=100, page_count=1)

        # 4 uploads: pdf, markdown, extracts, chunks
        self.assertEqual(mock_upload.call_count, 4)
        mock_record.assert_called_once_with(
            filename="sample.pdf",
            file_path="pdfs/sample.pdf",
            markdown_path="markdown/sample.md",
            json_extract_path="extracts/sample.json",
            chunks_path="chunks/sample_chunks.json",
            file_size_bytes=100,
            page_count=1,
            status="processed",
        )
        mock_cleanup.assert_called_once_with(self.ctx)

    @patch("core.supabase_sync.upload_bytes")
    @patch("core.supabase_sync.record_document")
    @patch("core.supabase_sync.cleanup_staging_area")
    def test_checkpoint_skips_already_synced_assets(self, mock_cleanup, mock_record, mock_upload):
        """Assets already flagged as synced in state.json are skipped on subsequent runs."""
        # Mark PDF and markdown as already synced in state.json
        state = json.loads(self.ctx.state_path.read_text(encoding="utf-8"))
        state["synced_assets"]["pdf"] = True
        state["synced_assets"]["markdown"] = True
        self.ctx.state_path.write_text(json.dumps(state), encoding="utf-8")

        sync_to_supabase(self.ctx, file_size=100, page_count=1)

        # Only extracts and chunks should be uploaded (2 calls, not 4)
        self.assertEqual(mock_upload.call_count, 2)
        uploaded_paths = [call_args[0][0] for call_args in mock_upload.call_args_list]
        self.assertNotIn("pdfs/sample.pdf", uploaded_paths)
        self.assertNotIn("markdown/sample.md", uploaded_paths)
        self.assertIn("extracts/sample.json", uploaded_paths)
        self.assertIn("chunks/sample_chunks.json", uploaded_paths)

        mock_record.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch("core.supabase_sync.upload_bytes")
    @patch("core.supabase_sync.record_document")
    @patch("core.supabase_sync.cleanup_staging_area")
    def test_sync_preserves_staging_if_db_record_fails(self, mock_cleanup, mock_record, mock_upload):
        """If record_document fails, cleanup_staging_area is not called, preserving state for retry."""
        mock_record.side_effect = RuntimeError("DB connection failure")

        with self.assertRaises(RuntimeError):
            sync_to_supabase(self.ctx, file_size=100, page_count=1)

        mock_cleanup.assert_not_called()
        # State should still record that file assets were uploaded
        state = json.loads(self.ctx.state_path.read_text(encoding="utf-8"))
        self.assertTrue(state["synced_assets"]["pdf"])
        self.assertFalse(state.get("db_committed", False))

    @patch("core.supabase_sync.upload_bytes")
    @patch("core.supabase_sync.record_document")
    @patch("core.supabase_sync.cleanup_staging_area")
    def test_sync_preserves_staging_if_upload_fails(self, mock_cleanup, mock_record, mock_upload):
        """If an asset upload fails permanently, staging is not cleaned up and DB is not committed."""
        mock_upload.side_effect = ConnectionError("Network dropped")

        from tenacity import wait_none
        orig_wait = _upload_asset.retry.wait
        _upload_asset.retry.wait = wait_none()

        try:
            with self.assertRaises(ConnectionError):
                sync_to_supabase(self.ctx, file_size=100, page_count=1)

            mock_record.assert_not_called()
            mock_cleanup.assert_not_called()
        finally:
            _upload_asset.retry.wait = orig_wait


class TestUploadRetry(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.test_file = self.tmp / "test.txt"
        self.test_file.write_bytes(b"data")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("core.supabase_sync.upload_bytes")
    def test_upload_asset_retries_and_succeeds(self, mock_upload):
        """_upload_asset retries on transient errors and succeeds when network recovers."""
        mock_upload.side_effect = [ConnectionError("Fail 1"), ConnectionError("Fail 2"), None]

        # Use wait_none so test doesn't sleep during retries
        from tenacity import wait_none
        orig_wait = _upload_asset.retry.wait
        _upload_asset.retry.wait = wait_none()

        try:
            _upload_asset("storage/test.txt", self.test_file, "text/plain")
            self.assertEqual(mock_upload.call_count, 3)
        finally:
            _upload_asset.retry.wait = orig_wait


if __name__ == "__main__":
    unittest.main()
