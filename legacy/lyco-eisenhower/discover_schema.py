#!/usr/bin/env python3
"""Discover Notion database schema and create intelligent adapter."""
import os
import json
from notion_client import Client
from typing import Dict, Any, Optional

class NotionSchemaAdapter:
    def __init__(self, notion_client: Client, database_id: str):
        self.client = notion_client
        self.database_id = database_id
        self.schema = self.discover_schema()
        self.property_map = self.build_mapping()

    def discover_schema(self) -> Dict[str, Any]:
        """Fetch actual database properties from Notion."""
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            properties = {}
            for prop_name, prop_data in database['properties'].items():
                properties[prop_name] = {
                    'type': prop_data['type'],
                    'name': prop_name
                }
                # Store additional metadata for specific types
                if prop_data['type'] == 'select' and 'select' in prop_data:
                    properties[prop_name]['options'] = [
                        opt['name'] for opt in prop_data['select'].get('options', [])
                    ]
                elif prop_data['type'] == 'multi_select' and 'multi_select' in prop_data:
                    properties[prop_name]['options'] = [
                        opt['name'] for opt in prop_data['multi_select'].get('options', [])
                    ]
            return properties
        except Exception as e:
            print(f"Error discovering schema: {e}")
            return {}

    def build_mapping(self) -> Dict[str, str]:
        """Build intelligent mapping from expected to actual properties."""
        mapping = {}
        actual_props_lower = {k.lower(): k for k in self.schema.keys()}
        
        # Expected properties from Eisenhower bot
        expected_mappings = {
            'Title': ['title', 'name', 'task', 'summary', 'description'],
            'Status': ['status', 'state', 'progress', 'stage'],
            'Urgency': ['urgency', 'urgent', 'priority'],
            'Importance': ['importance', 'important', 'impact'],
            'Assigned To': ['assigned to', 'assignee', 'owner', 'responsible', 'assigned'],
            'Quadrant': ['quadrant', 'category', 'type', 'classification'],
            'Tags': ['tags', 'labels', 'categories']
        }
        
        for expected, candidates in expected_mappings.items():
            for candidate in candidates:
                if candidate in actual_props_lower:
                    mapping[expected] = actual_props_lower[candidate]
                    break
        
        return mapping

    def adapt_task_properties(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert task properties to match actual database schema."""
        adapted = {}
        
        for expected_prop, value in task_data.items():
            if expected_prop in self.property_map:
                actual_prop = self.property_map[expected_prop]
                prop_type = self.schema[actual_prop]['type']
                
                # Handle type conversions
                if prop_type == 'title':
                    adapted[actual_prop] = {'title': [{'text': {'content': str(value)}}]}
                elif prop_type == 'rich_text':
                    adapted[actual_prop] = {'rich_text': [{'text': {'content': str(value)}}]}
                elif prop_type == 'select':
                    # Check if value exists in options
                    options = self.schema[actual_prop].get('options', [])
                    if not options or str(value) in options:
                        adapted[actual_prop] = {'select': {'name': str(value)}}
                elif prop_type == 'multi_select':
                    if isinstance(value, list):
                        adapted[actual_prop] = {'multi_select': [{'name': str(v)} for v in value]}
                    else:
                        adapted[actual_prop] = {'multi_select': [{'name': str(value)}]}
                elif prop_type == 'people':
                    # Skip people fields for now as they require user IDs
                    continue
                elif prop_type == 'checkbox':
                    adapted[actual_prop] = {'checkbox': bool(value)}
                elif prop_type == 'number':
                    try:
                        adapted[actual_prop] = {'number': float(value)}
                    except:
                        pass
                elif prop_type == 'url':
                    adapted[actual_prop] = {'url': str(value)}
                else:
                    # Try generic text fallback
                    print(f"Unknown type {prop_type} for {actual_prop}, skipping")
        
        # Ensure we have at least a title
        if not adapted:
            # Find first title property and use task description
            for prop_name, prop_info in self.schema.items():
                if prop_info['type'] == 'title':
                    adapted[prop_name] = {'title': [{'text': {'content': task_data.get('Title', 'New Task')}}]}
                    break
        
        return adapted

    def print_schema_report(self):
        """Print detailed schema discovery report."""
        print("\n" + "="*60)
        print("NOTION DATABASE SCHEMA DISCOVERY REPORT")
        print("="*60)
        print(f"Database ID: {self.database_id}")
        print(f"\nDiscovered {len(self.schema)} properties:")
        print("-"*40)
        
        for prop_name, prop_info in self.schema.items():
            print(f"  {prop_name}: {prop_info['type']}")
            if 'options' in prop_info:
                print(f"    Options: {', '.join(prop_info['options'])}")
        
        print("\n" + "="*60)
        print("PROPERTY MAPPING (Expected a Actual)")
        print("="*60)
        
        for expected, actual in self.property_map.items():
            print(f"  {expected} a {actual}")
        
        unmapped = [k for k in ['Title', 'Status', 'Urgency', 'Importance', 'Assigned To', 'Quadrant', 'Tags'] 
                   if k not in self.property_map]
        if unmapped:
            print("\nUnmapped properties (will be skipped):")
            for prop in unmapped:
                print(f"  a {prop}")
        
        print("\n" + "="*60)


def test_adapter():
    """Test the schema adapter with actual database."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    notion = Client(auth=os.getenv('NOTION_API_KEY'))
    database_id = os.getenv('NOTION_TASKS_DATABASE_ID')
    
    print(f"Testing with database: {database_id}")
    
    # Create adapter
    adapter = NotionSchemaAdapter(notion, database_id)
    adapter.print_schema_report()
    
    # Test task adaptation
    test_task = {
        'Title': 'Test Eisenhower Task',
        'Status': 'Todo',
        'Urgency': 'High',
        'Importance': 'High',
        'Quadrant': 'Q1: Do First',
        'Tags': ['test', 'eisenhower']
    }
    
    print("\nTest Task Adaptation:")
    print("-"*40)
    print("Input:", json.dumps(test_task, indent=2))
    
    adapted = adapter.adapt_task_properties(test_task)
    print("\nAdapted:", json.dumps(adapted, indent=2, default=str))
    
    # Try to create a test page
    print("\nAttempting to create test page...")
    try:
        response = notion.pages.create(
            parent={'database_id': database_id},
            properties=adapted
        )
        print(f"a Success! Created page with ID: {response['id']}")
        return adapter
    except Exception as e:
        print(f"a Failed: {e}")
        return None


if __name__ == '__main__':
    test_adapter()
