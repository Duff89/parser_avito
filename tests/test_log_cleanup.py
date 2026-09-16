import os
import tempfile
import time
from pathlib import Path

from utils.log_cleanup import clean_old_logs


def test_clean_old_logs_removes_old_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        old_log = dir_path / "app.old.log"
        fresh_log = dir_path / "app.log"

        old_log.write_text("old logs")
        fresh_log.write_text("fresh logs")

        # Set mtime of old_log to 10 days ago
        ten_days_ago = time.time() - (10 * 86400)
        os.utime(old_log, (ten_days_ago, ten_days_ago))

        removed = clean_old_logs(dir_path, max_age_days=5, max_files=10)

        assert len(removed) == 1
        assert old_log.name in [f.name for f in removed]
        assert not old_log.exists()
        assert fresh_log.exists()


def test_clean_old_logs_prunes_excess_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        now = time.time()

        # Create 8 files, each 1 hour apart
        files = []
        for i in range(8):
            f = dir_path / f"app.{i}.log"
            f.write_text(f"log {i}")
            file_time = now - (i * 3600)
            os.utime(f, (file_time, file_time))
            files.append(f)

        # Retain at most 3 files
        removed = clean_old_logs(dir_path, max_age_days=30, max_files=3)

        assert len(removed) == 5
        remaining = list(dir_path.glob("*.log"))
        assert len(remaining) == 3
        # The 3 newest files should be app.0.log, app.1.log, app.2.log
        remaining_names = {f.name for f in remaining}
        assert remaining_names == {"app.0.log", "app.1.log", "app.2.log"}


def test_clean_old_logs_handles_missing_dir():
    result = clean_old_logs("non_existent_logs_dir_xyz_123")
    assert result == []


def test_clean_old_logs_preserves_non_log_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        data_json = dir_path / "data.json"
        config_toml = dir_path / "config.toml"
        old_log = dir_path / "app.2025-01-01.log"

        data_json.write_text("{}")
        config_toml.write_text("")
        old_log.write_text("old log")

        ten_days_ago = time.time() - (10 * 86400)
        os.utime(data_json, (ten_days_ago, ten_days_ago))
        os.utime(config_toml, (ten_days_ago, ten_days_ago))
        os.utime(old_log, (ten_days_ago, ten_days_ago))

        removed = clean_old_logs(dir_path, max_age_days=5, max_files=1)

        assert len(removed) == 1
        assert removed[0].name == "app.2025-01-01.log"
        assert data_json.exists()
        assert config_toml.exists()
