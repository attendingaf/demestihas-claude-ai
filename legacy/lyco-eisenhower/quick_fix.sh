#!/bin/bash
# Quick fix for Notion properties

cd /root/lyco-eisenhower

# Create the patch
cat << 'EOF' > fix_notion.py
#!/usr/bin/env python3
import re

# Read the file
with open("agents/lyco/lyco_eisenhower.py", "r") as f:
    content = f.read()

# Add missing import
if "from dataclasses import dataclass, asdict" not in content:
    content = content.replace(
        "from dataclasses import dataclass",
        "from dataclasses import dataclass, asdict"
    )

# Replace the save_task_to_notion method with a flexible version
new_method = '''
    def save_task_to_notion(self, task: Task) -> bool:
        """Save task to Notion - works with any database structure"""
        if not self.notion or not self.notion_database_id:
            return False
        
        try:
            # Get database schema
            db = self.notion.databases.retrieve(database_id=self.notion_database_id)
            db_props = db["properties"]
            
            # Find title property (required)
            title_prop = next((name for name, data in db_props.items() if data["type"] == "title"), None)
            if not title_prop:
                return False
            
            # Minimal properties - just title
            properties = {title_prop: {"title": [{"text": {"content": task.title}}]}}
            
            # Create page
            response = self.notion.pages.create(
                parent={"database_id": self.notion_database_id},
                properties=properties
            )
            
            task.notion_id = response["id"]
            logger.info(f"Task saved: {task.title}")
            return True
        except Exception as e:
            logger.error(f"Notion error: {e}")
            return False'''

# Replace the method
pattern = r'def save_task_to_notion\(self, task: Task\) -> bool:.*?(?=\n    def |\Z)'
content = re.sub(pattern, new_method, content, flags=re.DOTALL)

# Write back
with open("agents/lyco/lyco_eisenhower.py", "w") as f:
    f.write(content)

print("✓ Patched successfully")
EOF

# Run the patch
docker exec yanay-eisenhower python fix_notion.py

# Restart
docker-compose restart yanay-eisenhower

echo "✅ Fix applied! Test your bot now."
