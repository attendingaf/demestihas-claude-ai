# Audio Workflow Package
# Automated pipeline for processing meeting recordings with AI-powered transcription and analysis

__version__ = "1.0.0"
__author__ = "Demestihas AI Team"

from .workflow import AudioWorkflow
from .audio_processor import AudioProcessor
from .google_drive_monitor import GoogleDriveMonitor
from .transcription_service import TranscriptionService
from .ai_formatter import AIScriptFormatter
from .ai_analyzer import MeetingAnalyzer

__all__ = [
    "AudioWorkflow",
    "AudioProcessor", 
    "GoogleDriveMonitor",
    "TranscriptionService",
    "AIScriptFormatter",
    "MeetingAnalyzer"
]
