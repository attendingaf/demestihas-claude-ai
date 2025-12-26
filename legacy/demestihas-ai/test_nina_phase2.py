#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/root/demestihas-ai')

from nina import process_schedule_command

async def test_nina_phase2():
    print("\n🧪 Testing Nina Phase 2 (Calendar Integration)\n")
    
    # Test calendar commands
    commands = [
        "Sync Viola's schedule to calendar",
        "Check calendar conflicts for Friday",
        "Viola has Friday off",
        "What's Viola's schedule this week?",
        "Need coverage Saturday evening for date night"
    ]
    
    for cmd in commands:
        print(f"\n📝 Command: '{cmd}'")
        result = await process_schedule_command(cmd, "Test User")
        print(f"✅ Result: {result.get('message', 'No message')[:200]}")
    
    print("\n✅ Nina Phase 2 test complete!")

if __name__ == '__main__':
    asyncio.run(test_nina_phase2())
