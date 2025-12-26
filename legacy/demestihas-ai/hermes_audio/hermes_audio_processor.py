#!/usr/bin/env python3
"""
Hermes Audio Processing System
Multi-agent architecture: Hermes handles audio/communication, Lyco handles tasks

Usage:
1. Family emails audio files to hermes.audio@gmail.com
2. Hermes checks email every 5 minutes  
3. Processes audio through transcription and analysis pipeline
4. Sends processed results to Lyco for task extraction
5. Results uploaded to Google Drive for family access

Hermes = Communication specialist (audio, email, messaging)
Lyco = Task management specialist (tasks, scheduling, Notion)
"""

import os
import imaplib
import email
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
import json
import sys

# Add shared audio_workflow modules to path
sys.path.append('/app/shared')

# Reuse existing workflow components
from audio_processor import AudioProcessor
from transcription_service import TranscriptionService  
from ai_formatter import AIScriptFormatter
from ai_analyzer import MeetingAnalyzer
from google_drive_monitor import GoogleDriveMonitor  # For uploads only

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HermesAudioProcessor:
    """Hermes: Communication specialist for audio processing"""
    
    def __init__(self):
        # Email configuration
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        self.email_address = os.getenv("HERMES_EMAIL_ADDRESS")  # hermes.audio@gmail.com
        self.email_password = os.getenv("HERMES_EMAIL_PASSWORD")  # App password
        
        # Processing components (reuse existing)
        self.audio_processor = AudioProcessor()
        self.transcriber = TranscriptionService()
        self.formatter = AIScriptFormatter()
        self.analyzer = MeetingAnalyzer()
        self.drive_uploader = GoogleDriveMonitor()  # For uploads only
        
        # Multi-agent integration
        self.lyco_api_url = os.getenv("LYCO_API_URL", "http://localhost:8000")  # For task extraction
        
        # Local working directory
        self.work_dir = Path("/tmp/hermes_audio_work")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Track processed emails
        self.processed_emails = self.load_processed_emails()
        
    def load_processed_emails(self) -> set:
        """Load list of already processed email IDs"""
        cache_file = self.work_dir / "hermes_processed_emails.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_processed_emails(self):
        """Save list of processed email IDs"""
        cache_file = self.work_dir / "hermes_processed_emails.json" 
        with open(cache_file, 'w') as f:
            json.dump(list(self.processed_emails), f)
    
    async def send_to_lyco(self, analysis: Dict, context: Dict) -> bool:
        """Send processed audio analysis to Lyco for task extraction"""
        try:
            import aiohttp
            
            payload = {
                'source': 'hermes_audio',
                'content': analysis.get('formatted_script', ''),
                'analysis': analysis,
                'context': context,
                'sender': context.get('sender', 'unknown')
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.lyco_api_url}/process_hermes_content", 
                                      json=payload) as response:
                    if response.status == 200:
                        logger.info("✅ Sent audio analysis to Lyco for task extraction")
                        return True
                    else:
                        logger.warning(f"⚠️ Lyco API returned {response.status}")
                        return False
                        
        except Exception as e:
            logger.warning(f"⚠️ Could not reach Lyco API: {e}")
            return False
    
    def connect_to_email(self):
        """Connect to email server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to email: {e}")
            raise
    
    def check_for_audio_emails(self) -> List[Dict]:
        """Check for new emails with audio attachments"""
        try:
            mail = self.connect_to_email()
            
            # Search for unseen emails
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            audio_emails = []
            
            for email_id in email_ids:
                email_id_str = email_id.decode()
                
                # Skip if already processed
                if email_id_str in self.processed_emails:
                    continue
                
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Check for audio attachments
                audio_attachments = []
                for part in email_message.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        if filename and any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.aac', '.ogg']):
                            audio_attachments.append({
                                'filename': filename,
                                'data': part.get_payload(decode=True),
                                'size': len(part.get_payload(decode=True))
                            })
                
                if audio_attachments:
                    audio_emails.append({
                        'email_id': email_id_str,
                        'subject': email_message.get('Subject', 'No Subject'),
                        'from': email_message.get('From', 'Unknown'),
                        'date': email_message.get('Date', 'Unknown'),
                        'attachments': audio_attachments
                    })
                    logger.info(f"Found email with {len(audio_attachments)} audio files: {email_message.get('Subject')}")
            
            mail.close()
            mail.logout()
            return audio_emails
            
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
            return []
    
    async def process_email_audio(self, email_info: Dict) -> Dict:
        """Process audio files from an email"""
        
        email_id = email_info['email_id']
        subject = email_info['subject']
        sender = email_info['from']
        
        logger.info(f"Processing email from {sender}: {subject}")
        
        try:
            # Create session folder
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + email_id[:8]
            session_dir = self.work_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            results = []
            
            # Process each audio attachment
            for i, attachment in enumerate(email_info['attachments']):
                filename = attachment['filename']
                logger.info(f"Processing attachment {i+1}/{len(email_info['attachments'])}: {filename}")
                
                # Save attachment to disk
                attachment_path = session_dir / filename
                with open(attachment_path, 'wb') as f:
                    f.write(attachment['data'])
                
                # Process through the same pipeline as Google Drive workflow
                result = await self.process_single_audio_file(
                    attachment_path, 
                    session_dir,
                    context={
                        'source': 'hermes_email',
                        'sender': sender,
                        'subject': subject,
                        'email_date': email_info['date'],
                        'filename': filename
                    }
                )
                results.append(result)
            
            # Mark email as processed
            self.processed_emails.add(email_id)
            self.save_processed_emails()
            
            # Send confirmation email (optional)
            await self.send_confirmation_email(sender, subject, len(results))
            
            logger.info(f"✅ Completed processing email: {subject}")
            return {
                'status': 'success',
                'email_subject': subject,
                'sender': sender,
                'files_processed': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error processing email {subject}: {e}")
            return {
                'status': 'error',
                'email_subject': subject,
                'error': str(e)
            }
    
    async def process_single_audio_file(self, file_path: Path, session_dir: Path, context: Dict) -> Dict:
        """Process a single audio file (same pipeline as Google Drive)"""
        
        try:
            # Step 1: Compress audio
            logger.info(f"Step 1: Compressing {file_path.name}")
            compressed_path = await self.audio_processor.compress_audio(
                file_path, 
                output_dir=session_dir
            )
            
            # Upload compressed version to Drive
            await self.drive_uploader.upload_to_folder(
                compressed_path,
                "01_compressed"
            )
            
            # Step 2: Chunk if needed (same logic as before)
            chunks = []
            if os.path.getsize(compressed_path) > 25 * 1024 * 1024:  # 25MB
                logger.info("Step 2: File >25MB, chunking")
                chunks = await self.audio_processor.chunk_audio(
                    compressed_path,
                    max_size_mb=20,
                    output_dir=session_dir / "chunks"
                )
                
                for chunk in chunks:
                    await self.drive_uploader.upload_to_folder(chunk, "02_chunks")
            else:
                chunks = [compressed_path]
            
            # Step 3: Transcribe
            logger.info("Step 3: Transcribing audio")
            transcripts = []
            for chunk in chunks:
                transcript = await self.transcriber.transcribe(chunk)
                transcripts.append(transcript)
            
            full_transcript = "\n\n".join(transcripts)
            transcript_path = session_dir / f"{file_path.stem}_transcript.txt"
            with open(transcript_path, 'w') as f:
                f.write(full_transcript)
            
            await self.drive_uploader.upload_to_folder(transcript_path, "03_transcripts")
            
            # Step 4: Format script
            logger.info("Step 4: Formatting transcript")
            formatted_script = await self.formatter.format_transcript(
                full_transcript,
                context=context
            )
            
            script_path = session_dir / f"{file_path.stem}_script.md"
            with open(script_path, 'w') as f:
                f.write(formatted_script)
                
            await self.drive_uploader.upload_to_folder(script_path, "04_formatted_scripts")
            
            # Step 5: Analyze
            logger.info("Step 5: Analyzing meeting")
            analysis = await self.analyzer.analyze_meeting(
                formatted_script,
                original_transcript=full_transcript
            )
            
            # Create analysis document
            analysis_doc = self.create_analysis_document(analysis, file_path.name, context)
            doc_path = session_dir / f"{file_path.stem}_analysis.md"
            with open(doc_path, 'w') as f:
                f.write(analysis_doc)
                
            await self.drive_uploader.upload_to_folder(doc_path, "05_analysis")
            
            return {
                'status': 'success',
                'filename': file_path.name,
                'transcript_length': len(full_transcript),
                'analysis': analysis,
                'formatted_script': formatted_script
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return {
                'status': 'error', 
                'filename': file_path.name,
                'error': str(e)
            }
    
    def create_analysis_document(self, analysis: Dict, filename: str, context: Dict) -> str:
        """Create formatted analysis document with email context"""
        
        doc = f"""# 🎧 Hermes Audio Analysis: {filename}

