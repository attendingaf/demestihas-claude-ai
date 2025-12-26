# Handoff #016: Complete Hermes Email & Audio Batch Processor

**Created**: August 25, 2025, 23:00 UTC
**Type**: Implementation (Dev-Sonnet)
**Priority**: HIGH - User needs working audio processing TODAY
**Estimated Time**: 45 minutes
**Assigned to**: Claude Sonnet Developer

---

## 🎯 Atomic Scope

**TWO deliverables in priority order:**

1. **Start Hermes email container** (5 minutes)
   - Container already configured, just needs startup
   - Verify it's processing emails

2. **Create Audio-Inbox batch processor** (40 minutes)
   - Script to process all MP3 files in Audio-Inbox/
   - Transcribe → Extract tasks → Format output
   - Save transcripts and task lists

---

## 📍 Current State

### Hermes Status (from Thread #14)
- ✅ Gmail created: hermesaudio444@gmail.com
- ✅ Password in VPS .env: ahd5egm2gvf!akr9UPY  
- ✅ docker-compose.yml has hermes_audio service defined
- ✅ hermes_audio_processor.py exists at /root/lyco-ai/hermes_audio/
- ❌ Container not started yet

### Audio-Inbox Status
- ✅ Local folder at ~/Projects/demestihas-ai/Audio-Inbox/
- ✅ Contains 3 MP3 files ready for processing
- ✅ OpenAI now installed on VPS (with --break-system-packages)
- ✅ Transcription working (just completed for one file)

### VPS Environment
- **Server**: 178.156.170.161
- **OS**: Ubuntu 24.04 (requires --break-system-packages for pip)
- **Docker**: Running but container IDs have changed
- **Python**: 3.12 with OpenAI library installed
- **API Keys**: In /root/lyco-ai/.env

---

## 📋 Implementation Tasks

### Task 1: Start Hermes Email Container (5 min)

```bash
# SSH to VPS
ssh root@178.156.170.161

# Navigate to project
cd /root/lyco-ai

# Check docker-compose has hermes_audio service
grep -A 10 "hermes_audio:" docker-compose.yml

# Build and start Hermes
docker-compose up -d --build hermes_audio

# Verify it's running
docker ps | grep hermes
docker logs hermes_audio --tail 50

# Test email connection
docker exec hermes_audio python -c "
import imaplib
import os
imap = imaplib.IMAP4_SSL('imap.gmail.com')
imap.login('hermesaudio444@gmail.com', 'ahd5egm2gvf!akr9UPY')
print('✅ Email connection working!')
"
```

**Success criteria**:
- Container status shows "Up" not "Restarting"
- Logs show "Connected to email server"
- Can connect to Gmail via IMAP

### Task 2: Create Audio Batch Processor (40 min)

Create script at `~/Projects/demestihas-ai/batch_process_audio.py`:

```python
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
```

**Also create quick launcher** `process_audio.sh`:

```bash
#!/bin/bash
cd ~/Projects/demestihas-ai
python3 batch_process_audio.py

# Show results
echo ""
echo "📊 Processing complete! Results:"
ls -la Audio-Inbox/processed/
```

---

## ✅ Success Criteria

1. **Hermes Container**
   - Running with status "Up"
   - Successfully connects to Gmail
   - Logs show monitoring for emails

2. **Batch Processor**
   - Processes all MP3 files in Audio-Inbox/
   - Creates transcript for each file
   - Extracts tasks (even if empty list)
   - Saves summaries to Audio-Inbox/processed/
   - Handles errors gracefully

---

## 🔧 Testing

### Test Hermes:
```bash
# Send test email to hermesaudio444@gmail.com with small audio
# Check logs: docker logs hermes_audio -f
# Verify processing starts
```

### Test Batch Processor:
```bash
cd ~/Projects/demestihas-ai
python3 batch_process_audio.py
# Should process all 3 MP3 files
# Check Audio-Inbox/ for transcripts
# Check Audio-Inbox/processed/ for summaries
```

---

## 🚨 Rollback Plan

If Hermes fails:
```bash
docker-compose stop hermes_audio
docker-compose rm hermes_audio
# Continue using batch processor
```

If batch processor fails:
```bash
# Use existing process_local_audio.py as fallback
python3 process_local_audio.py Audio-Inbox/[specific_file].mp3
```

---

## 📊 Reporting

Update `thread_log.md` with:
```markdown
## Thread #016 (Dev-Sonnet) - Hermes Email & Batch Processor
**Date**: [timestamp]
**Duration**: [actual time]
**Outcome**: [Success/Partial/Failed]
**Deliverables**:
- Hermes container: [status]
- Batch processor: [created/tested]
- Files processed: [X of Y]
**Issues**: [any problems]
**Next Thread**: Add task creation to Notion
```

---

## ⚡ Quick Tips

- Ubuntu 24.04 requires `--break-system-packages` for pip
- OpenAI already installed on VPS (verified working)
- Use existing VPS scripts when possible
- Keep processing simple - fancy features later
- Test with smallest audio file first

---

**Handoff to**: Claude Sonnet (use "Developer Mode" or standard Claude 3.5 Sonnet)
**Message**: "Please implement handoff #016 exactly as specified"
