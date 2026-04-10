from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_info_collection.frontend_launch import FrontendLauncher, LaunchConfig


class FrontendLaunchTests(unittest.TestCase):
    def test_launcher_start_stop_without_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "ui.db"
            fake_server = MagicMock()
            launcher = FrontendLauncher(
                LaunchConfig(
                    db_path=str(db_path),
                    host="127.0.0.1",
                    port=8765,
                    startup_timeout_seconds=3.0,
                )
            )

            with patch("ai_info_collection.frontend_launch.create_ui_server", return_value=fake_server):
                with patch.object(launcher, "_wait_until_ready", return_value=None):
                    result = launcher.start()
                    self.assertEqual(result.status, "started")
                    self.assertIsNotNone(launcher.server)
                    self.assertIsNotNone(launcher.server_thread)
                    self.assertIn("8765", result.url)

            launcher.stop()
            self.assertFalse(launcher.is_running)
            fake_server.shutdown.assert_called_once()
            fake_server.server_close.assert_called_once()

    def test_launcher_reports_port_in_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "ui.db"
            launcher = FrontendLauncher(
                LaunchConfig(
                    db_path=str(db_path),
                    host="127.0.0.1",
                    port=9999,
                    startup_timeout_seconds=1.0,
                )
            )
            with patch("ai_info_collection.frontend_launch.create_ui_server", side_effect=OSError("in use")):
                with self.assertRaises(RuntimeError) as ctx:
                    launcher.start()
            self.assertIn("port may already be in use", str(ctx.exception).lower())

    def test_launcher_stop_cleans_server_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "ui.db"
            fake_server = MagicMock()
            launcher = FrontendLauncher(
                LaunchConfig(
                    db_path=str(db_path),
                    host="127.0.0.1",
                    port=8766,
                    startup_timeout_seconds=3.0,
                )
            )
            with patch("ai_info_collection.frontend_launch.create_ui_server", return_value=fake_server):
                with patch.object(launcher, "_wait_until_ready", return_value=None):
                    launcher.start()
            launcher.stop()
            self.assertIsNone(launcher.server)
            self.assertIsNone(launcher.server_thread)


if __name__ == "__main__":
    unittest.main()