**Source**: Email from {context.get('sender', 'Unknown')}  
**Subject**: {context.get('subject', 'No Subject')}  
**Email Date**: {context.get('email_date', 'Unknown')}  
**Processed by**: Hermes Audio Specialist  
**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

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

## 🎯 Key Action Items
{self._format_action_items(analysis.get('action_items', []))}

## 📅 Important Dates
{self._format_dates(analysis.get('key_dates', []))}

---
*Processed by Hermes • Audio Communication Specialist*  
*Tasks extracted and sent to Lyco for management*
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
    
    async def send_confirmation_email(self, recipient: str, original_subject: str, files_count: int):
        """Send confirmation that files were processed by Hermes"""
        # This would integrate with SMTP to send confirmations
        # For now, just log
        logger.info(f"📧 Hermes would send confirmation to {recipient}: Processed {files_count} files from '{original_subject}'")
    
    async def run(self):
        """Main Hermes email monitoring loop"""
        logger.info("🚀 Starting Hermes Audio Processing System")
        logger.info("📨 Monitoring hermes.audio@gmail.com for audio attachments")
        
        while True:
            try:
                # Check for new audio emails
                audio_emails = self.check_for_audio_emails()
                
                if audio_emails:
                    logger.info(f"📧 Hermes found {len(audio_emails)} emails with audio attachments")
                    
                    for email_info in audio_emails:
                        result = await self.process_email_audio(email_info)
                        
                        # Send to Lyco for task extraction if successful
                        if result['status'] == 'success' and result.get('results'):
                            for file_result in result['results']:
                                if file_result.get('analysis'):
                                    await self.send_to_lyco(file_result['analysis'], {
                                        'sender': result['sender'],
                                        'subject': result['email_subject'],
                                        'filename': file_result.get('filename')
                                    })
                else:
                    logger.info("📭 Hermes: No new audio emails found")
                
                # Wait 5 minutes before checking again
                await asyncio.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down Hermes Audio Processing System")
                break
            except Exception as e:
                logger.error(f"❌ Error in Hermes email monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    processor = HermesAudioProcessor()
    asyncio.run(processor.run())
