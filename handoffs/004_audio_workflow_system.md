# Audio Processing Workflow System

## Overview
Automated pipeline for processing meeting recordings with AI-powered transcription and analysis.

## System Architecture

```
Google Drive Monitor
        │
        ▼
Audio Compression/Chunking
        │
        ▼
Whisper Transcription
        │
        ▼
AI Script Formatter (Supabase RAG)
        │
        ▼
AI Meeting Analyzer (5 Questions)
        │
        ▼
Google Drive Output Storage
```

## Folder Structure

```
Google Drive:
/Uploaded recordings/           (INPUT - monitored)
/Audio Processing/
  ├── 01_compressed/           (compressed files)
  ├── 02_chunks/               (if file >25MB)
  ├── 03_transcripts/          (raw transcriptions)
  ├── 04_formatted_scripts/    (narrative format)
  └── 05_analysis/             (meeting analysis)
```

## Implementation Files

### 1. Main Workflow Orchestrator
`/root/lyco-ai/audio_workflow/workflow.py`

```python
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
import hashlib

from google_drive_monitor import GoogleDriveMonitor
from audio_processor import AudioProcessor
from transcription_service import TranscriptionService
from ai_formatter import AIScriptFormatter
from ai_analyzer import MeetingAnalyzer
from drive_output_manager import DriveOutputManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioWorkflow:
    """Main orchestrator for audio processing pipeline"""
    
    def __init__(self):
        self.drive_monitor = GoogleDriveMonitor()
        self.audio_processor = AudioProcessor()
        self.transcriber = TranscriptionService()
        self.formatter = AIScriptFormatter()
        self.analyzer = MeetingAnalyzer()
        self.output_manager = DriveOutputManager()
        
        # Local working directory
        self.work_dir = Path("/root/lyco-ai/audio_workflow/temp")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Track processed files to avoid duplicates
        self.processed_files = self.load_processed_files()
    
    def load_processed_files(self) -> set:
        """Load list of already processed files"""
        cache_file = self.work_dir / "processed_files.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_processed_files(self):
        """Save list of processed files"""
        cache_file = self.work_dir / "processed_files.json"
        with open(cache_file, 'w') as f:
            json.dump(list(self.processed_files), f)
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate hash for file to track uniqueness"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    
    async def process_audio_file(self, file_info: Dict) -> Dict:
        """Process a single audio file through the entire pipeline"""
        
        file_id = file_info['id']
        file_name = file_info['name']
        
        # Check if already processed
        if file_id in self.processed_files:
            logger.info(f"File {file_name} already processed, skipping")
            return {"status": "skipped", "file": file_name}
        
        logger.info(f"Starting processing for: {file_name}")
        
        try:
            # Create session folder
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + file_id[:8]
            session_dir = self.work_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # Step 1: Download from Google Drive
            logger.info("Step 1: Downloading file")
            local_path = await self.drive_monitor.download_file(
                file_id, 
                session_dir / file_name
            )
            
            # Step 2: Compress audio (mono, 16kHz)
            logger.info("Step 2: Compressing audio")
            compressed_path = await self.audio_processor.compress_audio(
                local_path,
                output_dir=session_dir
            )
            
            # Upload compressed version back to Drive (replace original)
            await self.output_manager.upload_to_folder(
                compressed_path,
                "01_compressed",
                replace_original=True,
                original_file_id=file_id
            )
            
            # Step 3: Check size and chunk if needed
            chunks = []
            if os.path.getsize(compressed_path) > 25 * 1024 * 1024:  # 25MB
                logger.info("Step 3: File >25MB, chunking")
                chunks = await self.audio_processor.chunk_audio(
                    compressed_path,
                    max_size_mb=20,  # Leave buffer
                    output_dir=session_dir / "chunks"
                )
                
                # Upload chunks
                for chunk in chunks:
                    await self.output_manager.upload_to_folder(
                        chunk,
                        "02_chunks"
                    )
            else:
                chunks = [compressed_path]
            
            # Step 4: Transcribe each chunk
            logger.info("Step 4: Transcribing audio")
            transcripts = []
            for i, chunk in enumerate(chunks):
                transcript = await self.transcriber.transcribe(chunk)
                transcripts.append(transcript)
                
                # Save individual transcript
                transcript_file = session_dir / f"transcript_part_{i}.txt"
                with open(transcript_file, 'w') as f:
                    f.write(transcript)
            
            # Combine transcripts
            full_transcript = "\n\n".join(transcripts)
            transcript_path = session_dir / "full_transcript.txt"
            with open(transcript_path, 'w') as f:
                f.write(full_transcript)
            
            await self.output_manager.upload_to_folder(
                transcript_path,
                "03_transcripts"
            )
            
            # Step 5: Format into narrative/script
            logger.info("Step 5: Formatting transcript into narrative")
            formatted_script = await self.formatter.format_transcript(
                full_transcript,
                context={
                    "file_name": file_name,
                    "date": datetime.now().isoformat(),
                    "session_id": session_id
                }
            )
            
            script_path = session_dir / "formatted_script.md"
            with open(script_path, 'w') as f:
                f.write(formatted_script)
            
            await self.output_manager.upload_to_folder(
                script_path,
                "04_formatted_scripts"
            )
            
            # Step 6: Analyze meeting
            logger.info("Step 6: Analyzing meeting")
            analysis = await self.analyzer.analyze_meeting(
                formatted_script,
                original_transcript=full_transcript
            )
            
            analysis_path = session_dir / "meeting_analysis.json"
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            # Create readable analysis document
            analysis_doc = self.create_analysis_document(analysis, file_name)
            doc_path = session_dir / "meeting_analysis.md"
            with open(doc_path, 'w') as f:
                f.write(analysis_doc)
            
            await self.output_manager.upload_to_folder(
                doc_path,
                "05_analysis"
            )
            
            # Mark as processed
            self.processed_files.add(file_id)
            self.save_processed_files()
            
            # Clean up local files (keep for 24h for debugging)
            # self.schedule_cleanup(session_dir, hours=24)
            
            logger.info(f"✅ Completed processing: {file_name}")
            
            return {
                "status": "success",
                "file": file_name,
                "session_id": session_id,
                "transcript_length": len(full_transcript),
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_name}: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "file": file_name,
                "error": str(e)
            }
    
    def create_analysis_document(self, analysis: Dict, file_name: str) -> str:
        """Create formatted markdown document from analysis"""
        
        doc = f"""# Meeting Analysis: {file_name}
        
**Date Processed:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Session ID:** {analysis.get('session_id', 'N/A')}

---

## 1. What Happened
{analysis.get('what_happened', 'No summary available')}

## 2. What Was Really Being Said
{analysis.get('what_was_really_said', 'No subtext analysis available')}

## 3. Surprises That Occurred
{self._format_list(analysis.get('surprises', []))}

## 4. Objectives Accomplished
### ✅ Completed
{self._format_list(analysis.get('objectives_completed', []))}

### ❌ Not Completed
{self._format_list(analysis.get('objectives_not_completed', []))}

## 5. What Could Be Done Better Next Time
{self._format_list(analysis.get('improvements', []))}

---

## Key Action Items
{self._format_action_items(analysis.get('action_items', []))}

## Important Dates
{self._format_dates(analysis.get('key_dates', []))}
"""
        return doc
    
    def _format_list(self, items: List) -> str:
        if not items:
            return "- None identified"
        return "\n".join([f"- {item}" for item in items])
    
    def _format_action_items(self, items: List[Dict]) -> str:
        if not items:
            return "- No action items identified"
        
        formatted = []
        for item in items:
            owner = item.get('owner', 'Unassigned')
            task = item.get('task', 'No description')
            due = item.get('due', 'No deadline')
            formatted.append(f"- **{owner}**: {task} (Due: {due})")
        
        return "\n".join(formatted)
    
    def _format_dates(self, dates: List[Dict]) -> str:
        if not dates:
            return "- No key dates identified"
        
        formatted = []
        for date in dates:
            when = date.get('date', 'Unknown')
            what = date.get('event', 'No description')
            formatted.append(f"- **{when}**: {what}")
        
        return "\n".join(formatted)
    
    async def run(self):
        """Main workflow loop"""
        logger.info("Starting Audio Workflow System")
        
        while True:
            try:
                # Check for new files
                new_files = await self.drive_monitor.check_for_new_files()
                
                if new_files:
                    logger.info(f"Found {len(new_files)} new files to process")
                    
                    for file_info in new_files:
                        await self.process_audio_file(file_info)
                
                # Wait before next check (5 minutes)
                await asyncio.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Shutting down Audio Workflow System")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    workflow = AudioWorkflow()
    asyncio.run(workflow.run())
```

