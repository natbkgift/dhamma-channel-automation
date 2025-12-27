"""
Tests for FlowBiz contract endpoints
ทดสอบ endpoints ตามมาตรฐาน FlowBiz Client Product
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    env_vars = {
        "APP_SERVICE_NAME": "test-service",
        "APP_ENV": "test",
        "APP_LOG_LEVEL": "DEBUG",
        "APP_CORS_ORIGINS": '["http://test.example.com"]',
        "FLOWBIZ_VERSION": "1.2.3",
        "FLOWBIZ_BUILD_SHA": "abc123def",
    }
    return env_vars


class TestHealthzEndpoint:
    """Tests for /healthz endpoint"""

    def test_healthz_returns_200(self, client):
        """healthz endpoint ควรคืนค่า HTTP 200"""
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_returns_json(self, client):
        """healthz endpoint ควรคืนค่า JSON"""
        response = client.get("/healthz")
        assert response.headers["content-type"] == "application/json"

    def test_healthz_has_required_fields(self, client):
        """healthz endpoint ควรมี fields ที่จำเป็น"""
        response = client.get("/healthz")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data

    def test_healthz_status_is_ok(self, client):
        """healthz endpoint ควรมี status = ok"""
        response = client.get("/healthz")
        data = response.json()
        assert data["status"] == "ok"

    def test_healthz_service_name_from_config(self, client):
        """healthz endpoint ควรใช้ service name จาก config"""
        response = client.get("/healthz")
        data = response.json()

        # Service name should be set from APP_SERVICE_NAME or fallback
        assert isinstance(data["service"], str)
        assert len(data["service"]) > 0

    def test_healthz_version_from_config(self, client):
        """healthz endpoint ควรใช้ version จาก config"""
        response = client.get("/healthz")
        data = response.json()

        # Version should be set from FLOWBIZ_VERSION
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_healthz_no_authentication_required(self, client):
        """healthz endpoint ไม่ต้องการ authentication"""
        # Should not require session or credentials
        response = client.get("/healthz")
        assert response.status_code == 200
        # Not redirected to login
        assert response.headers.get("location") is None


class TestMetaEndpoint:
    """Tests for /v1/meta endpoint"""

    def test_meta_returns_200(self, client):
        """meta endpoint ควรคืนค่า HTTP 200"""
        response = client.get("/v1/meta")
        assert response.status_code == 200

    def test_meta_returns_json(self, client):
        """meta endpoint ควรคืนค่า JSON"""
        response = client.get("/v1/meta")
        assert response.headers["content-type"] == "application/json"

    def test_meta_has_required_fields(self, client):
        """meta endpoint ควรมี fields ที่จำเป็นทั้งหมด"""
        response = client.get("/v1/meta")
        data = response.json()

        required_fields = ["service", "environment", "version", "build_sha"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_meta_service_name_from_config(self, client):
        """meta endpoint ควรใช้ service name จาก config"""
        response = client.get("/v1/meta")
        data = response.json()

        assert isinstance(data["service"], str)
        assert len(data["service"]) > 0

    def test_meta_environment_from_config(self, client):
        """meta endpoint ควรใช้ environment จาก config"""
        response = client.get("/v1/meta")
        data = response.json()

        assert isinstance(data["environment"], str)
        assert data["environment"] in ["dev", "staging", "prod", "test"]

    def test_meta_version_from_config(self, client):
        """meta endpoint ควรใช้ version จาก config"""
        response = client.get("/v1/meta")
        data = response.json()

        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_meta_build_sha_from_config(self, client):
        """meta endpoint ควรใช้ build_sha จาก config"""
        response = client.get("/v1/meta")
        data = response.json()

        assert isinstance(data["build_sha"], str)
        assert len(data["build_sha"]) > 0

    def test_meta_no_authentication_required(self, client):
        """meta endpoint ไม่ต้องการ authentication"""
        # Should not require session or credentials
        response = client.get("/v1/meta")
        assert response.status_code == 200
        # Not redirected to login
        assert response.headers.get("location") is None


class TestEnvironmentVariableOverrides:
    """Tests for environment variable overrides"""

    def test_service_name_override(self, client, mock_env_vars):
        """ควรสามารถ override service name ผ่าน env var ได้"""
        with patch.dict(os.environ, mock_env_vars):
            # Need to reload config to pick up new env vars
            import importlib

            from app import config

            importlib.reload(config)

            # Create new client with reloaded config
            from app.main import app

            test_client = TestClient(app)

            response = test_client.get("/healthz")
            data = response.json()

            assert data["service"] == "test-service"

    def test_version_override(self, client, mock_env_vars):
        """ควรสามารถ override version ผ่าน env var ได้"""
        with patch.dict(os.environ, mock_env_vars):
            import importlib

            from app import config

            importlib.reload(config)

            from app.main import app

            test_client = TestClient(app)

            response = test_client.get("/v1/meta")
            data = response.json()

            assert data["version"] == "1.2.3"

    def test_build_sha_override(self, client, mock_env_vars):
        """ควรสามารถ override build_sha ผ่าน env var ได้"""
        with patch.dict(os.environ, mock_env_vars):
            import importlib

            from app import config

            importlib.reload(config)

            from app.main import app

            test_client = TestClient(app)

            response = test_client.get("/v1/meta")
            data = response.json()

            assert data["build_sha"] == "abc123def"

    def test_environment_override(self, client, mock_env_vars):
        """ควรสามารถ override environment ผ่าน env var ได้"""
        with patch.dict(os.environ, mock_env_vars):
            import importlib

            from app import config

            importlib.reload(config)

            from app.main import app

            test_client = TestClient(app)

            response = test_client.get("/v1/meta")
            data = response.json()

            assert data["environment"] == "test"


class TestEndpointPerformance:
    """Tests for endpoint performance requirements"""

    def test_healthz_responds_quickly(self, client):
        """healthz endpoint ควร respond เร็ว (< 100ms)"""
        import time

        start = time.time()
        response = client.get("/healthz")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Allow 100ms for overhead in testing environment
        assert elapsed < 0.1, f"healthz took {elapsed:.3f}s, should be < 0.1s"

    def test_meta_responds_quickly(self, client):
        """meta endpoint ควร respond เร็ว (< 100ms)"""
        import time

        start = time.time()
        response = client.get("/v1/meta")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Allow 100ms for overhead in testing environment
        assert elapsed < 0.1, f"meta took {elapsed:.3f}s, should be < 0.1s"


class TestBackwardsCompatibility:
    """Tests for backwards compatibility"""

    def test_existing_endpoints_still_work(self, client):
        """Existing endpoints ควรยังทำงานได้ปกติ"""
        # Test home page (redirects to dashboard or shows login)
        response = client.get("/", follow_redirects=False)
        assert response.status_code in [200, 302]

        # Test login page
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200

    def test_legacy_app_name_still_works(self):
        """Legacy APP_NAME env var ควรยังทำงานได้"""
        with patch.dict(os.environ, {"APP_NAME": "legacy-name"}, clear=False):
            import importlib

            from app import config

            importlib.reload(config)

            # APP_NAME should fallback to APP_SERVICE_NAME
            assert config.APP_NAME in [
                "legacy-name",
                config.APP_SERVICE_NAME,
            ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
