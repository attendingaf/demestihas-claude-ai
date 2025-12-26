#!/usr/bin/env python3
"""
Audio Inbox Processor - Automated Google Drive Audio Transcription Tool

SETUP INSTRUCTIONS:
==================

1. Install Required Libraries:
   pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

2. Google Cloud Setup:
   a. Go to https://console.cloud.google.com/
   b. Create a new project or select an existing one
   c. Enable the Google Drive API:
      - Go to "APIs & Services" > "Library"
      - Search for "Google Drive API" and enable it
   d. Create OAuth 2.0 credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop app" as the application type
      - Download the credentials JSON file
      - Save it as ~/.credentials/drive_credentials.json

3. OpenAI API Key Setup:
   a. Get your API key from https://platform.openai.com/api-keys
   b. Save it to ~/.openai_key (just the key, no quotes)
   OR
   c. Set environment variable: export OPENAI_API_KEY="your-key-here"

4. First Run:
   - Run: python3 audio_inbox_processor.py
   - A browser window will open for Google authentication
   - Grant permissions to access your Google Drive
   - The token will be saved for future runs

5. Usage:
   - Single run: python3 audio_inbox_processor.py
   - Watch mode: python3 audio_inbox_processor.py --watch
     (Checks for new files every 5 minutes)

FOLDER STRUCTURE IN GOOGLE DRIVE:
- MyDrive/Audio_Inbox/          (source folder for audio files)
- MyDrive/Audio_Inbox/archived/ (processed files moved here)
- MyDrive/Audio_Transcripts/    (transcripts uploaded here)
"""

import os
import sys
import json
import pickle
import argparse
import tempfile
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import urllib.request
import urllib.parse
import urllib.error
import io
import mimetypes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
AUDIO_FORMATS = {'.m4a', '.mp3', '.mp4', '.wav', '.ogg', '.webm'}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB Whisper limit
CREDENTIALS_PATH = Path.home() / '.credentials' / 'drive_credentials.json'
TOKEN_PATH = Path.home() / '.credentials' / 'token.pickle'
OPENAI_KEY_PATH = Path.home() / '.openai_key'
LOG_FILE = 'audio_processor.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoogleDriveManager:
    """Handles all Google Drive operations"""
    
    def __init__(self):
        self.service = None
        self.authenticate()
        
    def authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if TOKEN_PATH.exists():
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_PATH.exists():
                    logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
                    logger.error("Please follow setup instructions to create OAuth credentials")
                    sys.exit(1)
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Drive")
    
    def find_folder(self, folder_name: str, parent_id: str = None) -> Optional[str]:
        """Find a folder by name, optionally within a parent folder"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except HttpError as e:
            logger.error(f"Error finding folder {folder_name}: {e}")
            return None
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> Optional[str]:
        """Create a folder in Google Drive"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            file = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"Created folder: {folder_name}")
            return file.get('id')
            
        except HttpError as e:
            logger.error(f"Error creating folder {folder_name}: {e}")
            return None
    
    def list_audio_files(self, folder_id: str, archived_folder_id: str) -> List[Dict]:
        """List all audio files in the inbox folder, excluding archived"""
        try:
            # Build query for audio files
            mime_queries = [
                "mimeType='audio/mp4'",
                "mimeType='audio/mpeg'",
                "mimeType='audio/mp3'",
                "mimeType='audio/wav'",
                "mimeType='audio/ogg'",
                "mimeType='audio/webm'",
                "mimeType='audio/x-m4a'"
            ]
            
            query = f"('{folder_id}' in parents) and ({' or '.join(mime_queries)}) and trashed=false"
            
            audio_files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, size, mimeType)',
                    pageToken=page_token
                ).execute()
                
                files = results.get('files', [])
                
                # Filter out files in archived folder
                for file in files:
                    # Check if file is not in archived folder
                    parents_response = self.service.files().get(
                        fileId=file['id'],
                        fields='parents'
                    ).execute()
                    
                    parents = parents_response.get('parents', [])
                    if archived_folder_id not in parents:
                        audio_files.append(file)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return audio_files
            
        except HttpError as e:
            logger.error(f"Error listing audio files: {e}")
            return []
    
    def download_file(self, file_id: str, file_name: str, download_path: Path) -> bool:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            file_path = download_path / file_name
            fh = io.FileIO(str(file_path), 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download {int(status.progress() * 100)}% complete: {file_name}")
            
            fh.close()
            return True
            
        except HttpError as e:
            logger.error(f"Error downloading file {file_name}: {e}")
            return False
    
    def move_file(self, file_id: str, new_parent_id: str) -> bool:
        """Move a file to a different folder"""
        try:
            # Get current parents
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file
            self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    def upload_file(self, local_path: Path, file_name: str, folder_id: str, mime_type: str = 'text/markdown') -> bool:
        """Upload a file to Google Drive"""
        try:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                str(local_path),
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"Uploaded file: {file_name}")
            return True
            
        except HttpError as e:
            logger.error(f"Error uploading file {file_name}: {e}")
            return False


