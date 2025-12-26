#!/usr/bin/env python3
"""
Demestihas AI System Status - One command to rule them all
Usage: python status.py
"""

import subprocess
import json
from datetime import datetime

def check_system():
    """Everything you need to know in 10 seconds"""
    
    print("\n🤖 DEMESTIHAS AI STATUS")
    print("=" * 40)
    
    # 1. Are containers running?
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                container = json.loads(line)
                if 'demestihas' in container.get('Names', '').lower():
                    status = "✅" if 'Up' in container.get('Status', '') else "❌"
                    containers.append(f"{status} {container['Names']}")
        
        print("\nContainers:")
        for c in containers:
            print(f"  {c}")
            
        if not containers:
            print("  ❌ No Demestihas containers found")
            print("  Fix: cd ~/Projects/demestihas-ai && docker-compose up -d")
            
    except Exception as e:
        print(f"  ❌ Docker not accessible: {e}")
        
    # 2. Last activity
    print("\nLast Activity:")
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "1", "--timestamps", "demestihas-ai"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  No recent activity")
    except:
        print(f"  Cannot read logs")
        
    # 3. Quick health check
    print("\nQuick Actions:")
    print("  • Restart all: docker-compose restart")
    print("  • View logs:   docker logs demestihas-ai --tail 20")
    print("  • Full reset:  docker-compose down && docker-compose up -d")
    
    print("\n" + "=" * 40)
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    check_system()
