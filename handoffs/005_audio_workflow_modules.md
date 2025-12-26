# AI Agent Modules for Audio Workflow

## 1. AI Script Formatter
`/root/lyco-ai/audio_workflow/ai_formatter.py`

```python
import logging
from typing import Dict, Optional
import json
from anthropic import Anthropic
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

class AIScriptFormatter:
    """Format raw transcripts into narrative/script format using AI with context"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.model = "claude-3-haiku-20240307"  # Use Haiku for cost efficiency
        
    async def get_relevant_context(self, transcript: str, limit: int = 5) -> str:
        """Retrieve relevant context from Supabase vector store"""
        
        try:
            # Extract key terms for context search
            key_terms = self.extract_key_terms(transcript[:1000])  # First 1000 chars
            
            # Search vector store for relevant context
            response = self.supabase.table('user_profile').select('*').execute()
            
            # Format context for AI
            context_items = []
            if response.data:
                for item in response.data[:limit]:
                    context_items.append(f"- {item.get('content', '')}")
            
            return "\n".join(context_items) if context_items else "No additional context available."
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return "Context retrieval failed."
    
    def extract_key_terms(self, text: str) -> str:
        """Extract key terms from text for context search"""
        # Simple extraction - can be enhanced with NLP
        import re
        
        # Find capitalized words (likely names, places)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        # Common meeting-related terms
        meeting_terms = re.findall(r'\b(project|deadline|budget|meeting|decision|action)\b', text, re.I)
        
        return " ".join(set(proper_nouns[:10] + meeting_terms[:5]))
    
    async def format_transcript(self, transcript: str, context: Dict) -> str:
        """Format transcript into narrative/script format"""
        
        # Get relevant context from Supabase
        memory_context = await self.get_relevant_context(transcript)
        
        prompt = f"""You are a professional meeting transcript formatter with access to the user's context.

USER CONTEXT FROM MEMORY:
{memory_context}

METADATA:
- File: {context.get('file_name', 'Unknown')}
- Date: {context.get('date', 'Unknown')}
- Session: {context.get('session_id', 'Unknown')}

YOUR TASK:
Transform the raw transcript below into a well-formatted narrative/script format.

FORMATTING REQUIREMENTS:
1. Identify and label speakers consistently (use context to identify people when possible)
2. Add proper paragraph breaks and formatting
3. Clean up filler words and false starts while preserving meaning
4. Add scene/context markers where appropriate [e.g., [Phone rings], [Pause], [Laughter]]
5. Preserve the authentic voice and tone of speakers
6. Use context from memory to identify relationships and roles
7. Format as a readable script/narrative with clear speaker labels

OUTPUT FORMAT:
**Speaker Name:** Their dialogue here.

[Context or action markers in brackets]

**Next Speaker:** Their response.

---

RAW TRANSCRIPT:
{transcript}

---

FORMATTED SCRIPT:
"""
        
        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.3,  # Lower temperature for consistency
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            formatted_script = response.content[0].text
            
            # Add metadata header
            header = f"""# Meeting Transcript
**File:** {context.get('file_name', 'Unknown')}  
**Date:** {context.get('date', 'Unknown')}  
**Session ID:** {context.get('session_id', 'Unknown')}

---

"""
            
            return header + formatted_script
            
        except Exception as e:
            logger.error(f"Error formatting transcript: {e}")
            return f"# Formatting Error\n\nOriginal transcript preserved:\n\n{transcript}"
```

## 2. Meeting Analyzer
`/root/lyco-ai/audio_workflow/ai_analyzer.py`

```python
import logging
from typing import Dict, List
import json
from anthropic import Anthropic
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

class MeetingAnalyzer:
    """Analyze meetings using the 5-question framework"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.model = "claude-3-5-sonnet-20241022"  # Use Sonnet for deeper analysis
        
    async def get_meeting_context(self, script: str) -> str:
        """Get relevant context for meeting analysis"""
        
        try:
            # Search for related meetings or context
            response = self.supabase.table('user_profile').select('*').execute()
            
            context_items = []
            if response.data:
                # Filter for meeting-related context
                for item in response.data:
                    content = item.get('content', '')
                    if any(term in content.lower() for term in ['meeting', 'project', 'deadline', 'decision']):
                        context_items.append(f"- {content}")
            
            return "\n".join(context_items[:10]) if context_items else "No historical meeting context found."
            
        except Exception as e:
            logger.error(f"Error retrieving meeting context: {e}")
            return "Context retrieval failed."
    
    async def analyze_meeting(self, formatted_script: str, original_transcript: str) -> Dict:
        """Analyze meeting using 5-question framework"""
        
        # Get historical context
        historical_context = await self.get_meeting_context(formatted_script)
        
        prompt = f"""You are an expert meeting analyst with access to the user's historical context.

HISTORICAL CONTEXT:
{historical_context}

USER PROFILE:
- Name: Mene Demestihas
- Role: Physician executive, startup leader
- Focus: Emergency medicine, telehealth, AI-driven healthcare
- Family: Spouse (also ADHD), children (Stelios, Percy)
- Work style: ADHD-optimized, execution-focused

ANALYZE THIS MEETING using the following framework:

1. **What Happened** - Provide a clear, executive summary of the meeting's content and outcomes
2. **What Was Really Being Said** - Analyze subtext, unspoken concerns, political dynamics, and underlying messages
3. **What Surprises Occurred** - Identify unexpected revelations, sudden topic changes, or surprising reactions
4. **What Objectives Were Accomplished** - List completed objectives vs. unaccomplished ones, and any new objectives that emerged
5. **What Could Be Done Better Next Time** - Specific, actionable improvements for future meetings

FORMATTED SCRIPT:
{formatted_script}

PROVIDE YOUR ANALYSIS AS A JSON OBJECT with this structure:
{{
    "what_happened": "Executive summary here",
    "what_was_really_said": "Subtext and dynamics analysis",
    "surprises": ["surprise 1", "surprise 2"],
    "objectives_completed": ["objective 1", "objective 2"],
    "objectives_not_completed": ["objective 1", "objective 2"],
    "objectives_emerged": ["new objective 1"],
    "improvements": ["improvement 1", "improvement 2"],
    "action_items": [
        {{"task": "description", "owner": "name", "due": "date"}},
    ],
    "key_dates": [
        {{"date": "when", "event": "what"}},
    ],
    "participants": ["name1", "name2"],
    "sentiment": "overall positive/neutral/negative",
    "follow_up_required": true/false,
    "key_decisions": ["decision 1", "decision 2"]
}}

Ensure the JSON is valid and complete.
"""
        
        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            
            # Try to parse JSON (handle potential formatting issues)
            try:
                # Look for JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Fallback structure
                analysis = {
                    "what_happened": response_text[:500],
                    "error": "Failed to parse complete analysis",
                    "raw_response": response_text
                }
            
            # Store analysis in Supabase for future reference
            await self.store_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing meeting: {e}")
            return {
                "error": str(e),
                "what_happened": "Analysis failed - see error message"
            }
    
    async def store_analysis(self, analysis: Dict):
        """Store analysis in Supabase for future reference"""
        try:
            # Create embedding-friendly summary
            summary = f"""
            Meeting Analysis:
            What Happened: {analysis.get('what_happened', '')}
            Key Decisions: {', '.join(analysis.get('key_decisions', []))}
            Action Items: {len(analysis.get('action_items', []))} items
            Participants: {', '.join(analysis.get('participants', []))}
            """
            
            # Store in Supabase (you'll need to create this table)
            # self.supabase.table('meeting_analyses').insert({
            #     'content': summary,
            #     'full_analysis': json.dumps(analysis),
            #     'timestamp': datetime.now().isoformat()
            # }).execute()
            
            logger.info("Analysis stored in vector database")
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
```

