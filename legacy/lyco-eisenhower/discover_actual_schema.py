#!/usr/bin/env python3
"""
Discover the actual schema of the Notion database
"""

import os
import json
from notion_client import Client

def discover_notion_schema():
    """Discover the actual properties in the Notion database"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    notion_api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_TASKS_DATABASE_ID")
    
    if not notion_api_key or not database_id:
        print("❌ Missing NOTION_API_KEY or NOTION_TASKS_DATABASE_ID")
        return
    
    notion = Client(auth=notion_api_key)
    
    try:
        # Get database info
        print(f"🔍 Discovering schema for database: {database_id}")
        database = notion.databases.retrieve(database_id)
        
        print(f"📋 Database Title: {database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
        print(f"🆔 Database ID: {database_id}")
        print()
        
        # Analyze properties
        properties = database.get('properties', {})
        print(f"📊 Found {len(properties)} properties:")
        print("=" * 60)
        
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"🔹 {prop_name}")
            print(f"   Type: {prop_type}")
            
            # Show additional details based on type
            if prop_type == 'select':
                options = prop_info.get('select', {}).get('options', [])
                if options:
                    option_names = [opt.get('name', '') for opt in options]
                    print(f"   Options: {option_names}")
            elif prop_type == 'multi_select':
                options = prop_info.get('multi_select', {}).get('options', [])
                if options:
                    option_names = [opt.get('name', '') for opt in options]
                    print(f"   Options: {option_names}")
            elif prop_type == 'people':
                print("   Type: People (user references)")
            elif prop_type == 'number':
                format_info = prop_info.get('number', {}).get('format', 'number')
                print(f"   Format: {format_info}")
            elif prop_type == 'date':
                print("   Type: Date")
            elif prop_type == 'rich_text':
                print("   Type: Rich text")
            elif prop_type == 'title':
                print("   Type: Title (primary)")
            
            print()
        
        # Try to get a sample record to see actual data
        print("📄 Sample record analysis:")
        print("=" * 60)
        
        try:
            response = notion.databases.query(database_id, page_size=1)
            if response['results']:
                sample = response['results'][0]
                sample_props = sample.get('properties', {})
                
                for prop_name, prop_data in sample_props.items():
                    prop_type = prop_data.get('type', 'unknown')
                    print(f"🔸 {prop_name} ({prop_type}):")
                    
                    # Show sample data
                    if prop_type == 'title' and prop_data.get('title'):
                        title_text = prop_data['title'][0].get('text', {}).get('content', '')
                        print(f"   Sample: \"{title_text}\"")
                    elif prop_type == 'select' and prop_data.get('select'):
                        select_name = prop_data['select'].get('name', '')
                        print(f"   Sample: \"{select_name}\"")
                    elif prop_type == 'number' and prop_data.get('number') is not None:
                        number_val = prop_data['number']
                        print(f"   Sample: {number_val}")
                    elif prop_type == 'multi_select' and prop_data.get('multi_select'):
                        multi_names = [item.get('name', '') for item in prop_data['multi_select']]
                        print(f"   Sample: {multi_names}")
                    elif prop_type == 'date' and prop_data.get('date'):
                        date_val = prop_data['date'].get('start', '')
                        print(f"   Sample: \"{date_val}\"")
                    elif prop_type == 'rich_text' and prop_data.get('rich_text'):
                        rich_text = prop_data['rich_text'][0].get('text', {}).get('content', '') if prop_data['rich_text'] else ''
                        print(f"   Sample: \"{rich_text}\"")
                    elif prop_type == 'people' and prop_data.get('people'):
                        people_names = [person.get('name', person.get('id', '')) for person in prop_data['people']]
                        print(f"   Sample: {people_names}")
                    else:
                        print(f"   Sample: (empty or unsupported type)")
                    print()
            else:
                print("No records found in database")
        
        except Exception as e:
            print(f"❌ Could not fetch sample record: {e}")
        
        # Generate mapping suggestions
        print("\n🧠 INTELLIGENT MAPPING SUGGESTIONS:")
        print("=" * 60)
        
        expected_props = {
            'title': ['Title', 'Task', 'Name', 'Task Name'],
            'status': ['Status', 'State', 'Progress'],
            'urgency': ['Urgency', 'Urgent', 'Is Urgent'],
            'importance': ['Importance', 'Important', 'Is Important'],
            'assigned_to': ['Assigned To', 'Assignee', 'Owner', 'Assigned'],
            'quadrant': ['Quadrant', 'Priority', 'Eisenhower Quadrant'],
            'tags': ['Tags', 'Labels', 'Categories'],
            'description': ['Description', 'Notes', 'Details'],
            'due_date': ['Due Date', 'Due', 'Deadline']
        }
        
        found_mappings = {}
        for expected, aliases in expected_props.items():
            for alias in aliases:
                if alias in properties:
                    found_mappings[expected] = {
                        'actual_name': alias,
                        'type': properties[alias]['type']
                    }
                    print(f"✅ {expected} -> {alias} ({properties[alias]['type']})")
                    break
            else:
                # Try partial matching
                for prop_name in properties:
                    for alias in aliases:
                        if alias.lower() in prop_name.lower() or prop_name.lower() in alias.lower():
                            found_mappings[expected] = {
                                'actual_name': prop_name,
                                'type': properties[prop_name]['type']
                            }
                            print(f"🔶 {expected} -> {prop_name} ({properties[prop_name]['type']}) [partial match]")
                            break
                    if expected in found_mappings:
                        break
                else:
                    print(f"❌ {expected} -> NOT FOUND")
        
        # Save mapping to file
        mapping_file = '/root/lyco-eisenhower/discovered_mapping.json'
        with open(mapping_file, 'w') as f:
            json.dump({
                'database_info': {
                    'id': database_id,
                    'title': database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')
                },
                'properties': properties,
                'suggested_mappings': found_mappings
            }, f, indent=2)
        
        print(f"\n💾 Full schema saved to: {mapping_file}")
        
    except Exception as e:
        print(f"❌ Error discovering schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    discover_notion_schema()