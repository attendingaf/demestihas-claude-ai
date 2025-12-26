#!/usr/bin/env python3
"""
Google Drive Audio Processor with Automatic Compression and Chunking
Processes audio files from Google Drive, transcribes them using Whisper API,
and saves formatted transcripts back to Drive.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
import io
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# OpenAI imports
import requests

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
WHISPER_API_URL = 'https://api.openai.com/v1/audio/transcriptions'
MAX_FILE_SIZE_MB = 25
TARGET_SIZE_MB = 20
CHUNK_SIZE_MB = 20

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoogleDriveAudioProcessor:
    """Main processor class for handling audio files from Google Drive."""
    
    def __init__(self):
        """Initialize the processor with Google Drive and OpenAI credentials."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="audio_proc_"))
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
        # Setup Google Drive
        self.drive_service = self.setup_google_drive()
        
        # Setup OpenAI
        self.api_key = self.get_openai_key()
        
        # Check for ffmpeg
        if not self.check_ffmpeg():
            logger.error("ffmpeg is not installed!")
            print("\nffmpeg is required for audio processing.")
            print("Installation instructions:")
            print("  macOS: brew install ffmpeg")
            print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("  Windows: Download from https://ffmpeg.org/download.html")
            sys.exit(1)
        
        # Statistics
        self.stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_size_mb': 0,
            'compressed_size_mb': 0
        }
    
    def setup_google_drive(self):
        """Set up Google Drive API connection."""
        creds = None
        token_path = Path.home() / '.credentials' / 'token.json'
        creds_path = Path.home() / '.credentials' / 'drive_credentials.json'
        
        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # Refresh or create new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    logger.error(f"Credentials file not found: {creds_path}")
                    sys.exit(1)
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        logger.info("Successfully connected to Google Drive")
        return build('drive', 'v3', credentials=creds)
    
    def get_openai_key(self) -> str:
        """Get OpenAI API key from file or environment."""
        # Try file first
        key_file = Path.home() / '.openai_key'
        if key_file.exists():
            with open(key_file, 'r') as f:
                key = f.read().strip()
                if key:
                    logger.info("Loaded OpenAI API key from file")
                    return key
        
        # Try environment variable
        key = os.environ.get('OPENAI_API_KEY')
        if key:
            logger.info("Loaded OpenAI API key from environment")
            return key
        
        logger.error("OpenAI API key not found!")
        print("\nPlease provide OpenAI API key:")
        print("  1. Create ~/.openai_key file with your API key")
        print("  2. Or set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    def check_ffmpeg(self) -> bool:
        """Check if ffmpeg is installed."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_audio_duration(self, file_path: Path) -> float:
        """Get duration of audio file in seconds."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            logger.error(f"Failed to get duration for {file_path}")
            return 0
    
    def compress_audio(self, input_path: Path, target_mb: float = TARGET_SIZE_MB) -> Optional[Path]:
        """Compress audio file to target size."""
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb <= target_mb:
            logger.info(f"File already under {target_mb}MB, no compression needed")
            return input_path
        
        logger.info(f"Compressing {input_path.name} from {file_size_mb:.2f}MB to ~{target_mb}MB")
        
        # Calculate target bitrate
        duration = self.get_audio_duration(input_path)
        if duration == 0:
            logger.error("Cannot compress: unable to determine duration")
            return None
        
        # Calculate bitrate to achieve target size (with 95% safety margin)
        target_bits = target_mb * 0.95 * 1024 * 1024 * 8
        target_bitrate = int(target_bits / duration / 1000)  # in kbps
        
        # Minimum bitrate for reasonable quality
        target_bitrate = max(target_bitrate, 16)
        
        output_path = self.temp_dir / f"compressed_{input_path.name}"
        
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-b:a', f'{target_bitrate}k',
            '-ac', '1',  # Mono
            '-ar', '16000',  # 16kHz sample rate
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        try:
            logger.info(f"Compressing with bitrate: {target_bitrate}kbps")
            subprocess.run(cmd, capture_output=True, check=True)
            
            new_size_mb = output_path.stat().st_size / (1024 * 1024)
            compression_ratio = (1 - new_size_mb / file_size_mb) * 100
            logger.info(f"Compression successful: {file_size_mb:.2f}MB → {new_size_mb:.2f}MB ({compression_ratio:.1f}% reduction)")
            
            self.stats['compressed_size_mb'] += new_size_mb
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Compression failed: {e.stderr}")
            return None
    
    def chunk_audio(self, input_path: Path, chunk_mb: float = CHUNK_SIZE_MB) -> List[Path]:
        """Split audio file into chunks if still too large."""
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb <= MAX_FILE_SIZE_MB:
            return [input_path]
        
        logger.info(f"File still {file_size_mb:.2f}MB after compression, chunking required")
        
        duration = self.get_audio_duration(input_path)
        if duration == 0:
            logger.error("Cannot chunk: unable to determine duration")
            return [input_path]
        
        # Calculate segment duration for target chunk size
        num_chunks = int(file_size_mb / chunk_mb) + 1
        segment_duration = int(duration / num_chunks)
        
        output_pattern = str(self.temp_dir / f"chunk_{input_path.stem}_%03d{input_path.suffix}")
        
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-f', 'segment',
            '-segment_time', str(segment_duration),
            '-c', 'copy',
            '-y',
            output_pattern
        ]
        
        try:
            logger.info(f"Splitting into {num_chunks} chunks of ~{segment_duration}s each")
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Find all created chunks
            chunks = sorted(self.temp_dir.glob(f"chunk_{input_path.stem}_*{input_path.suffix}"))
            logger.info(f"Created {len(chunks)} chunks")
            
            return chunks
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Chunking failed: {e.stderr}")
            return [input_path]
    
    def transcribe_file(self, audio_path: Path) -> Optional[str]:
        """Transcribe a single audio file using Whisper API."""
        logger.info(f"Transcribing: {audio_path.name}")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            'model': 'whisper-1',
            'response_format': 'text'
        }
        
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': (audio_path.name, f, 'audio/mpeg')}
                
                response = requests.post(
                    WHISPER_API_URL,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=300
                )
                
                response.raise_for_status()
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def format_transcript(self, original_name: str, transcripts: List[str], 
                         metadata: Dict) -> str:
        """Format transcripts into markdown with metadata."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        md_content = [
            f"# Audio Transcript: {original_name}",
            f"\n**Processed:** {now}",
            "\n## Metadata",
            f"- **Original Size:** {metadata.get('original_size_mb', 0):.2f} MB",
            f"- **Compressed Size:** {metadata.get('compressed_size_mb', 0):.2f} MB",
            f"- **Chunks:** {metadata.get('chunk_count', 1)}",
            f"- **Compression Ratio:** {metadata.get('compression_ratio', 0):.1f}%",
            "\n---\n",
            "## Transcript\n"
        ]
        
        if len(transcripts) == 1:
            md_content.append(transcripts[0])
        else:
            for i, transcript in enumerate(transcripts, 1):
                md_content.append(f"\n### Part {i} of {len(transcripts)}\n")
                md_content.append(transcript)
                md_content.append("\n")
        
        # Add analysis template
        md_content.extend([
            "\n---\n",
            "## Analysis Template\n",
            "### Speaker Identification",
            "- [ ] Single speaker",
            "- [ ] Multiple speakers (identify below)",
            "\n### Action Items",
            "- [ ] _Add action items here_",
            "\n### Key Decisions",
            "- _List key decisions made_",
            "\n### Follow-ups Required",
            "- _List required follow-up actions_",
            "\n### Notes",
            "_Additional notes and observations_"
        ])
        
        return '\n'.join(md_content)
    
    def find_or_create_folder(self, folder_path: str) -> str:
        """Find or create a folder in Google Drive."""
        parts = folder_path.strip('/').split('/')
        parent_id = 'root'
        
        for part in parts:
            query = f"name='{part}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            try:
                results = self.drive_service.files().list(
                    q=query,
                    fields="files(id, name)"
                ).execute()
                
                items = results.get('files', [])
                
                if items:
                    parent_id = items[0]['id']
                else:
                    # Create folder
                    file_metadata = {
                        'name': part,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_id]
                    }
                    folder = self.drive_service.files().create(
                        body=file_metadata,
                        fields='id'
                    ).execute()
                    parent_id = folder['id']
                    logger.info(f"Created folder: {part}")
                    
            except HttpError as e:
                logger.error(f"Error finding/creating folder {part}: {e}")
                return parent_id
        
        return parent_id
    
    def download_file(self, file_id: str, file_name: str) -> Optional[Path]:
        """Download file from Google Drive."""
        local_path = self.temp_dir / file_name
        
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")
            
            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Downloaded: {file_name}")
            return local_path
            
        except HttpError as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def upload_file(self, local_path: Path, drive_folder_id: str, mime_type: str = 'text/markdown') -> bool:
        """Upload file to Google Drive."""
        try:
            file_metadata = {
                'name': local_path.name,
                'parents': [drive_folder_id]
            }
            
            media = MediaFileUpload(
                str(local_path),
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"Uploaded: {local_path.name} (ID: {file.get('id')})")
            return True
            
        except HttpError as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def move_to_archive(self, file_id: str, archive_folder_id: str) -> bool:
        """Move file to archive folder."""
        try:
            # Get current parents
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move to archive
            self.drive_service.files().update(
                fileId=file_id,
                addParents=archive_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            logger.info(f"Moved file to archive")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to move to archive: {e}")
            return False
    
    def process_file(self, file_id: str, file_name: str, inbox_folder_id: str,
                    archive_folder_id: str, transcript_folder_id: str) -> bool:
        """Process a single audio file through the entire pipeline."""
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {file_name}")
        logger.info(f"{'='*50}")
        
        try:
            # Download file
            local_path = self.download_file(file_id, file_name)
            if not local_path:
                logger.error("Failed to download file")
                self.stats['failed'] += 1
                return False
            
            original_size_mb = local_path.stat().st_size / (1024 * 1024)
            self.stats['total_size_mb'] += original_size_mb
            logger.info(f"Original size: {original_size_mb:.2f} MB")
            
            # Compress if needed
            compressed_path = local_path
            if original_size_mb > MAX_FILE_SIZE_MB:
                compressed_path = self.compress_audio(local_path)
                if not compressed_path:
                    logger.warning("Compression failed, using original")
                    compressed_path = local_path
            
            compressed_size_mb = compressed_path.stat().st_size / (1024 * 1024)
            
            # Chunk if still too large
            chunks = self.chunk_audio(compressed_path)
            
            # Transcribe all chunks
            transcripts = []
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"Transcribing chunk {i}/{len(chunks)}")
                transcript = self.transcribe_file(chunk)
                if transcript:
                    transcripts.append(transcript)
                else:
                    logger.warning(f"Failed to transcribe chunk {i}")
                    transcripts.append("[Transcription failed for this chunk]")
            
            if not any(t != "[Transcription failed for this chunk]" for t in transcripts):
                logger.error("All transcriptions failed")
                self.stats['failed'] += 1
                return False
            
            # Format transcript
            metadata = {
                'original_size_mb': original_size_mb,
                'compressed_size_mb': compressed_size_mb,
                'chunk_count': len(chunks),
                'compression_ratio': (1 - compressed_size_mb / original_size_mb) * 100 if compressed_path != local_path else 0
            }
            
            transcript_content = self.format_transcript(file_name, transcripts, metadata)
            
            # Save transcript locally
            transcript_name = Path(file_name).stem + '_transcript.md'
            transcript_path = self.temp_dir / transcript_name
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_content)
            
            # Upload transcript to Google Drive
            if self.upload_file(transcript_path, transcript_folder_id):
                logger.info(f"Transcript saved: {transcript_name}")
            else:
                logger.error("Failed to upload transcript")
                self.stats['failed'] += 1
                return False
            
            # Move original to archive
            if self.move_to_archive(file_id, archive_folder_id):
                logger.info(f"Archived original file")
            else:
                logger.warning("Failed to archive original file")
            
            # Clean up temp files
            for temp_file in [local_path, compressed_path] + chunks + [transcript_path]:
                if temp_file.exists():
                    temp_file.unlink()
            
            self.stats['processed'] += 1
            logger.info(f"✓ Successfully processed: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error processing {file_name}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return False
    
    def list_audio_files(self, folder_id: str) -> List[Dict]:
        """List all audio files in a folder."""
        audio_extensions = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'wma', 'aac', 'opus', 'webm']
        query_parts = [f"name contains '.{ext}'" for ext in audio_extensions]
        query = f"({' or '.join(query_parts)}) and '{folder_id}' in parents and trashed=false"
        
        try:
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, size)",
                orderBy='createdTime'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} audio files")
            return files
            
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def run(self, watch_mode: bool = False):
        """Main processing loop."""
        logger.info("Starting Google Drive Audio Processor")
        
        # Setup folders
        inbox_folder_id = self.find_or_create_folder('Audio_Inbox')
        archive_folder_id = self.find_or_create_folder('Audio_Inbox/archived')
        transcript_folder_id = self.find_or_create_folder('Audio_Transcripts')
        
        while True:
            # Get list of audio files
            files = self.list_audio_files(inbox_folder_id)
            
            if not files:
                logger.info("No audio files found in inbox")
                if not watch_mode:
                    break
                logger.info("Waiting 60 seconds before checking again...")
                time.sleep(60)
                continue
            
            # Process each file
            for i, file in enumerate(files, 1):
                logger.info(f"\nProcessing file {i}/{len(files)}")
                self.process_file(
                    file['id'],
                    file['name'],
                    inbox_folder_id,
                    archive_folder_id,
                    transcript_folder_id
                )
            
            # Print summary
            self.print_summary()
            
            if not watch_mode:
                break
            
            logger.info("\nWaiting 60 seconds before checking for new files...")
            time.sleep(60)
    
    def print_summary(self):
        """Print processing summary."""
        logger.info("\n" + "="*60)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Files processed: {self.stats['processed']}")
        logger.info(f"Files failed: {self.stats['failed']}")
        logger.info(f"Files skipped: {self.stats['skipped']}")
        
        if self.stats['total_size_mb'] > 0:
            compression_ratio = (1 - self.stats['compressed_size_mb'] / self.stats['total_size_mb']) * 100
            logger.info(f"Total original size: {self.stats['total_size_mb']:.2f} MB")
            logger.info(f"Total compressed size: {self.stats['compressed_size_mb']:.2f} MB")
            logger.info(f"Overall compression: {compression_ratio:.1f}%")
        
        logger.info("="*60)
    
    def cleanup(self):
        """Clean up temporary directory."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to clean up temp dir: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process audio files from Google Drive with automatic transcription'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Run in watch mode (continuously check for new files)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    processor = GoogleDriveAudioProcessor()
    
    try:
        processor.run(watch_mode=args.watch)
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        processor.cleanup()


if __name__ == "__main__":
    main()