"""Utilities for Docker availability detection in tests."""

import os

# Skip Docker tests if environment variable is set (useful in CI/containers)
SKIP_DOCKER_TESTS = os.environ.get("SKIP_DOCKER_TESTS", "").lower() in ("1", "true", "yes")

# Skip reason for Docker-dependent tests
SKIP_DOCKER_REASON = "Docker tests skipped (SKIP_DOCKER_TESTS=1)"
