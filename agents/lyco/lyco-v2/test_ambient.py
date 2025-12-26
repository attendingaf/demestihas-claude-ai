#!/usr/bin/env python3
"""
Test script for Lyco 2.0 Ambient Capture
Tests individual components and end-to-end flow
"""
import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager
from ambient.redis_connector import RedisConnector


async def test_database_connection():
    """Test Supabase connection"""
    print("\n📊 Testing Database Connection...")
    try:
        db = DatabaseManager()
        count = await db.get_pending_tasks_count()
        print(f"✅ Database connected! Pending tasks: {count}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_redis_connection():
    """Test Redis connection"""
    print("\n🔴 Testing Redis Connection...")
    try:
        redis = RedisConnector()
        connected = await redis.connect()
        if connected:
            # Test publish/subscribe
            await redis.publish('test:channel', {'test': 'message'})
            print("✅ Redis connected and working!")
            await redis.close()
            return True
        else:
            print("❌ Redis connection failed")
            return False
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


async def test_manual_signal():
    """Test creating a manual signal"""
    print("\n📝 Testing Manual Signal Creation...")
    try:
        db = DatabaseManager()

        # Create test signal
        signal_id = await db.create_signal(
            source='test',
            raw_content="I'll send the quarterly report by Friday afternoon",
            metadata={'test': True},
            user_id=os.environ.get('USER_WORK_EMAIL', 'test@example.com')
        )

        print(f"✅ Created test signal: {signal_id}")

        # Process the signal
        from src.processor import IntelligenceEngine

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_key:
            print("⚠️  ANTHROPIC_API_KEY not set - skipping LLM processing")
            return True

        engine = IntelligenceEngine(anthropic_key)
        results = await engine.process_all_signals()

        print(f"✅ Processed {results['processed']} signals")
        print(f"✅ Created {results['tasks_created']} tasks")

        return True

    except Exception as e:
        print(f"❌ Signal test failed: {e}")
        return False


async def test_email_capture():
    """Test Gmail integration"""
    print("\n📧 Testing Email Capture...")
    try:
        from ambient.capture_email import EmailCapture

        email_capture = EmailCapture()
        if not email_capture.service:
            print("⚠️  Gmail not configured - run setup_google_auth.py")
            return False

        # Test with work email
        work_email = os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
        signals = await email_capture.capture_signals(work_email)

        print(f"✅ Captured {len(signals)} email signals")

        # Show sample signal
        if signals:
            print(f"   Sample: {signals[0]['content'][:100]}...")

        return True

    except ImportError:
        print("⚠️  Google API libraries not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Email capture failed: {e}")
        return False


async def test_calendar_capture():
    """Test Calendar integration"""
    print("\n📅 Testing Calendar Capture...")
    try:
        from ambient.capture_calendar import CalendarCapture

        calendar_capture = CalendarCapture()
        if not calendar_capture.service:
            print("⚠️  Calendar not configured - run setup_google_auth.py")
            return False

        # Test with primary calendar
        signals = await calendar_capture.capture_signals('primary')

        print(f"✅ Captured {len(signals)} calendar signals")

        # Show sample signal
        if signals:
            print(f"   Sample: {signals[0]['content'][:100]}...")

        return True

    except ImportError:
        print("⚠️  Google API libraries not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Calendar capture failed: {e}")
        return False


async def test_end_to_end():
    """Test full ambient capture flow"""
    print("\n🔄 Testing End-to-End Flow...")

    try:
        from ambient.ambient_capture import AmbientCaptureOrchestrator

        orchestrator = AmbientCaptureOrchestrator()

        print("   Starting capture cycle...")
        start_time = datetime.now()

        # Run one capture cycle
        await asyncio.gather(
            orchestrator.capture_email_signals(),
            orchestrator.capture_calendar_signals()
        )

        # Process signals
        await orchestrator.process_signals()

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ Capture cycle completed in {elapsed:.1f} seconds")

        # Check for new tasks
        db = DatabaseManager()
        pending = await db.get_pending_tasks_count()
        print(f"✅ Pending tasks after capture: {pending}")

        return True

    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Lyco 2.0 Ambient Capture - Test Suite")
    print("=" * 60)

    # Check environment
    print("\n🔍 Checking Environment Variables...")
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'ANTHROPIC_API_KEY']
    missing = []

    for var in required_vars:
        if os.environ.get(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is missing")
            missing.append(var)

    if missing:
        print("\n⚠️  Missing required environment variables!")
        print("   Please check your .env file")
        return

    # Run tests
    tests = [
        ("Database", test_database_connection),
        ("Redis", test_redis_connection),
        ("Manual Signal", test_manual_signal),
        ("Email Capture", test_email_capture),
        ("Calendar Capture", test_calendar_capture),
        ("End-to-End", test_end_to_end)
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Ambient capture is ready to use.")
        print("\nRun continuously with: python ambient/ambient_capture.py")
        print("Or deploy with: docker-compose up -d")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before running.")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run tests
    asyncio.run(main())
