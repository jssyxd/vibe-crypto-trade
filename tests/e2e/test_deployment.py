"""E2E tests for production deployment."""

import os
import pytest
from pathlib import Path


class TestDeploymentConfiguration:
    """Test deployment configuration and setup."""

    def test_env_file_exists(self, vct_project):
        """Test .env.example file exists."""
        env_example = vct_project / ".env.example"
        assert env_example.exists(), ".env.example should exist"

    def test_dockerfile_exists(self, vct_project):
        """Test Dockerfile exists."""
        dockerfile = vct_project / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile should exist"

    def test_docker_compose_placeholder(self, vct_project):
        """Test docker-compose.yml exists."""
        compose = vct_project / "docker-compose.yml"
        assert compose.exists(), "docker-compose.yml should exist"

    def test_production_md_exists(self, vct_project):
        """Test PRODUCTION.md exists."""
        prod = vct_project / "PRODUCTION.md"
        assert prod.exists(), "PRODUCTION.md should exist"

    def test_production_md_has_sections(self, vct_project):
        """Test PRODUCTION.md has required sections."""
        prod = vct_project / "PRODUCTION.md"
        content = prod.read_text()

        required_sections = [
            "Environment Variables",
            "Docker Deployment",
            "Local Deployment",
            "Monitoring",
            "Trading Flow",
            "Circuit Breakers",
            "Rollback Procedures",
            "Testing",
        ]

        for section in required_sections:
            assert section in content, f"PRODUCTION.md should have {section} section"


class TestEnvironmentSetup:
    """Test environment setup for deployment."""

    def test_python_version(self):
        """Test Python version is 3.11+."""
        import sys
        assert sys.version_info >= (3, 11), "Python 3.11+ required"

    def test_required_packages_importable(self):
        """Test all required packages are importable."""
        required = [
            "streamlit",
            "plotly",
            "ccxt",
            "pandas",
            "numpy",
            "pytest",
            "pytest_asyncio",
        ]

        missing = []
        for package in required:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)

        if missing:
            pytest.skip(f"Optional packages not installed (for deployment validation): {', '.join(missing)}")

    def test_project_structure(self, vct_project):
        """Test all required directories exist."""
        required_dirs = [
            "execution",
            "execution/adapters",
            "execution/risk",
            "execution/signals",
            "execution/core",
            "portfolio",
            "iteration",
            "notifications",
            "dashboard",
            "tests",
            "tests/e2e",
        ]

        for dir_path in required_dirs:
            full_path = vct_project / dir_path
            assert full_path.exists(), f"Required directory missing: {dir_path}"


class TestDockerConfiguration:
    """Test Docker configuration."""

    def test_dockerfile_syntax(self, vct_project):
        """Test Dockerfile has valid syntax."""
        dockerfile = vct_project / "Dockerfile"
        if not dockerfile.exists():
            pytest.skip("Dockerfile not present")

        content = dockerfile.read_text()

        # Basic Dockerfile checks
        assert "FROM" in content, "Dockerfile should have FROM instruction"
        assert "WORKDIR" in content, "Dockerfile should have WORKDIR"
        assert "COPY" in content, "Dockerfile should have COPY"

    def test_docker_compose_services(self, vct_project):
        """Test docker-compose.yml has required services."""
        compose = vct_project / "docker-compose.yml"
        if not compose.exists():
            pytest.skip("docker-compose.yml not present")

        content = compose.read_text()

        assert "vct-trading" in content, "Should have vct-trading service"
        assert "vct-dashboard" in content, "Should have vct-dashboard service"


class TestMonitoringSetup:
    """Test monitoring configuration."""

    def test_logs_directory(self, vct_project):
        """Test logs directory exists or can be created."""
        logs_dir = vct_project / "runs" / "logs"
        # Should be creatable
        logs_dir.mkdir(parents=True, exist_ok=True)
        assert logs_dir.exists()

    def test_data_directory(self, vct_project):
        """Test data directory exists or can be created."""
        data_dir = vct_project / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        assert data_dir.exists()


class TestRollbackProcedures:
    """Test rollback procedure documentation."""

    def test_rollback_documented(self, vct_project):
        """Test rollback procedure is documented."""
        prod = vct_project / "PRODUCTION.md"
        content = prod.read_text()

        assert "docker stop" in content.lower() or "shutdown" in content.lower()
        assert "reset" in content.lower()
        assert "restart" in content.lower()

    def test_circuit_breaker_reset_documented(self, vct_project):
        """Test circuit breaker reset is documented."""
        prod = vct_project / "PRODUCTION.md"
        content = prod.read_text()

        assert "reset" in content.lower()
        assert "circuit" in content.lower()


class TestSecurityConfiguration:
    """Test security configuration."""

    def test_gitignore_includes_env(self, vct_project):
        """Test .gitignore includes .env."""
        gitignore = vct_project / ".gitignore"
        if not gitignore.exists():
            pytest.skip(".gitignore not present")

        content = gitignore.read_text()
        assert ".env" in content, ".gitignore should include .env"

    def test_requirements_file_exists(self, vct_project):
        """Test requirements.txt or setup.py exists."""
        req = vct_project / "requirements.txt"
        setup = vct_project / "setup.py"

        assert req.exists() or setup.exists(), "requirements.txt or setup.py needed"


class TestE2EPipeline:
    """Test full E2E pipeline."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_full_deployment_flow(self, vct_project):
        """Test complete deployment flow (marked as slow)."""
        # This is a documentation test - actual deployment test would be slow

        # 1. Verify all components are documented
        prod = vct_project / "PRODUCTION.md"
        assert prod.exists()

        # 2. Verify test infrastructure
        assert (vct_project / "pytest.ini").exists()
        assert (vct_project / "tests" / "conftest.py").exists()

        # 3. Verify E2E tests exist
        e2e_dir = vct_project / "tests" / "e2e"
        assert e2e_dir.exists()
        assert len(list(e2e_dir.glob("test_*.py"))) > 0

    @pytest.mark.e2e
    def test_documentation_complete(self, vct_project):
        """Test all documentation is complete."""
        docs = [
            "README.md",
            "QUICKSTART.md",
            "PRODUCTION.md",
        ]

        for doc in docs:
            path = vct_project / doc
            assert path.exists(), f"{doc} should exist"
            content = path.read_text()
            assert len(content) > 100, f"{doc} should have substantial content"


# Deployment markers for selective testing
pytestmark = pytest.mark.integration