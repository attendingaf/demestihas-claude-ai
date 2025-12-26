#!/usr/bin/env python3
"""
Test running the actual telegram bot to see the exact error
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set database connection for local testing
os.environ["PG_CONNINFO"] = "postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"

print("Starting telegram bot test...")
print("-" * 40)

try:
    # Import and run the main function
    from telegram_bot import main
    
    print("Calling main()...")
    main()
    
except Exception as e:
    print(f"\nError occurred: {e}")
    print(f"Error type: {type(e).__name__}")
    print("\nFull traceback:")
    traceback.print_exc()
    
    # Additional debugging
    print("\n" + "-" * 40)
    print("Debug info:")
    
    # Check if it's an attribute error
    if isinstance(e, AttributeError):
        print("This is an AttributeError - likely a version compatibility issue")
        print("The attribute being accessed doesn't exist in this version")
