"""
Tests for the nightly consolidation job, focusing on Turso/SQLite backup compatibility.
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

from src.jobs.nightly import run_nightly_consolidation


def test_nightly_turso_mode_skips_backup():
    """In Turso mode, db_path is not accessed and backup is skipped without error."""
    mock_memory = MagicMock()
    mock_memory.use_turso = True
    # Ensure db_path does NOT exist (as in real Turso mode where it's never set)
    if hasattr(mock_memory, "db_path"):
        del mock_memory.db_path

    mock_nebius = MagicMock()

    with patch("src.jobs.nightly.MemoryGraph", return_value=mock_memory), \
         patch("src.jobs.nightly.NebiusClient", return_value=mock_nebius), \
         patch("src.jobs.nightly.check_medications"), \
         patch("src.jobs.nightly.now_local"), \
         patch("src.jobs.nightly.shutil.copy2") as mock_copy2:

        mock_memory.graph.nodes.return_value = []

        run_nightly_consolidation()

    # shutil.copy2 must NOT be called in Turso mode
    mock_copy2.assert_not_called()


def test_nightly_sqlite_mode_performs_backup():
    """In SQLite mode, shutil.copy2 is called to create a local backup."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        mock_memory = MagicMock()
        mock_memory.use_turso = False
        mock_memory.db_path = db_path

        mock_nebius = MagicMock()

        with patch("src.jobs.nightly.MemoryGraph", return_value=mock_memory), \
             patch("src.jobs.nightly.NebiusClient", return_value=mock_nebius), \
             patch("src.jobs.nightly.check_medications"), \
             patch("src.jobs.nightly.now_local"), \
             patch("src.jobs.nightly.shutil.copy2") as mock_copy2:

            mock_memory.graph.nodes.return_value = []

            run_nightly_consolidation()

        # shutil.copy2 must be called with (db_path, backup_path)
        mock_copy2.assert_called_once()
        args = mock_copy2.call_args[0]
        assert args[0] == db_path
        assert "backups" in args[1]
        assert args[1].endswith(".db")
    finally:
        os.unlink(db_path)
