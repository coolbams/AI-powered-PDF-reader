"""
tests/test_staging.py
Unit tests for core/staging_manager.py — no I/O mocking needed as we work
in real temp directories.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.staging_manager import (
    StagingContext,
    _default_state,
    cleanup_staging_area,
    create_staging_area,
    list_incomplete_jobs,
    load_staging_context,
    read_state,
    update_state,
)


def _make_ctx(tmp: Path, filename: str = "test.pdf", db_committed: bool = False) -> StagingContext:
    """Helper: build a StagingContext inside `tmp` with a valid state.json."""
    stem = Path(filename).stem
    ctx = StagingContext(
        doc_id="fake-id",
        filename=filename,
        dir=tmp,
        state_path=tmp / "state.json",
        pdf_path=tmp / filename,
        md_path=tmp / f"{stem}.md",
        pages_path=tmp / f"{stem}.pages.json",
        chunks_path=tmp / f"{stem}.chunks.json",
    )
    state = _default_state("fake-id", filename)
    state["db_committed"] = db_committed
    ctx.state_path.write_text(json.dumps(state), encoding="utf-8")
    return ctx


class TestCreateStagingArea(unittest.TestCase):
    """create_staging_area() must build the right folder structure and state.json."""

    def setUp(self):
        self.staging_root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.staging_root, ignore_errors=True)

    def test_creates_directory_and_state_json(self):
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            ctx = create_staging_area("hello.pdf")

        self.assertTrue(ctx.dir.is_dir())
        self.assertTrue(ctx.state_path.is_file())

    def test_paths_are_relative_to_staging_dir(self):
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            ctx = create_staging_area("report.pdf")

        self.assertEqual(ctx.pdf_path, ctx.dir / "report.pdf")
        self.assertEqual(ctx.md_path, ctx.dir / "report.md")
        self.assertEqual(ctx.pages_path, ctx.dir / "report.pages.json")
        self.assertEqual(ctx.chunks_path, ctx.dir / "report.chunks.json")

    def test_state_json_has_expected_defaults(self):
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            ctx = create_staging_area("doc.pdf")

        state = json.loads(ctx.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["filename"], "doc.pdf")
        self.assertFalse(state["db_committed"])
        self.assertFalse(state["synced_assets"]["pdf"])
        self.assertEqual(state["status"], "staging")

    def test_unique_doc_ids_per_call(self):
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            ctx1 = create_staging_area("a.pdf")
            ctx2 = create_staging_area("a.pdf")

        self.assertNotEqual(ctx1.doc_id, ctx2.doc_id)
        self.assertNotEqual(ctx1.dir, ctx2.dir)


class TestUpdateState(unittest.TestCase):
    """update_state() must merge flat fields and nested synced_assets correctly."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctx = _make_ctx(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flat_field_update(self):
        update_state(self.ctx, {"status": "saved", "file_size": 1024})
        state = read_state(self.ctx)
        self.assertEqual(state["status"], "saved")
        self.assertEqual(state["file_size"], 1024)

    def test_synced_assets_merge_not_replace(self):
        update_state(self.ctx, {"synced_assets": {"pdf": True}})
        state = read_state(self.ctx)
        # Only 'pdf' changed; others remain False
        self.assertTrue(state["synced_assets"]["pdf"])
        self.assertFalse(state["synced_assets"]["markdown"])
        self.assertFalse(state["synced_assets"]["extracts"])

    def test_db_committed_update(self):
        update_state(self.ctx, {"db_committed": True})
        state = read_state(self.ctx)
        self.assertTrue(state["db_committed"])

    def test_multiple_updates_accumulate(self):
        update_state(self.ctx, {"synced_assets": {"pdf": True}})
        update_state(self.ctx, {"synced_assets": {"markdown": True}})
        state = read_state(self.ctx)
        self.assertTrue(state["synced_assets"]["pdf"])
        self.assertTrue(state["synced_assets"]["markdown"])
        self.assertFalse(state["synced_assets"]["extracts"])


class TestCleanupStagingArea(unittest.TestCase):
    """cleanup_staging_area() must delete the entire staging directory."""

    def test_removes_directory(self):
        tmp = Path(tempfile.mkdtemp())
        ctx = _make_ctx(tmp)
        self.assertTrue(tmp.is_dir())
        cleanup_staging_area(ctx)
        self.assertFalse(tmp.exists())

    def test_idempotent_when_already_removed(self):
        tmp = Path(tempfile.mkdtemp())
        ctx = _make_ctx(tmp)
        cleanup_staging_area(ctx)
        # Should not raise even if directory is already gone
        cleanup_staging_area(ctx)


class TestListIncompleteJobs(unittest.TestCase):
    """list_incomplete_jobs() must return only staging dirs where db_committed=False."""

    def setUp(self):
        self.staging_root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.staging_root, ignore_errors=True)

    def _add_job(self, name: str, db_committed: bool) -> Path:
        job_dir = self.staging_root / name
        job_dir.mkdir()
        _make_ctx(job_dir, filename=f"{name}.pdf", db_committed=db_committed)
        return job_dir

    def test_returns_incomplete_jobs(self):
        self._add_job("incomplete", db_committed=False)
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            jobs = list_incomplete_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].filename, "incomplete.pdf")

    def test_ignores_completed_jobs(self):
        self._add_job("done", db_committed=True)
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            jobs = list_incomplete_jobs()
        self.assertEqual(len(jobs), 0)

    def test_mixed_jobs(self):
        self._add_job("done1", db_committed=True)
        self._add_job("pending1", db_committed=False)
        self._add_job("done2", db_committed=True)
        self._add_job("pending2", db_committed=False)
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            jobs = list_incomplete_jobs()
        self.assertEqual(len(jobs), 2)

    def test_ignores_non_directory_entries(self):
        # A stray file inside STAGING_DIR must not crash the scan
        (self.staging_root / ".gitkeep").touch()
        self._add_job("pending", db_committed=False)
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            jobs = list_incomplete_jobs()
        self.assertEqual(len(jobs), 1)

    def test_ignores_dirs_without_state_json(self):
        orphan = self.staging_root / "orphan"
        orphan.mkdir()
        # No state.json written
        with patch("core.staging_manager.STAGING_DIR", self.staging_root):
            jobs = list_incomplete_jobs()
        self.assertEqual(len(jobs), 0)


class TestLoadStagingContext(unittest.TestCase):
    """load_staging_context() must reconstruct a StagingContext from state.json."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_loads_valid_context(self):
        _make_ctx(self.tmp, filename="resume.pdf")
        ctx = load_staging_context(self.tmp)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.filename, "resume.pdf")
        self.assertEqual(ctx.pdf_path, self.tmp / "resume.pdf")

    def test_returns_none_for_missing_state_json(self):
        ctx = load_staging_context(self.tmp)
        self.assertIsNone(ctx)

    def test_returns_none_for_corrupt_state_json(self):
        (self.tmp / "state.json").write_text("not json!!!", encoding="utf-8")
        ctx = load_staging_context(self.tmp)
        self.assertIsNone(ctx)


if __name__ == "__main__":
    unittest.main()
