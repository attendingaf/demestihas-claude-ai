#!/bin/bash
cd ~/Projects/demestihas-ai
python3 batch_process_audio.py

# Show results
echo ""
echo "📊 Processing complete! Results:"
ls -la Audio-Inbox/processed/
