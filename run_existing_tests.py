#!/usr/bin/env python3
"""
Script to run your existing tests with proper environment setup.
This ensures the database and environment are properly initialized.
"""
import os
import sys
import subprocess


def setup_test_environment():
    """Setup test environment before running tests."""
    print("Setting up test environment...")

    # Set environment variables
    os.environ["DEV_MODE"] = "true"
    os.environ["DB_PATH"] = "test_db.sqlite"
    os.environ["MOCK_EMAIL_DIR"] = "example_mails/"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["CI"] = "true"  # Simulate CI environment

    # Create necessary directories
    os.makedirs("example_mails", exist_ok=True)

    # Initialize database
    print("Initializing test database...")
    subprocess.run([sys.executable, "db_init.py"], check=True)
    subprocess.run([sys.executable, "app_init.py"], check=True)

    print("Test environment ready!\n")


def run_tests():
    """Run pytest with appropriate arguments."""
    # Build pytest command
    pytest_args = [
        sys.executable, "-m", "pytest",
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
    ]

    # Add coverage if pytest-cov is installed
    try:
        import pytest_cov
        pytest_args.extend(["--cov=src", "--cov-report=term-missing"])
    except ImportError:
        print("Note: Install pytest-cov for coverage reports")

    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    else:
        # Default to running all tests
        pytest_args.append("tests/")

    # Run pytest
    print(f"Running: {' '.join(pytest_args)}\n")
    return subprocess.run(pytest_args).returncode


def main():
    """Main function."""
    try:
        # Setup environment
        setup_test_environment()

        # Run tests
        exit_code = run_tests()

        # Exit with same code as pytest
        sys.exit(exit_code)

    except subprocess.CalledProcessError as e:
        print(f"Error during setup: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nTest run interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