### 2. Audio Processor Module
`/root/lyco-ai/audio_workflow/audio_processor.py`

```python
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
import math

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handle audio compression and chunking"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # Assumes ffmpeg is in PATH
    
    async def compress_audio(self, input_path: Path, output_dir: Path) -> Path:
        """Compress audio to mono 16kHz MP3"""
        
        output_path = output_dir / f"compressed_{input_path.name}"
        
        # Change extension to .mp3 if different
        if output_path.suffix != '.mp3':
            output_path = output_path.with_suffix('.mp3')
        
        cmd = [
            self.ffmpeg_path,
            '-i', str(input_path),
            '-ac', '1',           # Mono
            '-ar', '16000',       # 16kHz sample rate
            '-b:a', '32k',        # Lower bitrate for speech
            '-y',                 # Overwrite output
            str(output_path)
        ]
        
        logger.info(f"Compressing: {input_path.name}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg compression failed: {result.stderr}")
        
        # Log size reduction
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        compressed_size = os.path.getsize(output_path) / (1024 * 1024)
        reduction = (1 - compressed_size/original_size) * 100
        
        logger.info(f"Compressed {original_size:.1f}MB → {compressed_size:.1f}MB ({reduction:.1f}% reduction)")
        
        return output_path
    
    async def chunk_audio(
        self, 
        input_path: Path, 
        max_size_mb: int = 20,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """Split audio into chunks smaller than max_size_mb"""
        
        if output_dir is None:
            output_dir = input_path.parent / "chunks"
        output_dir.mkdir(exist_ok=True)
        
        # Get duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(input_path)
        ]
        
        result = subprocess.run(duration_cmd, capture_output=True, text=True)
        total_duration = float(result.stdout.strip())
        
        # Calculate chunk duration based on file size
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        num_chunks = math.ceil(file_size_mb / max_size_mb)
        chunk_duration = total_duration / num_chunks
        
        logger.info(f"Splitting into {num_chunks} chunks of ~{chunk_duration:.1f} seconds")
        
        chunks = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            output_path = output_dir / f"{input_path.stem}_chunk_{i:03d}.mp3"
            
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-c', 'copy',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to create chunk {i}: {result.stderr}")
                continue
            
            chunks.append(output_path)
            logger.info(f"Created chunk {i+1}/{num_chunks}: {output_path.name}")
        
        return chunks
    
    async def get_audio_info(self, file_path: Path) -> Dict:
        """Get audio file information"""
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            return {}
```

