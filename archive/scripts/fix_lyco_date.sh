#!/bin/bash
# Script to fix the lyco_api.py date parsing issue
# Run this from your LOCAL Mac terminal

echo "🔧 Fixing lyco_api.py date parsing issue..."
echo ""
echo "Step 1: Downloading current file from VPS..."
scp root@178.156.170.161:/root/demestihas-ai/lyco_api.py ~/Projects/demestihas-ai/lyco_api_broken.py

echo "Step 2: Applying fix locally..."
python3 << 'EOF'
import re
import sys

print("Reading broken file...")
with open('/Users/menedemestihas/Projects/demestihas-ai/lyco_api_broken.py', 'r') as f:
    content = f.read()

print("Applying date parsing fix...")

# Find the due date section and replace it
# We need to fix the section that handles due_date

# Pattern to find the problematic section
pattern = r"(\s+)if task_data\.get\('due_date'\):.*?properties\['Due Date'\] = \{.*?\}.*?\}"

# The proper replacement
replacement = r'''        if task_data.get('due_date'):
            # Parse relative dates to ISO format
            import datetime
            import re
            
            due_text = task_data['due_date'].lower().strip()
            due_iso = None
            today = datetime.datetime.now()
            
            # Parse common relative dates
            if due_text in ['tomorrow', 'tmrw']:
                due_iso = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            elif due_text == 'today':
                due_iso = today.strftime('%Y-%m-%d')
            elif due_text == 'next week':
                due_iso = (today + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', task_data['due_date']):
                due_iso = task_data['due_date']
            else:
                # Default to original if can't parse
                due_iso = task_data['due_date']
            
            # Add Due Date property
            if due_iso:
                properties['Due Date'] = {
                    'date': {'start': due_iso}
                }'''

# Apply the fix
content_fixed = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Check if we made a change
if content_fixed == content:
    # Try a different approach - look for lines
    lines = content.split('\n')
    new_lines = []
    i = 0
    fixed = False
    
    while i < len(lines):
        if "if task_data.get('due_date'):" in lines[i] and not fixed:
            # Found the section, replace it
            indent_count = len(lines[i]) - len(lines[i].lstrip())
            indent = ' ' * indent_count
            
            # Skip the old implementation
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('#') and 'notion_data' not in lines[j]:
                if 'properties[' in lines[j] and 'Due Date' in lines[j]:
                    j += 3  # Skip the Due Date block
                    break
                j += 1
            
            # Add the fixed version
            for line in replacement.split('\n'):
                new_lines.append(line)
            
            i = j
            fixed = True
        else:
            new_lines.append(lines[i])
            i += 1
    
    content_fixed = '\n'.join(new_lines)

# Save the fixed version
print("Saving fixed version...")
with open('/Users/menedemestihas/Projects/demestihas-ai/lyco_api_fixed.py', 'w') as f:
    f.write(content_fixed)

print("✅ Fixed file created: lyco_api_fixed.py")
EOF

echo ""
echo "Step 3: Uploading fixed file to VPS..."
scp ~/Projects/demestihas-ai/lyco_api_fixed.py root@178.156.170.161:/root/demestihas-ai/lyco_api.py

echo ""
echo "Step 4: Restarting container..."
ssh root@178.156.170.161 "docker restart demestihas-yanay && sleep 5 && docker logs demestihas-yanay --tail 5"

echo ""
echo "✅ Fix complete! Test by sending 'Buy groceries tomorrow' to the bot"