class WhisperTranscriber:
    """Handles audio transcription using OpenAI Whisper API"""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from file or environment"""
        # Try environment variable first
        api_key = os.environ.get('OPENAI_API_KEY')
        
        # Try file if environment variable not set
        if not api_key and OPENAI_KEY_PATH.exists():
            with open(OPENAI_KEY_PATH, 'r') as f:
                api_key = f.read().strip()
        
        if not api_key:
            logger.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or save key to ~/.openai_key")
            sys.exit(1)
        
        return api_key
    
    def transcribe(self, audio_file_path: Path) -> Optional[str]:
        """Transcribe audio file using Whisper API"""
        try:
            # Check file size
            file_size = audio_file_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"File {audio_file_path.name} exceeds 25MB limit ({file_size / 1024 / 1024:.2f}MB)")
                return None
            
            # Prepare the request
            url = "https://api.openai.com/v1/audio/transcriptions"
            
            # Read the audio file
            with open(audio_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Create multipart form data
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            body = []
            
            # Add model field
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="model"')
            body.append(b'')
            body.append(b'whisper-1')
            
            # Add file field
            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="file"; filename="{audio_file_path.name}"'.encode())
            body.append(f'Content-Type: {mimetypes.guess_type(audio_file_path)[0] or "audio/mpeg"}'.encode())
            body.append(b'')
            body.append(audio_data)
            
            # End boundary
            body.append(f'--{boundary}--'.encode())
            body.append(b'')
            
            # Join body parts
            body_bytes = b'\r\n'.join(body)
            
            # Create request
            request = urllib.request.Request(
                url,
                data=body_bytes,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': f'multipart/form-data; boundary={boundary}'
                }
            )
            
            # Send request
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('text', '')
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Whisper API error: {e.code} - {error_body}")
            return None
        except Exception as e:
            logger.error(f"Error transcribing {audio_file_path.name}: {e}")
            return None


class TranscriptFormatter:
    """Formats transcripts into markdown and text files"""
    
    @staticmethod
    def estimate_duration(word_count: int) -> str:
        """Estimate speaking duration from word count (150 words/minute average)"""
        minutes = word_count / 150
        if minutes < 1:
            return "< 1 minute"
        elif minutes < 60:
            return f"~{int(minutes)} minutes"
        else:
            hours = minutes / 60
            return f"~{hours:.1f} hours"
    
    @staticmethod
    def create_markdown_transcript(filename: str, transcript: str) -> str:
        """Create formatted markdown transcript"""
        now = datetime.now()
        word_count = len(transcript.split())
        duration = TranscriptFormatter.estimate_duration(word_count)
        
        markdown = f"""# Audio Transcript: {filename}

## Metadata
- **File:** {filename}
- **Processed:** {now.strftime('%Y-%m-%d %H:%M:%S')}
- **Word Count:** {word_count:,}
- **Estimated Duration:** {duration}

---

## Raw Transcript

{transcript}

---

## Analysis

### Speaker Identification
*[To be filled: Identify different speakers if multiple]*

- Speaker 1: 
- Speaker 2: 
- Speaker 3: 

### Action Items
*[Extract action items from the transcript]*

- [ ] Action item 1
- [ ] Action item 2
- [ ] Action item 3

### Key Decisions
*[Document any decisions made during the conversation]*

1. Decision 1: 
2. Decision 2: 
3. Decision 3: 

### Follow-ups Required
*[List any follow-up tasks or meetings needed]*

1. Follow-up 1: 
2. Follow-up 2: 
3. Follow-up 3: 

---

## Notes
*[Additional notes or context]*