### 3. Docker Compose Addition
`/root/lyco-ai/docker-compose.yml` (add this service)

```yaml
  audio_workflow:
    build: 
      context: .
      dockerfile: Dockerfile.audio
    container_name: audio_workflow
    restart: unless-stopped
    volumes:
      - ./audio_workflow:/app
      - ./logs:/app/logs
      - /tmp/audio_work:/tmp/audio_work
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
    depends_on:
      - redis
    networks:
      - lyco-network
```

### 4. Dockerfile for Audio Service
`/root/lyco-ai/Dockerfile.audio`

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.audio.txt .
RUN pip install --no-cache-dir -r requirements.audio.txt

# Copy application code
COPY audio_workflow/ ./audio_workflow/

# Create necessary directories
RUN mkdir -p /app/logs /tmp/audio_work

# Run the workflow
CMD ["python", "-m", "audio_workflow.workflow"]
```

### 5. Requirements File
`/root/lyco-ai/requirements.audio.txt`

```
# Core
asyncio
aiohttp
aiofiles

# Google APIs
google-api-python-client==2.88.0
google-auth==2.19.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.0

# OpenAI
openai==1.12.0

# Anthropic
anthropic==0.18.1

# Supabase
supabase==2.0.3

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
httpx==0.25.0
tenacity==8.2.3
```

## Environment Variables Required

Add to `/root/lyco-ai/.env`:

```bash
# Google Drive
GOOGLE_DRIVE_FOLDER_ID="1HuuRO8xMgCksqxf5Aj_-EWVMJJTR9sj7"
GOOGLE_SERVICE_ACCOUNT_PATH="/app/credentials/google-service-account.json"

# OpenAI
OPENAI_API_KEY="sk-..."

# Anthropic (for AI agents)
ANTHROPIC_API_KEY="sk-ant-..."

# Supabase (for vector memory)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
```

## Setup Instructions

1. **Create Google Service Account**
   - Go to Google Cloud Console
   - Create service account with Drive API access
   - Download JSON key
   - Share Drive folders with service account email

2. **Install FFmpeg on VPS**
   ```bash
   apt-get update && apt-get install -y ffmpeg
   ```

3. **Deploy the service**
   ```bash
   cd /root/lyco-ai
   docker-compose up -d audio_workflow
   ```

4. **Monitor logs**
   ```bash
   docker logs -f audio_workflow
   ```

## Key Features

1. **Automatic Compression**: All files compressed to mono 16kHz
2. **Smart Chunking**: Only chunks if >25MB
3. **Parallel Processing**: Each step saves to Drive for QA
4. **Memory Integration**: Uses Supabase for context
5. **Comprehensive Analysis**: 5-question framework
6. **Error Recovery**: Tracks processed files, resumes on restart

## Monitoring & Maintenance

```bash
# Check service status
docker ps | grep audio_workflow

# View recent logs
docker logs --tail 100 audio_workflow

# Restart service
docker restart audio_workflow

# Clear processed files cache (to reprocess)
docker exec audio_workflow rm /app/temp/processed_files.json
```
