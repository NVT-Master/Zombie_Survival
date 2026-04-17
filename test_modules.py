"""Backward-compatible wrapper for tests/test_modules.py."""

from tests.test_modules import run_smoke_test


if __name__ == "__main__":
    raise SystemExit(run_smoke_test())
