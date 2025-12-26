#!/usr/bin/env python3
"""
Self-Adapting Notion Schema Adapter
Intelligently maps expected Eisenhower properties to actual database schema
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from notion_client import Client
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PropertyMapping:
    """Maps an expected property to actual database property"""
    actual_name: str
    actual_type: str
    expected_type: str
    transformation_notes: str = ""

class NotionSchemaAdapter:
    """Self-adapting Notion database integration"""
    
    # Expected properties the Eisenhower bot wants to use
    EXPECTED_PROPERTIES = {
        'title': {
            'aliases': ['Name', 'Title', 'Task', 'Task Name'], 
            'type': 'title',
            'required': True
        },
        'status': {
            'aliases': ['Status', 'State', 'Progress', 'Complete'], 
            'type': ['select', 'checkbox'],
            'required': False
        },
        'urgency': {
            'aliases': ['Urgency', 'Urgent', 'Is Urgent'], 
            'type': ['select', 'checkbox', 'number'],
            'required': False
        },
        'importance': {
            'aliases': ['Importance', 'Important', 'Is Important'], 
            'type': ['select', 'checkbox', 'number'],
            'required': False
        },
        'assigned_to': {
            'aliases': ['Assigned To', 'Assignee', 'Owner', 'Assigned'], 
            'type': ['people', 'select'],
            'required': False
        },
        'quadrant': {
            'aliases': ['Quadrant', 'Priority', 'Eisenhower Quadrant', 'Eisenhower'], 
            'type': 'select',
            'required': False
        },
        'tags': {
            'aliases': ['Tags', 'Labels', 'Categories', 'Context/Tags', 'Context'], 
            'type': ['multi_select', 'select'],
            'required': False
        },
        'description': {
            'aliases': ['Description', 'Notes', 'Details', 'Note'], 
            'type': 'rich_text',
            'required': False
        },
        'due_date': {
            'aliases': ['Due Date', 'Due', 'Deadline'], 
            'type': 'date',
            'required': False
        }
    }
    
    def __init__(self, notion_client: Client, database_id: str):
        self.notion = notion_client
        self.database_id = database_id
        self._cached_schema = None
        self._cached_mapping = None
        self._cache_time = None
        self._cache_ttl = 3600  # 1 hour
        
    def discover_schema(self) -> Dict[str, Any]:
        """Fetch and cache the actual database schema"""
        
        # Check cache first
        if (self._cached_schema and self._cache_time and 
            (datetime.now() - self._cache_time).seconds < self._cache_ttl):
            return self._cached_schema
        
        try:
            database = self.notion.databases.retrieve(self.database_id)
            self._cached_schema = database.get('properties', {})
            self._cache_time = datetime.now()
            
            logger.info(f"Discovered {len(self._cached_schema)} properties in database")
            return self._cached_schema
            
        except Exception as e:
            logger.error(f"Failed to discover schema: {e}")
            # Return empty dict to allow graceful degradation
            return {}
    
    def build_intelligent_mapping(self) -> Dict[str, PropertyMapping]:
        """Create smart mapping between expected and actual properties"""
        
        if self._cached_mapping and self._cache_time and \
           (datetime.now() - self._cache_time).seconds < self._cache_ttl:
            return self._cached_mapping
        
        actual_schema = self.discover_schema()
        if not actual_schema:
            logger.warning("No schema discovered, using minimal mapping")
            return {}
        
        mappings = {}
        
        for expected_prop, config in self.EXPECTED_PROPERTIES.items():
            aliases = config['aliases']
            expected_type = config['type']
            
            # Try exact matches first
            for alias in aliases:
                if alias in actual_schema:
                    actual_prop = actual_schema[alias]
                    actual_type = actual_prop['type']
                    
                    mappings[expected_prop] = PropertyMapping(
                        actual_name=alias,
                        actual_type=actual_type,
                        expected_type=expected_type,
                        transformation_notes=f"Exact match: {alias}"
                    )
                    logger.info(f"✅ {expected_prop} -> {alias} ({actual_type})")
                    break
            else:
                # Try fuzzy/partial matches
                for prop_name, prop_info in actual_schema.items():
                    prop_type = prop_info['type']
                    
                    # Check if property name contains any alias or vice versa
                    for alias in aliases:
                        if (alias.lower() in prop_name.lower() or 
                            prop_name.lower() in alias.lower()):
                            
                            mappings[expected_prop] = PropertyMapping(
                                actual_name=prop_name,
                                actual_type=prop_type,
                                expected_type=expected_type,
                                transformation_notes=f"Partial match: {prop_name} ~ {alias}"
                            )
                            logger.info(f"🔶 {expected_prop} -> {prop_name} ({prop_type}) [partial]")
                            break
                    if expected_prop in mappings:
                        break
                else:
                    logger.warning(f"❌ {expected_prop} -> NOT FOUND")
        
        self._cached_mapping = mappings
        return mappings
    
    def adapt_task_for_notion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert task data to match actual database schema"""
        
        mappings = self.build_intelligent_mapping()
        if not mappings:
            # Fallback: try to save with just title if we find it
            return self._create_minimal_task(task_data)
        
        adapted_properties = {}
        
        for expected_prop, value in task_data.items():
            if value is None or value == "":
                continue
                
            if expected_prop not in mappings:
                logger.debug(f"Skipping unmapped property: {expected_prop}")
                continue
            
            mapping = mappings[expected_prop]
            
            try:
                adapted_value = self._transform_property_value(
                    value, expected_prop, mapping
                )
                if adapted_value:
                    adapted_properties[mapping.actual_name] = adapted_value
                    
            except Exception as e:
                logger.warning(f"Failed to transform {expected_prop}: {e}")
                continue
        
        # Ensure we have at least a title
        if not any(prop for prop in adapted_properties.values() 
                  if isinstance(prop, dict) and 'title' in prop):
            adapted_properties.update(self._create_minimal_task(task_data))
        
        # Add metadata
        adapted_properties = self._add_metadata(adapted_properties)
        
        return adapted_properties
    
    def _transform_property_value(self, value: Any, expected_prop: str, 
                                mapping: PropertyMapping) -> Optional[Dict[str, Any]]:
        """Transform a value to match the actual property type"""
        
        actual_type = mapping.actual_type
        
        # Title property
        if actual_type == 'title':
            return {"title": [{"text": {"content": str(value)[:2000]}}]}
        
        # Rich text property  
        elif actual_type == 'rich_text':
            return {"rich_text": [{"text": {"content": str(value)[:2000]}}]}
        
        # Date property
        elif actual_type == 'date':
            if isinstance(value, str) and value:
                return {"date": {"start": value}}
        
        # Select property
        elif actual_type == 'select':
            if expected_prop == 'quadrant':
                return self._map_quadrant_to_eisenhower(value)
            elif expected_prop == 'status':
                return self._map_status_to_complete(value)
            else:
                return {"select": {"name": str(value)}}
        
        # Multi-select property
        elif actual_type == 'multi_select':
            if isinstance(value, list):
                return {"multi_select": [{"name": str(tag)} for tag in value if tag]}
            elif isinstance(value, str):
                # Split on common delimiters
                tags = [tag.strip() for tag in value.replace(',', ' ').split() if tag.strip()]
                return {"multi_select": [{"name": tag} for tag in tags]}
        
        # People property
        elif actual_type == 'people':
            # For now, skip people properties as they require user IDs
            logger.debug(f"Skipping people property {mapping.actual_name} - requires user IDs")
            return None
        
        # Checkbox property
        elif actual_type == 'checkbox':
            if expected_prop in ['status', 'urgency', 'importance']:
                # Convert various formats to boolean
                if isinstance(value, bool):
                    return {"checkbox": value}
                elif isinstance(value, str):
                    return {"checkbox": value.lower() in ['true', 'yes', 'complete', 'done', '1']}
                elif isinstance(value, (int, float)):
                    return {"checkbox": value > 0}
        
        # Number property
        elif actual_type == 'number':
            try:
                return {"number": float(value)}
            except (ValueError, TypeError):
                return None
        
        logger.debug(f"No transformation for {expected_prop} -> {mapping.actual_name} ({actual_type})")
        return None
    
    def _map_quadrant_to_eisenhower(self, quadrant_value: Any) -> Dict[str, Any]:
        """Map Eisenhower quadrant to the actual Eisenhower field options"""
        
        # Get actual options from schema
        schema = self.discover_schema()
        eisenhower_prop = schema.get('Eisenhower', {})
        options = eisenhower_prop.get('select', {}).get('options', [])
        option_names = [opt['name'] for opt in options]
        
        # Map quadrant numbers/names to available options
        quadrant_mappings = {
            1: ["🔥 Do Now"],
            2: ["📅 Schedule"], 
            3: ["👥 Delegate", "🟪 Delegate"],
            4: ["🗄️ Someday/Maybe", "🧠 Brain Dump"]
        }
        
        # Try to map the value
        if isinstance(quadrant_value, int) and quadrant_value in quadrant_mappings:
            for option_name in quadrant_mappings[quadrant_value]:
                if option_name in option_names:
                    return {"select": {"name": option_name}}
        
        # Try string matching
        quadrant_str = str(quadrant_value).lower()
        for option_name in option_names:
            option_lower = option_name.lower()
            if any(keyword in option_lower for keyword in ['do now', 'urgent', 'fire']) and \
               any(keyword in quadrant_str for keyword in ['1', 'urgent', 'first', 'do']):
                return {"select": {"name": option_name}}
            elif any(keyword in option_lower for keyword in ['schedule', 'calendar']) and \
                 any(keyword in quadrant_str for keyword in ['2', 'schedule', 'plan']):
                return {"select": {"name": option_name}}
            elif any(keyword in option_lower for keyword in ['delegate']) and \
                 any(keyword in quadrant_str for keyword in ['3', 'delegate']):
                return {"select": {"name": option_name}}
            elif any(keyword in option_lower for keyword in ['someday', 'maybe', 'brain']) and \
                 any(keyword in quadrant_str for keyword in ['4', 'someday', 'maybe', 'later']):
                return {"select": {"name": option_name}}
        
        # Default to first available option
        if option_names:
            return {"select": {"name": option_names[0]}}
        
        return None
    
    def _map_status_to_complete(self, status_value: Any) -> Optional[Dict[str, Any]]:
        """Map status to Complete checkbox if that's what's available"""
        
        # Check if we actually have a Complete checkbox
        schema = self.discover_schema()
        if 'Complete' in schema and schema['Complete']['type'] == 'checkbox':
            # Map status to checkbox
            status_str = str(status_value).lower()
            is_complete = status_str in ['complete', 'done', 'finished', 'true', '1']
            return {"checkbox": is_complete}
        
        # Otherwise treat as regular select
        return {"select": {"name": str(status_value)}}
    
    def _create_minimal_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create minimal task with just title if all else fails"""
        
        title = task_data.get('title', 'Untitled Task')
        schema = self.discover_schema()
        
        # Find the title property
        for prop_name, prop_info in schema.items():
            if prop_info['type'] == 'title':
                return {prop_name: {"title": [{"text": {"content": str(title)[:2000]}}]}}
        
        # Last resort: use 'Name' or 'Title'
        return {"Name": {"title": [{"text": {"content": str(title)[:2000]}}]}}
    
    def _add_metadata(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata properties like Source, RecordType if they exist"""
        
        schema = self.discover_schema()
        
        # Set Source to Telegram if available
        if 'Source' in schema:
            properties['Source'] = {"select": {"name": "Telegram"}}
        
        # Set RecordType to Task if available
        if 'RecordType' in schema:
            properties['RecordType'] = {"select": {"name": "Task"}}
        
        return properties
    
    def get_mapping_report(self) -> str:
        """Return a human-readable report of property mappings"""
        
        mappings = self.build_intelligent_mapping()
        
        report = ["🔗 NOTION SCHEMA MAPPING REPORT", "=" * 40]
        
        if not mappings:
            report.append("❌ No mappings discovered - using fallback mode")
            return "\n".join(report)
        
        for expected, mapping in mappings.items():
            status = "✅" if mapping.transformation_notes.startswith("Exact") else "🔶"
            report.append(f"{status} {expected} -> {mapping.actual_name} ({mapping.actual_type})")
            if mapping.transformation_notes:
                report.append(f"   Note: {mapping.transformation_notes}")
        
        missing = []
        for expected in self.EXPECTED_PROPERTIES:
            if expected not in mappings and self.EXPECTED_PROPERTIES[expected]['required']:
                missing.append(expected)
        
        if missing:
            report.append("\n❌ MISSING REQUIRED PROPERTIES:")
            for prop in missing:
                report.append(f"   • {prop}")
        
        return "\n".join(report)
    
    def test_mapping(self, sample_task: Dict[str, Any]) -> Dict[str, Any]:
        """Test the mapping with a sample task"""
        
        try:
            adapted = self.adapt_task_for_notion(sample_task)
            logger.info("✅ Sample task adaptation successful")
            logger.info(f"Input: {sample_task}")
            logger.info(f"Output: {list(adapted.keys())}")
            return adapted
        except Exception as e:
            logger.error(f"❌ Sample task adaptation failed: {e}")
            return {}


# Factory function for easy integration
def create_notion_adapter(notion_client: Client, database_id: str) -> NotionSchemaAdapter:
    """Create and validate a NotionSchemaAdapter"""
    
    adapter = NotionSchemaAdapter(notion_client, database_id)
    
    # Test the connection
    try:
        schema = adapter.discover_schema()
        if not schema:
            logger.warning("⚠️ No schema properties discovered - adapter may not work correctly")
        else:
            logger.info(f"✅ Adapter created successfully with {len(schema)} properties")
    except Exception as e:
        logger.error(f"❌ Failed to create adapter: {e}")
        
    return adapter