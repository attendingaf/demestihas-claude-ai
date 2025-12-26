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
        
        # Local working directory
        self.work_dir = Path("/tmp/audio_work")
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
            
            # Upload compressed version back to Drive
            await self.drive_monitor.upload_to_folder(
                compressed_path,
                "01_compressed"
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
                    await self.drive_monitor.upload_to_folder(
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
            
            await self.drive_monitor.upload_to_folder(
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
            
            await self.drive_monitor.upload_to_folder(
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
            
            await self.drive_monitor.upload_to_folder(
                doc_path,
                "05_analysis"
            )
            
            # Mark as processed
            self.processed_files.add(file_id)
            self.save_processed_files()
            
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
        
        # Initial debug check - list all files in folder
        logger.info("Performing initial folder scan...")
        all_files = await self.drive_monitor.check_all_files()
        logger.info(f"Initial scan complete: {len(all_files)} files found")
        
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
