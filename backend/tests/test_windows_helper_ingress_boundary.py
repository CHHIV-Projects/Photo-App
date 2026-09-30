from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class WindowsHelperIngressBoundaryTests(unittest.TestCase):
    def test_compose_helper_service_is_loopback_only_and_has_no_source_authority(self) -> None:
        compose = (REPOSITORY_ROOT / "docker" / "compose.development.yml").read_text(encoding="utf-8")
        helper_block = compose.split("  helper-ingress:\n", 1)[1].split("\n  frontend:\n", 1)[0]
        self.assertIn('"127.0.0.1:18011:8011"', helper_block)
        self.assertIn("app.helper_main:app", helper_block)
        self.assertIn("- application_internal", helper_block)
        self.assertIn("- helper_loopback", helper_block)
        self.assertNotIn("browser_edge", helper_block)
        self.assertEqual(helper_block.count("volumes:"), 1)
        self.assertEqual(
            helper_block.count("windows_acquisition_receiving:/app/storage/acquisition/windows"),
            1,
        )
        self.assertNotIn("group_add:", helper_block)
        self.assertNotIn("/app/sources", helper_block)
        self.assertNotIn("/app/storage/vault", helper_block)
        self.assertNotIn("/var/run/docker.sock", helper_block)
        self.assertNotIn("application_storage", helper_block)
        self.assertNotIn("photo-organizer-source-access", helper_block)
        self.assertNotIn("REDIS_", helper_block)

    def test_helper_asgi_app_does_not_import_ordinary_application_router(self) -> None:
        helper_main = (REPOSITORY_ROOT / "backend" / "app" / "helper_main.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("app.api.windows_helper", helper_main)
        self.assertNotIn("app.api.admin", helper_main)
        self.assertNotIn("app.main", helper_main)
        self.assertNotIn("StaticFiles", helper_main)
        self.assertNotIn("CORSMiddleware", helper_main)



    def test_ordinary_backend_mounts_admin_controls_but_not_helper_ingress(self) -> None:
        main = (REPOSITORY_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("app.api.windows_helper_admin", main)
        self.assertNotIn("app.api.windows_helper import", main)
        frontend_proxy = (REPOSITORY_ROOT / "frontend" / "src" / "lib" / "backendProxy.ts").read_text(encoding="utf-8")
        self.assertNotIn("helper/v1", frontend_proxy)
if __name__ == "__main__":
    unittest.main()