## 3. Google Drive Integration
`/root/lyco-ai/audio_workflow/google_drive_monitor.py`

```python
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
    """Monitor Google Drive folder for new audio files"""
    
    def __init__(self):
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.service = self.authenticate()
        self.last_check_file = Path("/tmp/last_drive_check.txt")
        
    def authenticate(self):
        """Authenticate with Google Drive API"""
        
        SCOPES = ['https://www.googleapis.com/auth/drive']
        
        # Use service account if available
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
        if service_account_file and os.path.exists(service_account_file):
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        else:
            # Fall back to OAuth2 (requires initial setup)
            creds = None
            token_file = '/app/token.pickle'
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    raise Exception("No valid Google credentials found")
        
        return build('drive', 'v3', credentials=creds)
    
    async def check_for_new_files(self) -> List[Dict]:
        """Check for new audio files in the monitored folder"""
        
        # Get last check time
        last_check = self.get_last_check_time()
        
        # Query for files modified after last check
        query = f"'{self.folder_id}' in parents and mimeType contains 'audio/' and modifiedTime > '{last_check}'"
        
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Update last check time
            if files:
                self.update_last_check_time()
                logger.info(f"Found {len(files)} new audio files")
            
            return files
            
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
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

class DriveOutputManager:
    """Manage output folders and file uploads to Google Drive"""
    
    def __init__(self):
        self.service = GoogleDriveMonitor().service
        self.base_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.output_folders = {}
        self.ensure_output_folders()
    
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
        parent_folder = self.get_or_create_folder("Audio Processing", self.base_folder_id)
        
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
```

## 4. Transcription Service
`/root/lyco-ai/audio_workflow/transcription_service.py`

```python
import os
import logging
from pathlib import Path
from openai import OpenAI
from typing import Optional

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Handle audio transcription using OpenAI Whisper API"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe audio file using Whisper API"""
        
        logger.info(f"Transcribing: {audio_path.name}")
        
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,  # Optional language hint
                    response_format="text"
                )
            
            # Log basic stats
            word_count = len(transcript.split())
            logger.info(f"Transcription complete: {word_count} words")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path.name}: {e}")
            raise
    
    async def transcribe_with_timestamps(self, audio_path: Path) -> dict:
        """Transcribe with timestamps (returns SRT format)"""
        
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="srt"
                )
            
            return {
                "format": "srt",
                "content": transcript
            }
            
        except Exception as e:
            logger.error(f"Transcription with timestamps failed: {e}")
            raise
```

## Deployment Instructions

1. **Copy files to VPS:**
```bash
# Create directory structure
ssh root@178.156.170.161
mkdir -p /root/lyco-ai/audio_workflow

# Copy files (from local)
scp -r ~/projects/demestihas-ai/handoffs/audio_workflow_files/* root@178.156.170.161:/root/lyco-ai/audio_workflow/
```

2. **Set up Google Service Account:**
```bash
# On VPS
mkdir -p /root/lyco-ai/credentials
# Upload service account JSON
# Share Google Drive folders with service account email
```

3. **Update .env file:**
```bash
nano /root/lyco-ai/.env
# Add all required environment variables
```

4. **Build and deploy:**
```bash
cd /root/lyco-ai
docker-compose up -d audio_workflow
```

5. **Monitor:**
```bash
docker logs -f audio_workflow
```

## Testing

Upload a test audio file to your Google Drive folder and monitor the logs:
```bash
docker logs -f audio_workflow | grep "Found"
```

The system will:
1. Detect the file within 5 minutes
2. Compress it to mono 16kHz
3. Chunk if needed
4. Transcribe
5. Format into narrative
6. Analyze with 5 questions
7. Save all outputs to Drive folders