"""
        return markdown
    
    @staticmethod
    def save_transcripts(filename: str, transcript: str, temp_dir: Path) -> Tuple[Path, Path]:
        """Save transcript as markdown and text files"""
        base_name = Path(filename).stem
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Save markdown version
        markdown_content = TranscriptFormatter.create_markdown_transcript(filename, transcript)
        markdown_file = temp_dir / f"{base_name}_transcript_{date_str}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Save raw text version
        text_file = temp_dir / f"{base_name}_transcript_{date_str}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Transcript of: {filename}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
        
        return markdown_file, text_file


class AudioInboxProcessor:
    """Main processor orchestrating the workflow"""
    
    def __init__(self):
        self.drive = GoogleDriveManager()
        self.transcriber = WhisperTranscriber()
        self.formatter = TranscriptFormatter()
        self.setup_folders()
        
    def setup_folders(self):
        """Setup required folders in Google Drive"""
        # Find or create Audio_Inbox folder
        self.inbox_folder_id = self.drive.find_folder('Audio_Inbox')
        if not self.inbox_folder_id:
            logger.info("Creating Audio_Inbox folder...")
            self.inbox_folder_id = self.drive.create_folder('Audio_Inbox')
            if not self.inbox_folder_id:
                logger.error("Failed to create Audio_Inbox folder")
                sys.exit(1)
        
        # Find or create archived subfolder
        self.archived_folder_id = self.drive.find_folder('archived', self.inbox_folder_id)
        if not self.archived_folder_id:
            logger.info("Creating archived subfolder...")
            self.archived_folder_id = self.drive.create_folder('archived', self.inbox_folder_id)
        
        # Find or create Audio_Transcripts folder
        self.transcripts_folder_id = self.drive.find_folder('Audio_Transcripts')
        if not self.transcripts_folder_id:
            logger.info("Creating Audio_Transcripts folder...")
            self.transcripts_folder_id = self.drive.create_folder('Audio_Transcripts')
    
    def process_audio_file(self, file_info: Dict, temp_dir: Path, file_num: int, total_files: int) -> bool:
        """Process a single audio file"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        logger.info(f"Processing file {file_num}/{total_files}: {file_name}")
        
        # Download file
        logger.info(f"Downloading {file_name}...")
        if not self.drive.download_file(file_id, file_name, temp_dir):
            logger.error(f"Failed to download {file_name}")
            return False
        
        # Transcribe
        logger.info(f"Transcribing {file_name}...")
        audio_path = temp_dir / file_name
        transcript = self.transcriber.transcribe(audio_path)
        
        if not transcript:
            logger.error(f"Failed to transcribe {file_name}")
            return False
        
        logger.info(f"Successfully transcribed {file_name}")
        
        # Save transcripts
        markdown_file, text_file = self.formatter.save_transcripts(file_name, transcript, temp_dir)
        
        # Upload transcripts
        success = True
        for file_path, mime_type in [(markdown_file, 'text/markdown'), (text_file, 'text/plain')]:
            if not self.drive.upload_file(file_path, file_path.name, self.transcripts_folder_id, mime_type):
                logger.error(f"Failed to upload {file_path.name}")
                success = False
        
        if success:
            # Move original file to archived
            logger.info(f"Moving {file_name} to archived...")
            if self.drive.move_file(file_id, self.archived_folder_id):
                logger.info(f"Successfully processed and archived {file_name}")
            else:
                logger.warning(f"Processed {file_name} but failed to move to archive")
        
        # Clean up temporary files
        try:
            audio_path.unlink()
            markdown_file.unlink()
            text_file.unlink()
        except:
            pass
        
        return success
    
    def process_all_files(self) -> Tuple[int, int]:
        """Process all audio files in the inbox"""
        # Get list of audio files
        logger.info("Fetching audio files from Audio_Inbox...")
        audio_files = self.drive.list_audio_files(self.inbox_folder_id, self.archived_folder_id)
        
        if not audio_files:
            logger.info("No audio files found in Audio_Inbox")
            return 0, 0
        
        logger.info(f"Found {len(audio_files)} audio file(s) to process")
        
        successful = 0
        failed = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, file_info in enumerate(audio_files, 1):
                try:
                    if self.process_audio_file(file_info, temp_path, i, len(audio_files)):
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Unexpected error processing {file_info['name']}: {e}")
                    failed += 1
        
        return successful, failed
    
    def run_once(self):
        """Run the processor once"""
        logger.info("=" * 60)
        logger.info("Starting audio inbox processing...")
        
        successful, failed = self.process_all_files()
        
        logger.info("=" * 60)
        logger.info(f"Processing complete: {successful} successful, {failed} failed")
        
        return successful, failed
    
    def watch_folder(self, interval: int = 300):
        """Watch folder and process new files periodically"""
        logger.info(f"Starting watch mode - checking every {interval} seconds")
        
        while True:
            try:
                successful, failed = self.run_once()
                
                if successful > 0 or failed > 0:
                    logger.info(f"Batch complete: {successful} successful, {failed} failed")
                
                logger.info(f"Waiting {interval} seconds before next check...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Watch mode interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in watch mode: {e}")
                logger.info(f"Retrying in {interval} seconds...")
                time.sleep(interval)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Process audio files from Google Drive and generate transcripts'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch folder continuously (check every 5 minutes)'
    )
    
    args = parser.parse_args()
    
    # Check for credentials file
    if not CREDENTIALS_PATH.exists():
        logger.error(f"Google Drive credentials not found at {CREDENTIALS_PATH}")
        logger.error("Please follow the setup instructions in this script's header")
        sys.exit(1)
    
    # Initialize processor
    try:
        processor = AudioInboxProcessor()
    except Exception as e:
        logger.error(f"Failed to initialize processor: {e}")
        sys.exit(1)
    
    # Run processor
    if args.watch:
        processor.watch_folder()
    else:
        processor.run_once()


if __name__ == "__main__":
    main()