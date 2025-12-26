#!/usr/bin/env python3
"""
Safely integrate Pluma routing into existing yanay.py
"""

import re
import os

def integrate_pluma_into_yanay():
    # Read the current yanay.py
    with open('yanay.py', 'r') as f:
        yanay_content = f.read()
    
    # Read the Pluma additions
    with open('yanay_pluma_additions.py', 'r') as f:
        pluma_additions = f.read()
    
    # Extract the PlumaIntegration class from additions
    pluma_class_match = re.search(r'class PlumaIntegration:.*?(?=\n\n|\n(?=class|\nif|\n$|\Z))', pluma_additions, re.DOTALL)
    if not pluma_class_match:
        print("❌ Could not extract PlumaIntegration class")
        return False
    
    pluma_class = pluma_class_match.group(0)
    
    # Check if PlumaIntegration is already in yanay.py
    if 'class PlumaIntegration' in yanay_content:
        print("⚠️  PlumaIntegration already exists in yanay.py")
        return True
    
    # Find the right place to insert PlumaIntegration (before the main YanayOrchestrator class)
    insert_position = yanay_content.find('class YanayOrchestrator')
    if insert_position == -1:
        # Try alternative class names
        insert_position = yanay_content.find('class Yanay')
        
    if insert_position == -1:
        print("❌ Could not find main class in yanay.py")
        return False
    
    # Insert PlumaIntegration class
    enhanced_yanay = (
        yanay_content[:insert_position] +
        pluma_class + '\n\n' +
        yanay_content[insert_position:]
    )
    
    # Look for the process_message method and add Pluma routing
    process_message_pattern = r'(async def process_message\(self, message: str, user_id: str\) -> str:.*?)(return.*?)(?=\n    async def|\n    def|\nclass|\n$|\Z)'
    
    def add_pluma_routing(match):
        method_start = match.group(1)
        return_statement = match.group(2)
        
        # Add Pluma routing before the return statement
        pluma_routing = '''
        # Check for Pluma routing (email/meeting processing)
        pluma_integration = PlumaIntegration(self.redis_client, self.logger)
        if pluma_integration.should_route_to_pluma(message):
            return await pluma_integration.route_to_pluma(message, user_id)
        
        '''
        
        return method_start + pluma_routing + return_statement
    
    enhanced_yanay = re.sub(process_message_pattern, add_pluma_routing, enhanced_yanay, flags=re.DOTALL)
    
    # Write the enhanced yanay.py
    with open('yanay_enhanced.py', 'w') as f:
        f.write(enhanced_yanay)
    
    # Replace the original
    os.replace('yanay.py', 'yanay_backup_pre_pluma.py')
    os.replace('yanay_enhanced.py', 'yanay.py')
    
    print("✅ Pluma integration added to yanay.py")
    return True

if __name__ == '__main__':
    print("🔧 Integrating Pluma into Yanay.ai...")
    
    if not os.path.exists('yanay.py'):
        print("❌ yanay.py not found")
        exit(1)
    
    if not os.path.exists('yanay_pluma_additions.py'):
        print("❌ yanay_pluma_additions.py not found")  
        exit(1)
    
    if integrate_pluma_into_yanay():
        print("🎉 Pluma integration complete!")
        print("\nNext steps:")
        print("1. Rebuild Yanay container: docker-compose build yanay")
        print("2. Restart services: docker-compose restart yanay")
        print("3. Deploy Pluma: docker-compose up -d pluma")
        print("4. Test integration via @LycurgusBot")
    else:
        print("❌ Integration failed")
        exit(1)

