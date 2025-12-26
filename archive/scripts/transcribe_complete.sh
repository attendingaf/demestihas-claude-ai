#!/bin/bash
# Complete solution to transcribe audio on VPS

echo "🔍 Checking VPS status and transcribing audio..."
echo "======================================================="

ssh root@178.156.170.161 << 'ENDSSH'
# First, show what containers are running
echo "📦 Current Docker containers:"
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"
echo ""

# Install OpenAI properly on the host
echo "🔧 Installing OpenAI on host system..."
# For Ubuntu 24.04, we need to use --break-system-packages
pip3 install openai --break-system-packages --quiet

# Check if installation worked
if python3 -c "import openai" 2>/dev/null; then
    echo "✅ OpenAI installed successfully"
else
    echo "Trying with apt..."
    apt install -y python3-openai 2>/dev/null || {
        echo "Using virtual environment approach..."
        apt install -y python3-venv
        python3 -m venv /tmp/transcribe_env
        /tmp/transcribe_env/bin/pip install openai
        alias python3='/tmp/transcribe_env/bin/python3'
    }
fi

# Load API key
cd /root/lyco-ai
if [ -f .env ]; then
    export $(grep OPENAI_API_KEY .env | xargs)
    echo "✅ API key loaded"
    # Show masked key for verification
    echo "API Key starts with: ${OPENAI_API_KEY:0:10}..."
fi

# Create standalone transcription script
echo ""
echo "📝 Creating transcription script..."
cat > /tmp/transcribe_standalone.py << 'SCRIPT'
#!/usr/bin/env python3
import os
import sys

# Install if needed
try:
    from openai import OpenAI
except ImportError:
    print("Installing OpenAI...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "--break-system-packages"])
    from openai import OpenAI

def transcribe():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key found. Checking .env file...")
        if os.path.exists("/root/lyco-ai/.env"):
            with open("/root/lyco-ai/.env") as f:
                for line in f:
                    if "OPENAI_API_KEY" in line:
                        api_key = line.split("=")[1].strip()
                        os.environ["OPENAI_API_KEY"] = api_key
                        break
    
    if not api_key:
        print("❌ No OPENAI_API_KEY found!")
        return False
    
    print(f"✅ API key loaded: {api_key[:10]}...")
    
    audio_path = "/tmp/Audio_08_22_2025_12_01_43.mp3"
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    file_size = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"📂 Found audio: {file_size:.1f} MB")
    
    try:
        client = OpenAI(api_key=api_key)
        print("📡 Calling Whisper API...")
        
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Save transcript
        output_path = "/tmp/transcript.txt"
        with open(output_path, "w") as f:
            f.write(response)
        
        print("\n✅ SUCCESS! Transcription complete")
        print(f"📄 Saved to: {output_path}")
        print(f"📊 Length: {len(response)} characters")
        print("\n--- PREVIEW (first 1000 chars) ---")
        print(response[:1000])
        if len(response) > 1000:
            print("\n... [continues] ...")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    transcribe()
SCRIPT

# Run the transcription
echo ""
echo "🎤 Running transcription..."
echo "======================================="
python3 /tmp/transcribe_standalone.py

# Check if transcript was created
if [ -f /tmp/transcript.txt ]; then
    echo ""
    echo "✅ Transcript file created!"
    echo "File size: $(wc -c < /tmp/transcript.txt) bytes"
    echo "Word count: $(wc -w < /tmp/transcript.txt) words"
    echo "Line count: $(wc -l < /tmp/transcript.txt) lines"
    
    # Copy to multiple locations for easy access
    cp /tmp/transcript.txt /tmp/Audio_08_22_2025_12_01_43_transcript.txt
    cp /tmp/transcript.txt /root/transcript_latest.txt
    
    echo ""
    echo "📍 Transcript available at:"
    echo "  - /tmp/transcript.txt"
    echo "  - /tmp/Audio_08_22_2025_12_01_43_transcript.txt"
    echo "  - /root/transcript_latest.txt"
else
    echo "❌ Transcript not created. Check errors above."
fi

ENDSSH

echo ""
echo "======================================================="
echo "📥 Downloading transcript to your local machine..."
echo "======================================================="

# Try multiple download paths
for remote_path in "/tmp/transcript.txt" "/tmp/Audio_08_22_2025_12_01_43_transcript.txt" "/root/transcript_latest.txt"; do
    scp root@178.156.170.161:$remote_path ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Downloaded from $remote_path"
        break
    fi
done

if [ -f "./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt" ]; then
    echo ""
    echo "🎉 SUCCESS! Transcript saved locally!"
    echo "📍 Location: Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
    echo ""
    echo "📄 First 40 lines of your transcript:"
    echo "======================================="
    head -40 ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt
    echo "======================================="
    echo ""
    echo "📊 Stats:"
    echo "  Words: $(wc -w < ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt)"
    echo "  Lines: $(wc -l < ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt)"
    echo ""
    echo "View full transcript:"
    echo "cat Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
else
    echo ""
    echo "⚠️ Could not download automatically. Manual download:"
    echo "scp root@178.156.170.161:/tmp/transcript.txt ./Audio-Inbox/"
fi
