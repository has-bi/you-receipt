#!/usr/bin/env python3
"""
Setup verification script for Pharmacy Stock Management System.
Run this to check if all requirements are properly configured.
"""

import json
import os
import sys
from pathlib import Path


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✓ {description}: Found")
        return True
    else:
        print(f"✗ {description}: NOT FOUND")
        return False


def check_env_var(var_name, description):
    """Check if environment variable is set."""
    value = os.getenv(var_name)
    if value and value != f"your_{var_name.lower()}":
        print(f"✓ {description}: Set")
        return True
    else:
        print(f"✗ {description}: NOT SET or using default value")
        return False


def verify_credentials_json():
    """Verify credentials.json structure."""
    try:
        with open("credentials.json", "r") as f:
            creds = json.load(f)

        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing_fields = [field for field in required_fields if field not in creds]

        if missing_fields:
            print(f"✗ credentials.json: Missing fields: {', '.join(missing_fields)}")
            return False

        if creds.get("type") != "service_account":
            print("✗ credentials.json: Not a service account key")
            return False

        print("✓ credentials.json: Valid service account")
        print(f"  Service account email: {creds.get('client_email')}")
        return True
    except FileNotFoundError:
        print("✗ credentials.json: File not found")
        return False
    except json.JSONDecodeError:
        print("✗ credentials.json: Invalid JSON format")
        return False
    except Exception as e:
        print(f"✗ credentials.json: Error reading file: {e}")
        return False


def verify_env_file():
    """Verify .env file."""
    if not Path(".env").exists():
        print("✗ .env file: NOT FOUND")
        print("  Run: cp .env.example .env")
        return False

    print("✓ .env file: Found")

    # Load .env
    from dotenv import load_dotenv

    load_dotenv()

    checks = [
        ("MISTRAL_API_KEY", "Mistral API Key"),
        ("ANTHROPIC_API_KEY", "Anthropic API Key"),
        ("GCS_BUCKET_NAME", "GCS Bucket Name"),
        ("GCS_PROJECT_ID", "GCS Project ID"),
        ("MASTER_SHEET_ID", "Master Sheet ID"),
        ("OUTPUT_SHEET_ID", "Output Sheet ID"),
    ]

    all_set = True
    for var, desc in checks:
        if not check_env_var(var, f"  {desc}"):
            all_set = False

    return all_set


def main():
    print("=" * 60)
    print("Pharmacy Stock Management System - Setup Verification")
    print("=" * 60)
    print()

    all_checks_passed = True

    # Check files
    print("1. Checking Required Files:")
    print("-" * 60)
    if not check_file_exists(".env", ".env file"):
        all_checks_passed = False
    if not check_file_exists("credentials.json", "Google credentials"):
        all_checks_passed = False
    print()

    # Verify credentials.json structure
    print("2. Verifying Google Service Account Credentials:")
    print("-" * 60)
    if not verify_credentials_json():
        all_checks_passed = False
    print()

    # Check environment variables
    print("3. Checking Environment Variables:")
    print("-" * 60)
    if not verify_env_file():
        all_checks_passed = False
    print()

    # Check dependencies
    print("4. Checking Python Dependencies:")
    print("-" * 60)
    try:
        import fastapi

        print(f"✓ FastAPI: {fastapi.__version__}")
    except ImportError:
        print("✗ FastAPI: NOT INSTALLED")
        all_checks_passed = False

    try:
        from google.oauth2 import service_account as google_service_account

        print(f"✓ google-auth: Installed ({google_service_account.__name__})")
    except ImportError:
        print("✗ google-auth: NOT INSTALLED")
        all_checks_passed = False

    try:
        import mistralai

        version = getattr(mistralai, "__version__", "unknown")
        print(f"✓ mistralai: Installed (v{version})")
    except ImportError:
        print("✗ mistralai: NOT INSTALLED")
        all_checks_passed = False

    try:
        import anthropic

        version = getattr(anthropic, "__version__", "unknown")
        print(f"✓ anthropic: Installed (v{version})")
    except ImportError:
        print("✗ anthropic: NOT INSTALLED")
        all_checks_passed = False
    print()

    # Check directories
    print("5. Checking Directories:")
    print("-" * 60)
    if not check_file_exists("static/uploads", "Uploads directory"):
        print("  Creating uploads directory...")
        Path("static/uploads").mkdir(parents=True, exist_ok=True)
        print("  ✓ Created")
    print()

    # Final summary
    print("=" * 60)
    if all_checks_passed:
        print("✓ All checks passed! You're ready to run the application.")
        print()
        print("Next steps:")
        print("  1. Ensure Google Sheets are set up (see SHEETS_SETUP.md)")
        print("  2. Share sheets with service account email")
        print("  3. Run: docker compose up --build")
        print("     OR: uvicorn main:app --reload")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("  - Copy .env.example to .env and fill in your credentials")
        print("  - Download service account JSON as credentials.json")
        print("  - Install dependencies: uv pip install -r pyproject.toml")
        print("  - See README.md for detailed setup instructions")
    print("=" * 60)

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
