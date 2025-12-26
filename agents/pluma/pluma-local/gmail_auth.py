#!/usr/bin/env python3
"""Gmail OAuth2 authentication module for local Pluma setup."""

import os
import pickle
import json
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for reading and modifying emails
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailAuthenticator:
    """Handles Gmail OAuth2 authentication for local development."""
    
    def __init__(self, credentials_dir: str = "credentials"):
        self.credentials_dir = credentials_dir
        self.token_path = os.path.join(credentials_dir, "token.pickle")
        self.credentials_path = os.path.join(credentials_dir, "credentials.json")
        
    def authenticate(self) -> Optional[Credentials]:
        """
        Authenticate with Gmail API using OAuth2.
        
        Returns:
            Credentials object if successful, None otherwise
        """
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
                print("✓ Loaded existing credentials from token.pickle")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
                print("✓ Credentials refreshed successfully")
            else:
                if not os.path.exists(self.credentials_path):
                    print(f"❌ Error: credentials.json not found at {self.credentials_path}")
                    print("Please follow the README to set up Gmail API credentials")
                    return None
                
                print("Starting OAuth2 flow...")
                print("A browser window will open for authentication")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                print("✓ Authentication successful")
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
                print(f"✓ Credentials saved to {self.token_path}")
        
        return creds
    
    def get_service(self):
        """
        Get authenticated Gmail service object.
        
        Returns:
            Gmail service object or None if authentication fails
        """
        creds = self.authenticate()
        if not creds:
            return None
        
        try:
            service = build('gmail', 'v1', credentials=creds)
            # Test the connection
            profile = service.users().getProfile(userId='me').execute()
            print(f"✓ Connected to Gmail for: {profile.get('emailAddress', 'unknown')}")
            return service
        except HttpError as error:
            print(f"❌ An error occurred: {error}")
            return None
    
    def revoke_credentials(self):
        """Revoke stored credentials and delete token file."""
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
            print(f"✓ Removed token file: {self.token_path}")
        else:
            print("No token file found to remove")

if __name__ == "__main__":
    # Test authentication when run directly
    auth = GmailAuthenticator()
    service = auth.get_service()
    
    if service:
        print("\n✓ Gmail authentication test successful!")
        print("You can now use Pluma locally with your Gmail account")
    else:
        print("\n❌ Gmail authentication failed")
        print("Please check your credentials and try again")