import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

logger = logging.getLogger(__name__)

class GoogleDriveMonitor:
    """Monitor Google Drive folder for new audio files and manage uploads"""
    
    def __init__(self):
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.service = self.authenticate()
        self.last_check_file = Path("/tmp/last_drive_check.txt")
        self.output_folders = {}
        self.ensure_output_folders()
        
    def authenticate(self):
        """Authenticate with Google Drive API"""
        
        SCOPES = ['https://www.googleapis.com/auth/drive']
        
        # Use service account if available
        service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if service_account_file and os.path.exists(service_account_file):
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        else:
            # Fall back to OAuth2 (requires initial setup)
            creds = None
            token_file = '/app/credentials/token.pickle'
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    raise Exception("No valid Google credentials found")
        
        return build('drive', 'v3', credentials=creds)
    
    def ensure_output_folders(self):
        """Create output folder structure if it doesn't exist"""
        
        folders = [
            "01_compressed",
            "02_chunks", 
            "03_transcripts",
            "04_formatted_scripts",
            "05_analysis"
        ]
        
        # Get Audio Processing parent folder
        parent_folder = self.get_or_create_folder("Audio Processing", self.folder_id)
        
        for folder_name in folders:
            folder_id = self.get_or_create_folder(folder_name, parent_folder)
            self.output_folders[folder_name] = folder_id
    
    def get_or_create_folder(self, name: str, parent_id: str) -> str:
        """Get folder ID or create if it doesn't exist"""
        
        # Check if folder exists
        query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        
        results = self.service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            # Create folder
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"Created folder: {name}")
            return folder.get('id')
    
    async def check_for_new_files(self) -> List[Dict]:
        """Check for new audio files in the monitored folder"""
        
        # Get last check time
        last_check = self.get_last_check_time()
        
        # Query for files modified after last check - includes fallback MIME type and folder scope
        query = f"'{self.folder_id}' in parents and (mimeType contains 'audio' or mimeType = 'application/octet-stream') and modifiedTime > '{last_check}' and trashed = false"
        
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            # Debug logging
            logger.info(f"Search query: {query}")
            logger.info(f"Found {len(files)} files in Audio Processing folder (modified after {last_check})")
            if files:
                for file in files:
                    logger.info(f"  - {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")
            
            # Update last check time
            if files:
                self.update_last_check_time()
                logger.info(f"Updated last check time after finding {len(files)} new audio files")
            else:
                logger.info("No new audio files found")
            
            return files
            
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
            return []
    
    async def check_all_files(self) -> List[Dict]:
        """Check for ALL audio files in the monitored folder (for debugging)"""
        
        # Query for all audio files in folder (no time restriction)
        query = f"'{self.folder_id}' in parents and (mimeType contains 'audio' or mimeType = 'application/octet-stream') and trashed = false"
        
        try:
            results = self.service.files().list(
                q=query,
                pageSize=10,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            # Debug logging
            logger.info(f"Debug search query: {query}")
            logger.info(f"Found {len(files)} total files in Audio Processing folder")
            if files:
                for file in files:
                    logger.info(f"  - {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")
            else:
                logger.info("No audio files found in folder - check permissions and folder sharing")
            
            return files
            
        except Exception as e:
            logger.error(f"Error checking for all files: {e}")
            return []
    
    async def download_file(self, file_id: str, output_path: Path) -> Path:
        """Download file from Google Drive"""
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")
            
            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Downloaded to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
    
    async def upload_to_folder(
        self, 
        file_path: Path, 
        folder_name: str,
        replace_original: bool = False,
        original_file_id: Optional[str] = None
    ) -> str:
        """Upload file to specified output folder"""
        
        folder_id = self.output_folders.get(folder_name)
        if not folder_id:
            raise ValueError(f"Unknown folder: {folder_name}")
        
        file_metadata = {
            'name': file_path.name,
            'parents': [folder_id]
        }
        
        # Determine MIME type
        mime_type = 'text/plain'
        if file_path.suffix == '.mp3':
            mime_type = 'audio/mpeg'
        elif file_path.suffix == '.json':
            mime_type = 'application/json'
        elif file_path.suffix == '.md':
            mime_type = 'text/markdown'
        
        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )
        
        try:
            if replace_original and original_file_id:
                # Update the original file
                file = self.service.files().update(
                    fileId=original_file_id,
                    media_body=media
                ).execute()
                logger.info(f"Replaced original file: {file.get('name')}")
            else:
                # Create new file
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name'
                ).execute()
                logger.info(f"Uploaded {file.get('name')} to {folder_name}")
            
            return file.get('id')
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def get_last_check_time(self) -> str:
        """Get the last check time in RFC3339 format"""
        
        if self.last_check_file.exists():
            with open(self.last_check_file, 'r') as f:
                return f.read().strip()
        else:
            # Default to 24 hours ago
            last_check = datetime.utcnow() - timedelta(hours=24)
            return last_check.isoformat() + 'Z'
    
    def update_last_check_time(self):
        """Update the last check time"""
        
        current_time = datetime.utcnow().isoformat() + 'Z'
        with open(self.last_check_file, 'w') as f:
            f.write(current_time)
