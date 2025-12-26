#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add pluma_local to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pluma-local"))

from pluma_local import LocalPlumaAgent

def main():
    try:
        # Get input from Node.js
        input_data = json.loads(sys.argv[1])
        method = input_data['method']
        params = input_data.get('params', {})
        
        # Initialize agent
        agent = LocalPlumaAgent()
        if not agent.initialize():
            print(json.dumps({'error': 'Failed to initialize Gmail service'}))
            sys.exit(1)
        
        # Route to appropriate method
        if method == 'pluma_fetch_emails':
            result = fetch_emails(agent, params)
        elif method == 'pluma_generate_reply':
            result = generate_reply(agent, params)
        elif method == 'pluma_create_draft':
            result = create_draft(agent, params)
        elif method == 'pluma_search_emails':
            result = search_emails(agent, params)
        elif method == 'pluma_get_thread':
            result = get_thread(agent, params)
        else:
            result = {'error': f'Unknown method: {method}'}
        
        # Return JSON response
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

def fetch_emails(agent, params):
    """Fetch latest emails from Gmail"""
    max_results = params.get('max_results', 10)
    days_back = params.get('days_back', 7)
    
    # Use existing agent method
    emails = agent.fetch_latest_emails(max_results=max_results)
    
    # Format for Claude display
    if not emails:
        return "No emails found in your inbox."
    
    formatted = []
    for i, email in enumerate(emails, 1):
        formatted.append(f"{i}. From: {email.get('from', 'Unknown')}")
        formatted.append(f"   Subject: {email.get('subject', 'No subject')}")
        formatted.append(f"   Date: {email.get('date', 'Unknown date')}")
        formatted.append(f"   ID: {email.get('id', '')}")
        formatted.append(f"   Preview: {email.get('snippet', '')[:100]}...")
        formatted.append("")
    
    return "\n".join(formatted)

def generate_reply(agent, params):
    """Generate a draft reply using Claude"""
    email_id = params['email_id']
    instructions = params.get('instructions', '')
    style = params.get('style', 'professional')
    
    # First, fetch the email by ID
    email = None
    
    # Try to get from cache first
    if agent.redis_client:
        try:
            cache_key = f"email:{email_id}"
            cached = agent.redis_client.get(cache_key)
            if cached:
                email = json.loads(cached)
        except:
            pass
    
    # If not in cache, fetch from Gmail
    if not email:
        try:
            message = agent.gmail_service.users().messages().get(
                userId='me',
                id=email_id
            ).execute()
            email = agent._parse_email(message)
        except Exception as e:
            return f"Error: Could not fetch email {email_id}: {str(e)}"
    
    # Update style preference
    agent.draft_style = style
    
    # Generate reply using agent
    prompt = instructions if instructions else f"Reply to this email in a {style} style"
    
    reply = agent.generate_draft_reply(email, prompt)
    
    return f"Draft Reply Generated:\n\n{reply}"

def create_draft(agent, params):
    """Create a Gmail draft"""
    email_id = params['email_id']
    draft_body = params['draft_body']
    
    # Get email details
    email = None
    
    # Try cache first
    if agent.redis_client:
        try:
            cache_key = f"email:{email_id}"
            cached = agent.redis_client.get(cache_key)
            if cached:
                email = json.loads(cached)
        except:
            pass
    
    # If not in cache, fetch from Gmail
    if not email:
        try:
            message = agent.gmail_service.users().messages().get(
                userId='me',
                id=email_id
            ).execute()
            email = agent._parse_email(message)
        except Exception as e:
            return f"Error: Could not fetch email {email_id}: {str(e)}"
    
    # Create draft using agent
    draft_id = agent.create_gmail_draft(email, draft_body)
    
    if draft_id:
        return f"✓ Draft created successfully in Gmail (ID: {draft_id})"
    else:
        return "Failed to create draft"

def search_emails(agent, params):
    """Search emails with Gmail query"""
    query = params['query']
    max_results = params.get('max_results', 10)
    
    # Use Gmail API search
    try:
        results = agent.gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"No emails found matching: {query}"
        
        emails = []
        for msg in messages:
            # Get full message details
            message = agent.gmail_service.users().messages().get(
                userId='me',
                id=msg['id']
            ).execute()
            
            # Parse email data
            email_data = agent._parse_email(message)
            emails.append(email_data)
        
        formatted = [f"Found {len(emails)} emails matching '{query}':\n"]
        for i, email in enumerate(emails, 1):
            formatted.append(f"{i}. {email.get('subject', 'No subject')}")
            formatted.append(f"   From: {email.get('from', 'Unknown')}")
            formatted.append(f"   Date: {email.get('date', 'Unknown')}")
            formatted.append(f"   ID: {email.get('id', '')}")
            formatted.append("")
        
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Error searching emails: {str(e)}"

def get_thread(agent, params):
    """Get full email thread"""
    thread_id = params['thread_id']
    
    try:
        # Get thread from Gmail
        thread = agent.gmail_service.users().threads().get(
            userId='me',
            id=thread_id
        ).execute()
        
        messages = thread.get('messages', [])
        
        if not messages:
            return "Thread not found or empty"
        
        formatted = [f"Thread with {len(messages)} messages:\n"]
        for i, msg in enumerate(messages, 1):
            # Parse each message
            email_data = agent._parse_email(msg)
            
            formatted.append(f"--- Message {i} ---")
            formatted.append(f"From: {email_data.get('from', 'Unknown')}")
            formatted.append(f"Date: {email_data.get('date', 'Unknown')}")
            formatted.append(f"Subject: {email_data.get('subject', 'No subject')}")
            formatted.append(f"Body preview: {email_data.get('snippet', 'No content')[:200]}...")
            formatted.append("")
        
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Error fetching thread: {str(e)}"

if __name__ == '__main__':
    main()
