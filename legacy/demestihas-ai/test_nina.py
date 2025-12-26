#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/root/demestihas-ai')

from nina import NinaSchedulingAgent

async def test_nina():
    print("\n🧪 Testing Nina Scheduling Agent\n")
    
    # Initialize Nina
    nina = NinaSchedulingAgent()
    await nina.initialize()
    
    # Test 1: Parse dates
    print("1️⃣ Testing date parsing:")
    test_dates = ["Thursday", "tomorrow", "next week", "Friday afternoon"]
    for text in test_dates:
        date = nina.parse_date_from_text(text)
        print(f"   '{text}' → {date.strftime('%Y-%m-%d %A') if date else 'None'}")
    
    # Test 2: Parse times
    print("\n2️⃣ Testing time parsing:")
    test_times = ["3-5pm", "morning", "evening", "off", "7am-7pm"]
    for text in test_times:
        time = nina.parse_time_from_text(text)
        print(f"   '{text}' → {time}")
    
    # Test 3: Process commands
    print("\n3️⃣ Testing schedule commands:")
    commands = [
        "Viola has Thursday off",
        "Need coverage tomorrow 3-5pm",
        "What's Viola's schedule this week?",
        "Viola worked extra 3 hours Saturday"
    ]
    
    for cmd in commands:
        result = await nina.update_schedule(cmd, "Test User")
        if 'schedule' in cmd.lower() or 'what' in cmd.lower():
            result = await nina.query_schedule(cmd)
        print(f"\n   Command: '{cmd}'")
        print(f"   Result: {result.get('message', 'No message')[:100]}...")
    
    # Test 4: Check coverage gaps
    print("\n4️⃣ Testing gap detection:")
    gaps = await nina.detect_gaps()
    if gaps:
        for gap in gaps:
            print(f"   Gap found: {gap}")
    else:
        print("   No coverage gaps detected")
    
    print("\n✅ Nina test complete!")

if __name__ == '__main__':
    asyncio.run(test_nina())
