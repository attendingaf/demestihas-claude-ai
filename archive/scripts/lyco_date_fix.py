#!/usr/bin/env python3
"""
Hotfix for Yanay/Lyco date parsing bug
Fixes the 'tomorrow' date parsing issue in lyco_api.py
"""

import sys

def apply_date_parsing_fix():
    """Apply the date parsing fix to lyco_api.py"""
    
    # Read the current file
    try:
        with open('/app/lyco_api.py', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("ERROR: lyco_api.py not found. Are you in the right directory?")
        return False
    
    # Find the line with the Due Date setting
    fixed = False
    for i in range(len(lines)):
        if "properties['Due Date'] = {" in lines[i]:
            # Found it! Replace the problematic section
            indent = "            "  # Match the indentation
            
            # Build the replacement code
            replacement = [
                f"{indent}# Parse relative dates to ISO format\n",
                f"{indent}import datetime\n",
                f"{indent}import re\n",
                f"{indent}due_date_text = task_data['due_date']\n",
                f"{indent}due_date_iso = None\n",
                f"{indent}\n",
                f"{indent}if due_date_text:\n",
                f"{indent}    due_date_lower = due_date_text.lower().strip()\n",
                f"{indent}    today = datetime.datetime.now()\n",
                f"{indent}    \n",
                f"{indent}    if due_date_lower in ['tomorrow', 'tmrw']:\n",
                f"{indent}        due_date_iso = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')\n",
                f"{indent}    elif due_date_lower == 'today':\n",
                f"{indent}        due_date_iso = today.strftime('%Y-%m-%d')\n",
                f"{indent}    elif due_date_lower == 'next week':\n",
                f"{indent}        due_date_iso = (today + datetime.timedelta(days=7)).strftime('%Y-%m-%d')\n",
                f"{indent}    elif re.match(r'\\d{{4}}-\\d{{2}}-\\d{{2}}', due_date_text):\n",
                f"{indent}        due_date_iso = due_date_text\n",
                f"{indent}    \n",
                f"{indent}if due_date_iso:\n",
                f"{indent}    properties['Due Date'] = {{\n",
                f"{indent}        'date': {{'start': due_date_iso}}\n",
                f"{indent}    }}\n"
            ]
            
            # Replace the old code (3 lines) with our new code
            lines[i:i+3] = replacement
            fixed = True
            break
    
    if not fixed:
        print("ERROR: Could not find the Due Date setting code to patch")
        return False
    
    # Write the fixed version back
    try:
        with open('/app/lyco_api.py', 'w') as f:
            f.writelines(lines)
        print("SUCCESS: Date parsing fix applied!")
        print("The following date formats will now work:")
        print("  - 'tomorrow' or 'tmrw' → next day")
        print("  - 'today' → current day")
        print("  - 'next week' → 7 days from now")
        print("  - 'YYYY-MM-DD' → exact date")
        return True
    except Exception as e:
        print(f"ERROR: Could not write file: {e}")
        return False

if __name__ == "__main__":
    if apply_date_parsing_fix():
        print("\nNext steps:")
        print("1. Exit this container: exit")
        print("2. Restart Yanay: docker restart demestihas-yanay")
        print("3. Test with: 'Buy groceries tomorrow'")
        sys.exit(0)
    else:
        sys.exit(1)
