#!/usr/bin/env python3
import asyncio
from yanay import YanayOrchestrator

async def test():
    o = YanayOrchestrator()
    await o.initialize()
    
    print("Testing: 'show my tasks'")
    response = await o.process_message('show my tasks', 'test_user', 'TestUser')
    print(f"Response: {response}")
    
    if 'Failed to query tasks: 400' in response:
        print("❌ FAILED - Still getting 400 error")
        return False
    elif 'Calendar queries' in response:
        print("❌ FAILED - Still routing to calendar")
        return False
    else:
        print("✅ SUCCESS - Task routing restored!")
        return True

if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"Test result: {result}")