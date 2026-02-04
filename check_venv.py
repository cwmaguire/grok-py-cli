#!/usr/bin/env python3
"""Script to verify if we're running in the proper uv-managed virtual environment."""

import sys
import os

def check_venv():
    """Check if we're in the expected virtual environment."""
    current_dir = os.getcwd()
    expected_venv_path = os.path.join(current_dir, ".venv")
    expected_python = os.path.join(expected_venv_path, "bin", "python")

    print(f"Current working directory: {current_dir}")
    print(f"Python executable: {sys.executable}")
    print(f"Expected venv Python: {expected_python}")

    if sys.executable == expected_python:
        print("✅ Correct: Running in the expected virtual environment")
        return True
    else:
        print("❌ Incorrect: Not running in the expected virtual environment")
        print("Make sure to activate with: source .venv/bin/activate")
        return False

def check_packages():
    """Check if required packages are installed."""
    required_packages = ["grok_py", "mcp", "httpx"]

    print("\nChecking required packages:")
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))  # Handle package names with dashes
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Not found")
            return False

    return True

if __name__ == "__main__":
    venv_ok = check_venv()
    packages_ok = check_packages()

    if venv_ok and packages_ok:
        print("\n🎉 Environment is properly set up!")
        sys.exit(0)
    else:
        print("\n💥 Environment setup issues detected!")
        sys.exit(1)