#!/usr/bin/env python3
"""
Direct fix for lyco_api.py - removes duplicates and fixes date parsing
Run this directly on the VPS in /root/demestihas-ai/
"""

print("🔧 Fixing lyco_api.py date parsing...")

# Read the file
with open('lyco_api.py', 'r') as f:
    lines = f.readlines()

# Remove any duplicate "if task_data.get('due_date'):" lines
cleaned_lines = []
last_line = ""
for line in lines:
    if "if task_data.get('due_date'):" in line and "if task_data.get('due_date'):" in last_line:
        continue  # Skip duplicate
    cleaned_lines.append(line)
    last_line = line

# Now fix the date parsing section
final_lines = []
i = 0
while i < len(cleaned_lines):
    if "if task_data.get('due_date'):" in cleaned_lines[i]:
        # Found the section to fix
        indent = ' ' * 8  # 8 spaces for proper indentation
        
        # Add the if statement
        final_lines.append(cleaned_lines[i])
        
        # Skip old implementation until we find notion_data or # Prepare
        i += 1
        while i < len(cleaned_lines):
            if "notion_data = {" in cleaned_lines[i] or "# Prepare request" in cleaned_lines[i]:
                break
            i += 1
        
        # Add our fixed implementation
        final_lines.append(f"{indent}    # Parse relative dates to ISO format\n")
        final_lines.append(f"{indent}    import datetime\n")
        final_lines.append(f"{indent}    import re\n")
        final_lines.append(f"{indent}    \n")
        final_lines.append(f"{indent}    due_text = task_data['due_date'].lower().strip()\n")
        final_lines.append(f"{indent}    today = datetime.datetime.now()\n")
        final_lines.append(f"{indent}    \n")
        final_lines.append(f"{indent}    if due_text in ['tomorrow', 'tmrw']:\n")
        final_lines.append(f"{indent}        due_iso = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')\n")
        final_lines.append(f"{indent}    elif due_text == 'today':\n")
        final_lines.append(f"{indent}        due_iso = today.strftime('%Y-%m-%d')\n")
        final_lines.append(f"{indent}    elif due_text == 'next week':\n")
        final_lines.append(f"{indent}        due_iso = (today + datetime.timedelta(days=7)).strftime('%Y-%m-%d')\n")
        final_lines.append(f"{indent}    elif re.match(r'^\\d{{4}}-\\d{{2}}-\\d{{2}}$', due_text):\n")
        final_lines.append(f"{indent}        due_iso = due_text\n")
        final_lines.append(f"{indent}    else:\n")
        final_lines.append(f"{indent}        due_iso = due_text  # Use as-is\n")
        final_lines.append(f"{indent}    \n")
        final_lines.append(f"{indent}    properties['Due Date'] = {{\n")
        final_lines.append(f"{indent}        'date': {{'start': due_iso}}\n")
        final_lines.append(f"{indent}    }}\n")
        
        # Continue with rest of file
        continue
    else:
        final_lines.append(cleaned_lines[i])
    i += 1

# Write the fixed file
with open('lyco_api.py', 'w') as f:
    f.writelines(final_lines)

print("✅ Fixed lyco_api.py!")
print("\nVerifying fix...")

# Verify no syntax errors
import subprocess
result = subprocess.run(['python3', '-m', 'py_compile', 'lyco_api.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("✅ No syntax errors found!")
    print("\nNext steps:")
    print("1. Restart container: docker restart demestihas-yanay")
    print("2. Check logs: docker logs demestihas-yanay --tail 10")
    print("3. Test with Telegram: 'Buy groceries tomorrow'")
else:
    print("❌ Syntax error found:")
    print(result.stderr)
