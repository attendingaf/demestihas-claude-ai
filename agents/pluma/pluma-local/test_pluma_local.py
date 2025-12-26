#!/usr/bin/env python3
"""Automated tests for Pluma Local components."""

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import redis
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pluma_local import LocalPlumaAgent
from gmail_auth import GmailAuthenticator

class TestGmailAuth(unittest.TestCase):
    """Test Gmail authentication functionality."""
    
    def setUp(self):
        self.auth = GmailAuthenticator()
    
    def test_credentials_path(self):
        """Test that credentials paths are set correctly."""
        self.assertTrue(self.auth.credentials_path.endswith('credentials.json'))
        self.assertTrue(self.auth.token_path.endswith('token.pickle'))
    
    def test_credentials_exist(self):
        """Check if credentials.json exists."""
        if not os.path.exists(self.auth.credentials_path):
            self.skipTest("credentials.json not found - run setup.py first")
        self.assertTrue(os.path.exists(self.auth.credentials_path))
    
    @patch('gmail_auth.build')
    def test_service_creation(self, mock_build):
        """Test Gmail service creation."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock the getProfile call
        mock_service.users().getProfile().execute.return_value = {
            'emailAddress': 'test@gmail.com'
        }
        
        with patch.object(self.auth, 'authenticate') as mock_auth:
            mock_auth.return_value = MagicMock()
            service = self.auth.get_service()
            self.assertIsNotNone(service)

class TestLocalPlumaAgent(unittest.TestCase):
    """Test LocalPlumaAgent functionality."""
    
    def setUp(self):
        self.agent = LocalPlumaAgent()
    
    def test_redis_connection(self):
        """Test Redis connection setup."""
        # Check if Redis is available
        try:
            client = redis.Redis(host='localhost', port=6379)
            client.ping()
            redis_available = True
        except:
            redis_available = False
        
        if redis_available:
            self.assertIsNotNone(self.agent.redis_client)
        else:
            self.assertIsNone(self.agent.redis_client)
    
    def test_anthropic_api_key(self):
        """Test that Anthropic API key is loaded."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            self.skipTest("ANTHROPIC_API_KEY not set")
        self.assertIsNotNone(self.agent.claude_client.api_key)
    
    @patch.object(LocalPlumaAgent, 'gmail_auth')
    def test_initialization(self, mock_auth):
        """Test agent initialization."""
        mock_service = MagicMock()
        mock_auth.get_service.return_value = mock_service
        
        result = self.agent.initialize()
        self.assertTrue(result)
        self.assertEqual(self.agent.gmail_service, mock_service)
    
    def test_parse_email(self):
        """Test email parsing."""
        sample_message = {
            'id': 'test123',
            'threadId': 'thread123',
            'snippet': 'Test email snippet',
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
                ],
                'body': {
                    'data': 'VGVzdCBlbWFpbCBib2R5'  # "Test email body" in base64
                }
            }
        }
        
        parsed = self.agent._parse_email(sample_message)
        
        self.assertEqual(parsed['id'], 'test123')
        self.assertEqual(parsed['subject'], 'Test Subject')
        self.assertEqual(parsed['from'], 'sender@example.com')
        self.assertEqual(parsed['to'], 'recipient@example.com')
        self.assertIn('Test email', parsed['snippet'])
    
    @patch('anthropic.Anthropic')
    def test_generate_draft_reply(self, mock_anthropic):
        """Test draft generation with Claude API."""
        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is a test draft reply.")]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        # Create test email
        test_email = {
            'id': 'test123',
            'from': 'sender@example.com',
            'subject': 'Test Subject',
            'date': 'Mon, 1 Jan 2024',
            'body': 'Test email body'
        }
        
        # Generate draft
        agent = LocalPlumaAgent()
        draft = agent.generate_draft_reply(test_email)
        
        self.assertIn("test draft reply", draft.lower())
    
    def test_email_stats_without_redis(self):
        """Test getting stats when Redis is not available."""
        self.agent.redis_client = None
        stats = self.agent.get_email_stats()
        self.assertIn('status', stats)
        self.assertEqual(stats['status'], 'Redis not available')
    
    @patch('redis.Redis')
    def test_email_stats_with_redis(self, mock_redis):
        """Test getting stats with Redis available."""
        mock_client = MagicMock()
        mock_client.keys.side_effect = [
            ['email:1', 'email:2'],  # email keys
            ['draft:1']  # draft keys
        ]
        self.agent.redis_client = mock_client
        
        stats = self.agent.get_email_stats()
        
        self.assertEqual(stats['cached_emails'], 2)
        self.assertEqual(stats['cached_drafts'], 1)
        self.assertEqual(stats['redis_status'], 'connected')

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up for integration tests."""
        cls.agent = LocalPlumaAgent()
        cls.gmail_initialized = cls.agent.initialize()
    
    def test_full_workflow(self):
        """Test the complete email fetch and draft generation workflow."""
        if not self.gmail_initialized:
            self.skipTest("Gmail not initialized - run setup.py first")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set")
        
        print("\n=== Running Full Workflow Test ===")
        
        # 1. Fetch emails
        print("1. Fetching emails...")
        emails = self.agent.fetch_latest_emails(max_results=1)
        
        if not emails:
            self.skipTest("No emails found to test with")
        
        self.assertGreater(len(emails), 0)
        print(f"   ✓ Fetched {len(emails)} email(s)")
        
        # 2. Generate draft
        print("2. Generating draft reply...")
        test_email = emails[0]
        draft = self.agent.generate_draft_reply(
            test_email,
            instructions="Keep it brief and professional"
        )
        
        self.assertIsNotNone(draft)
        self.assertGreater(len(draft), 10)
        print(f"   ✓ Generated draft ({len(draft)} chars)")
        
        # 3. Check caching if Redis available
        if self.agent.redis_client:
            print("3. Checking cache...")
            stats = self.agent.get_email_stats()
            self.assertGreater(stats.get('cached_emails', 0), 0)
            print(f"   ✓ Cache working: {stats}")
        else:
            print("3. Redis not available - skipping cache test")
        
        print("\n✓ Full workflow test completed successfully!")

def run_component_tests():
    """Run individual component tests."""
    print("\n" + "="*50)
    print("COMPONENT TESTS")
    print("="*50)
    
    # Test 1: Check environment
    print("\n1. Environment Check:")
    env_vars = {
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'PLUMA_DRAFT_STYLE': os.getenv('PLUMA_DRAFT_STYLE', 'not set')
    }
    
    for var, value in env_vars.items():
        status = "✓" if value and value != 'not set' else "✗"
        display_value = "***" if "KEY" in var and value else value
        print(f"   {status} {var}: {display_value}")
    
    # Test 2: Check credentials
    print("\n2. Gmail Credentials Check:")
    creds_path = "credentials/credentials.json"
    token_path = "credentials/token.pickle"
    
    print(f"   {'✓' if os.path.exists(creds_path) else '✗'} credentials.json exists")
    print(f"   {'✓' if os.path.exists(token_path) else '✗'} token.pickle exists")
    
    # Test 3: Redis connection
    print("\n3. Redis Connection Check:")
    try:
        client = redis.Redis(host='localhost', port=6379)
        client.ping()
        print("   ✓ Redis is running")
    except:
        print("   ✗ Redis not available (optional)")
    
    # Test 4: Gmail API
    print("\n4. Gmail API Check:")
    try:
        auth = GmailAuthenticator()
        service = auth.get_service()
        if service:
            print("   ✓ Gmail authentication successful")
        else:
            print("   ✗ Gmail authentication failed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Claude API
    print("\n5. Claude API Check:")
    if os.getenv('ANTHROPIC_API_KEY'):
        try:
            import anthropic
            client = anthropic.Anthropic()
            print("   ✓ Claude client initialized")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    else:
        print("   ✗ ANTHROPIC_API_KEY not set")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Pluma Local components')
    parser.add_argument('--quick', action='store_true', help='Run quick component tests only')
    parser.add_argument('--full', action='store_true', help='Run full test suite')
    args = parser.parse_args()
    
    if args.quick or (not args.full):
        run_component_tests()
    
    if args.full or (not args.quick):
        print("\n" + "="*50)
        print("RUNNING FULL TEST SUITE")
        print("="*50)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test cases
        suite.addTests(loader.loadTestsFromTestCase(TestGmailAuth))
        suite.addTests(loader.loadTestsFromTestCase(TestLocalPlumaAgent))
        suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Summary
        print("\n" + "="*50)
        if result.wasSuccessful():
            print("✓ ALL TESTS PASSED!")
        else:
            print(f"✗ Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
        print("="*50)