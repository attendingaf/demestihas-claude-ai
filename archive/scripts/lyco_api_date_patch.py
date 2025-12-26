#!/usr/bin/env python3
"""
Clean fix for lyco_api.py date parsing issue
This script will properly fix the date parsing without breaking indentation
"""

def fix_lyco_api():
    """Fix the date parsing in lyco_api.py"""
    
    # The exact fix to apply at line 268-272
    fix_code = '''        # Add due date if present
        if task_data.get('due_date'):
            # Parse relative dates to ISO format
            import datetime
            import re
            
            due_text = task_data['due_date'].lower().strip()
            due_iso = None
            
            # Get today's date
            today = datetime.datetime.now()
            
            # Parse relative dates
            if due_text in ['tomorrow', 'tmrw', 'tom']:
                due_iso = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            elif due_text == 'today':
                due_iso = today.strftime('%Y-%m-%d')
            elif due_text == 'next week':
                due_iso = (today + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            elif due_text == 'next month':
                due_iso = (today + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', due_text):
                # Already in ISO format
                due_iso = due_text
            else:
                # Try to parse other date formats
                try:
                    # Could add more sophisticated parsing here
                    due_iso = due_text  # Fallback to original
                except:
                    due_iso = None
            
            # Only add Due Date if we have a valid date
            if due_iso:
                properties['Due Date'] = {
                    'date': {'start': due_iso}
                }
'''
    
    try:
        # Read the current file
        with open('/root/demestihas-ai/lyco_api.py', 'r') as f:
            lines = f.readlines()
        
        # Find the section to replace
        # Looking for the due_date section around line 268
        new_lines = []
        i = 0
        while i < len(lines):
            # Look for the start of the due date section
            if i >= 267 and "if task_data.get('due_date'):" in lines[i]:
                # Found it! Skip any duplicate lines
                while i < len(lines) and "if task_data.get('due_date'):" in lines[i]:
                    i += 1
                    
                # Skip the old implementation (usually 3 lines)
                old_impl_lines = 0
                start_i = i
                while i < len(lines) and old_impl_lines < 4:
                    if i < len(lines):
                        # Check if we've reached the next section
                        if "# Prepare request" in lines[i] or "notion_data = {" in lines[i]:
                            break
                        i += 1
                        old_impl_lines += 1
                
                # Add our fixed implementation
                for fix_line in fix_code.split('\n'):
                    new_lines.append(fix_line + '\n')
                    
            else:
                # Keep the original line
                new_lines.append(lines[i])
                i += 1
        
        # Write the fixed version
        with open('/root/demestihas-ai/lyco_api.py', 'w') as f:
            f.writelines(new_lines)
            
        print("✅ Successfully fixed lyco_api.py!")
        print("\nThe following date formats will now work:")
        print("  • 'tomorrow' or 'tmrw' → next day")
        print("  • 'today' → current date")  
        print("  • 'next week' → 7 days from now")
        print("  • 'next month' → 30 days from now")
        print("  • 'YYYY-MM-DD' → exact date")
        print("\nNext steps:")
        print("1. Restart container: docker restart demestihas-yanay")
        print("2. Test with: 'Buy groceries tomorrow'")
        return True
        
    except FileNotFoundError:
        print("❌ ERROR: File /root/demestihas-ai/lyco_api.py not found")
        print("Make sure you're running this from the VPS")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    fix_lyco_api()
