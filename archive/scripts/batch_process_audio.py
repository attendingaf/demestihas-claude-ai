#!/usr/bin/env python3
"""
Audio Inbox Batch Processor
Processes all MP3 files: transcribe → extract tasks → save results
"""

import os
import glob
import json
import subprocess
from datetime import datetime
from pathlib import Path

class AudioBatchProcessor:
    def __init__(self, audio_dir="Audio-Inbox"):
        self.audio_dir = audio_dir
        self.vps_host = "root@178.156.170.161"
        self.results_dir = f"{audio_dir}/processed"
        Path(self.results_dir).mkdir(exist_ok=True)
        
    def get_pending_files(self):
        """Find MP3 files without transcripts"""
        mp3_files = glob.glob(f"{self.audio_dir}/*.mp3")
        pending = []
        
        for mp3 in mp3_files:
            transcript_file = mp3.replace('.mp3', '_transcript.txt')
            if not os.path.exists(transcript_file):
                pending.append(mp3)
        
        return pending
    
    def upload_to_vps(self, local_file):
        """Upload file to VPS for processing"""
        filename = os.path.basename(local_file)
        print(f"📤 Uploading {filename}...")
        
        cmd = ["scp", local_file, f"{self.vps_host}:/tmp/"]
        result = subprocess.run(cmd, capture_output=True)
        
        return result.returncode == 0
    
    def transcribe_on_vps(self, filename):
        """Transcribe audio on VPS using Whisper"""
        print(f"🎤 Transcribing {filename}...")
        
        ssh_cmd = f"""
        cd /root/lyco-ai
        export $(grep OPENAI_API_KEY .env | xargs)
        
        python3 << 'EOF'
import os
from openai import OpenAI

client = OpenAI()
with open('/tmp/{filename}', 'rb') as f:
    transcript = client.audio.transcriptions.create(
        model='whisper-1',
        file=f,
        response_format='text'
    )

# Save transcript
with open('/tmp/{filename}_transcript.txt', 'w') as out:
    out.write(transcript)

print(f"Transcribed: {{len(transcript)}} characters")
EOF
        """
        
        result = subprocess.run(
            ["ssh", self.vps_host, ssh_cmd],
            capture_output=True,
            text=True
        )
        
        return "Transcribed:" in result.stdout
    
    def extract_tasks(self, transcript_file):
        """Extract tasks from transcript using Claude"""
        print(f"📝 Extracting tasks...")
        
        with open(transcript_file) as f:
            transcript = f.read()
        
        # Use VPS to call Claude for task extraction
        ssh_cmd = f"""
        cd /root/lyco-ai
        export $(grep ANTHROPIC_API_KEY .env | xargs)
        
        python3 << 'EOF'
import os
import json
from anthropic import Anthropic

transcript = '''{transcript[:8000]}'''  # Limit to 8k chars

client = Anthropic()
response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{{
                "role": "user",
                "content": f"Extract actionable tasks from this transcript. Return as JSON array: {{transcript}}"
            }}]
)

print(response.content[0].text)
EOF
        """
        
        result = subprocess.run(
            ["ssh", self.vps_host, ssh_cmd],
            capture_output=True,
            text=True
        )
        
        # Parse tasks or return empty list
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', result.stdout, re.DOTALL)
            if json_match:
                tasks = json.loads(json_match.group())
            else:
                tasks = []
        except:
            tasks = []
        
        return tasks
    
    def download_transcript(self, filename):
        """Download transcript from VPS"""
        remote_path = f"/tmp/{filename}_transcript.txt"
        local_path = f"{self.audio_dir}/{filename.replace('.mp3', '_transcript.txt')}"
        
        cmd = ["scp", f"{self.vps_host}:{remote_path}", local_path]
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            print(f"✅ Transcript saved: {local_path}")
            return local_path
        return None
    
    def create_summary(self, audio_file, transcript_file, tasks):
        """Create formatted summary of results"""
        summary_file = f"{self.results_dir}/{Path(audio_file).stem}_summary.md"
        
        with open(transcript_file) as f:
            transcript = f.read()
        
        word_count = len(transcript.split())
        
        summary = f"""# Audio Processing Summary
        
**File**: {os.path.basename(audio_file)}
**Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Duration**: ~{word_count // 150} minutes (estimated)
**Words**: {word_count}

## Extracted Tasks

"""
        
        if tasks:
            for i, task in enumerate(tasks, 1):
                if isinstance(task, dict):
                    summary += f"{i}. {task.get('task', task)}\n"
                else:
                    summary += f"{i}. {task}\n"
        else:
            summary += "No specific tasks identified.\n"
        
        summary += f"\n## Transcript Preview\n\n{transcript[:1000]}...\n"
        summary += f"\nFull transcript: {transcript_file}\n"
        
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        print(f"📄 Summary saved: {summary_file}")
        return summary_file
    
    def process_file(self, audio_file):
        """Process single audio file"""
        filename = os.path.basename(audio_file)
        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print('='*60)
        
        # Upload
        if not self.upload_to_vps(audio_file):
            print(f"❌ Failed to upload {filename}")
            return False
        
        # Transcribe
        if not self.transcribe_on_vps(filename):
            print(f"❌ Failed to transcribe {filename}")
            return False
        
        # Download transcript
        transcript_file = self.download_transcript(filename)
        if not transcript_file:
            return False
        
        # Extract tasks
        tasks = self.extract_tasks(transcript_file)
        print(f"📋 Found {len(tasks)} tasks")
        
        # Create summary
        self.create_summary(audio_file, transcript_file, tasks)
        
        return True
    
    def process_all(self):
        """Process all pending audio files"""
        pending = self.get_pending_files()
        
        if not pending:
            print("✅ All files already processed!")
            return
        
        print(f"🎯 Found {len(pending)} files to process:")
        for f in pending:
            print(f"  • {os.path.basename(f)}")
        
        success = 0
        for audio_file in pending:
            if self.process_file(audio_file):
                success += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Batch processing complete!")
        print(f"Processed: {success}/{len(pending)} files")
        print(f"Results in: {self.results_dir}/")
        print('='*60)

def main():
    processor = AudioBatchProcessor()
    processor.process_all()

if __name__ == "__main__":
    main()
