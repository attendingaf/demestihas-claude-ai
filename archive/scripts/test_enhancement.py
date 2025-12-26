#!/usr/bin/env python3
"""
Quick test to verify Yanay enhancement is working
Run this on the VPS to test conversation and token tracking
"""

import asyncio
import redis
import json
from datetime import datetime

async def test_yanay_enhancement():
    """Test the conversation enhancement components"""
    
    print("🧪 Testing Yanay Conversation Enhancement")
    print("=" * 50)
    
    # Test Redis connection
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return
    
    # Check conversation state
    user_id = "7496082572"
    conv_key = f"conv:{user_id}:turns"
    turn_count = r.llen(conv_key)
    print(f"📝 Conversation turns stored: {turn_count}")
    
    if turn_count > 0:
        latest = r.lindex(conv_key, 0)
        try:
            turn_data = json.loads(latest)
            print(f"   Latest message: {turn_data.get('message', 'N/A')[:50]}...")
            print(f"   Emotion detected: {turn_data.get('emotion', 'N/A')}")
        except:
            print("   (Unable to parse turn data)")
    
    # Test token tracking
    today = datetime.now().strftime('%Y-%m-%d')
    token_key = f"tokens:{today}:{user_id}"
    usage = r.get(token_key)
    
    if usage:
        print(f"💰 Token usage today: ${float(usage):.4f}")
    else:
        print("💰 No token usage tracked yet")
        print("   (This is normal if Opus conversation hasn't been triggered)")
    
    # Try to import and test managers
    print("\n🔧 Testing enhancement components:")
    print("-" * 30)
    
    try:
        from conversation_manager import ConversationStateManager
        cm = ConversationStateManager()
        summary = cm.get_summary(user_id)
        print(f"✅ ConversationStateManager working")
        print(f"   Summary: {summary[:100]}...")
    except Exception as e:
        print(f"❌ ConversationStateManager error: {e}")
    
    try:
        from token_manager import TokenBudgetManager
        tm = TokenBudgetManager()
        budget = tm.check_budget(user_id)
        stats = tm.get_usage_stats(user_id)
        print(f"✅ TokenBudgetManager working")
        print(f"   Daily limit: ${stats['limit_usd']}")
        print(f"   Remaining: ${stats['remaining_usd']:.2f}")
        print(f"   Est. messages left: {stats['estimated_messages_remaining']}")
    except Exception as e:
        print(f"❌ TokenBudgetManager error: {e}")
    
    # Check if Yanay has the methods
    print("\n🔍 Checking Yanay integration:")
    print("-" * 30)
    
    try:
        with open('yanay.py', 'r') as f:
            content = f.read()
            
        checks = [
            ('evaluate_response_mode', 'Intelligent routing'),
            ('opus_conversation', 'Opus conversation handler'),
            ('conversation_manager', 'Conversation manager import'),
            ('token_manager', 'Token manager import'),
            ('enhanced_process_message', 'Enhanced processing')
        ]
        
        for method, desc in checks:
            if method in content:
                print(f"✅ {desc} found")
            else:
                print(f"❌ {desc} missing")
                
    except Exception as e:
        print(f"❌ Could not check yanay.py: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    
    if turn_count > 0 and 'evaluate_response_mode' in content:
        print("✅ Enhancement is partially working!")
        print("   - Conversations are being tracked")
        print("   - To activate token tracking, trigger an Opus conversation:")
        print("     Send: 'I'm feeling stressed about work'")
    elif turn_count > 0:
        print("⚠️  Conversation tracking works but full enhancement not integrated")
        print("   Run: python3 yanay_integrator.py")
    else:
        print("❌ Enhancement not fully active yet")
        print("   Check if yanay.py was properly modified")

if __name__ == "__main__":
    asyncio.run(test_yanay_enhancement())
