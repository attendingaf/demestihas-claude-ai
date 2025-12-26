#!/usr/bin/env python3
"""
Quick audio transcription using OpenAI Whisper API
Usage: python quick_transcribe.py <audio_file_path>
"""

import sys
import os
from openai import OpenAI

# You'll need to set your OpenAI API key
# Either set OPENAI_API_KEY environment variable or replace here
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
)

def transcribe_audio(file_path):
    """Transcribe audio file using OpenAI Whisper API"""
    
    # Check file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return None
    
    # Check file size (25MB limit for Whisper)
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
    if file_size > 25:
        print(f"Warning: File is {file_size:.1f}MB. Whisper API limit is 25MB")
        print("Consider compressing or splitting the file")
    
    print(f"Transcribing {file_path} ({file_size:.1f}MB)...")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        return transcript
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python quick_transcribe.py <audio_file_path>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Transcribe
    transcript = transcribe_audio(audio_file)
    
    if transcript:
        # Save to file
        output_file = audio_file.rsplit('.', 1)[0] + '_transcript.txt'
        with open(output_file, 'w') as f:
            f.write(transcript)
        
        print(f"\n✅ Transcription saved to: {output_file}")
        print("\n--- TRANSCRIPT ---")
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
    else:
        print("❌ Transcription failed")

if __name__ == "__main__":
    main()
