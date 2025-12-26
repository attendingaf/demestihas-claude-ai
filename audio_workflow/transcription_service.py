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
