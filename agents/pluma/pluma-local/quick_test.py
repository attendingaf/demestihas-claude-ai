#!/usr/bin/env python3
"""Quick test script to verify all imports are working."""

import sys
print("Testing Python imports for Pluma Local...")
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}\n")

# Test each critical import
imports_to_test = [
    ("dotenv", "python-dotenv"),
    ("anthropic", "anthropic"),
    ("google.auth", "google-auth"),
    ("googleapiclient.discovery", "google-api-python-client"),
    ("google_auth_oauthlib.flow", "google-auth-oauthlib"),
    ("redis", "redis"),
    ("rich.console", "rich"),
    ("rich.table", "rich"),
    ("rich.prompt", "rich"),
]

all_success = True

for module_name, package_name in imports_to_test:
    try:
        if "." in module_name:
            parts = module_name.split(".")
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)
        else:
            __import__(module_name)
        print(f"✅ {package_name} - {module_name}")
    except ImportError as e:
        print(f"❌ {package_name} failed: {e}")
        all_success = False

print("\n" + "="*50)

if all_success:
    print("✅ All imports successful! Environment is ready.")
    print("\nYou can now run:")
    print("  python test_interface.py")
else:
    print("❌ Some imports failed. Please check the errors above.")
    sys.exit(1)
