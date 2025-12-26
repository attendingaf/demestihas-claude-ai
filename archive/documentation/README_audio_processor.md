# Google Drive Audio Processor

Automated audio transcription pipeline with Google Drive integration, automatic compression, and intelligent chunking.

## Features

- **Google Drive Integration**: Automatically processes files from `MyDrive/Audio_Inbox/`
- **Smart Compression**: Automatically compresses files >25MB using ffmpeg
- **Intelligent Chunking**: Splits large files that remain >25MB after compression
- **Whisper Transcription**: Uses OpenAI's Whisper API for accurate transcription
- **Formatted Output**: Creates markdown transcripts with metadata and analysis templates
- **Automatic Archiving**: Moves processed files to `MyDrive/Audio_Inbox/archived/`
- **Watch Mode**: Continuously monitors for new files

## Prerequisites

1. **Python 3.7+**
2. **ffmpeg** - Required for audio compression and chunking
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

3. **Google Drive API Credentials**
   - Place your credentials at `~/.credentials/drive_credentials.json`
   - Token will be saved to `~/.credentials/token.json`

4. **OpenAI API Key**
   - Save to `~/.openai_key` file, or
   - Set `OPENAI_API_KEY` environment variable

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make the script executable:
   ```bash
   chmod +x google_drive_audio_processor.py
   ```

## Google Drive Setup

The script expects the following folder structure in your Google Drive:
```
MyDrive/
├── Audio_Inbox/           # Place audio files here
│   └── archived/          # Processed files moved here
└── Audio_Transcripts/     # Transcripts saved here
```

Folders will be created automatically if they don't exist.

## Usage

### Basic Usage
Process all audio files in the inbox once:
```bash
python google_drive_audio_processor.py
```

### Watch Mode
Continuously monitor for new files (checks every 60 seconds):
```bash
python google_drive_audio_processor.py --watch
```

### Verbose Logging
Enable detailed debug output:
```bash
python google_drive_audio_processor.py --verbose
```

## How It Works

1. **Discovery**: Scans `Audio_Inbox/` for audio files (mp3, wav, m4a, etc.)
2. **Download**: Downloads each file to a temporary directory
3. **Compression** (if needed):
   - Files >25MB are compressed using ffmpeg
   - Target: mono, 16kHz sample rate, optimized bitrate
   - Maintains speech quality while reducing size
4. **Chunking** (if still >25MB):
   - Splits into ~20MB segments
   - Maintains chronological order
5. **Transcription**:
   - Each chunk sent to Whisper API
   - Results combined in order
6. **Output Generation**:
   - Creates markdown with full transcript
   - Includes metadata (sizes, compression ratio, chunks)
   - Adds analysis template for notes
7. **Upload & Archive**:
   - Transcript saved to `Audio_Transcripts/`
   - Original moved to `Audio_Inbox/archived/`
8. **Cleanup**: Removes all temporary files

## Output Format

Transcripts are saved as markdown with:
- Original filename and processing date
- File metadata (sizes, compression ratio, chunks)
- Full transcript (with part markers if chunked)
- Analysis template with sections for:
  - Speaker identification
  - Action items
  - Key decisions
  - Follow-ups required
  - Notes

## Logging

All operations are logged to `audio_processor.log` with:
- Processing progress
- Compression statistics
- Error details
- Summary statistics

## Error Handling

- **Missing ffmpeg**: Provides installation instructions
- **Failed compression**: Falls back to original file
- **Failed chunks**: Continues with successful chunks
- **API errors**: Logs and continues with next file
- **Network issues**: Retries with timeout

## Performance Notes

- Compression typically achieves 60-80% size reduction for speech
- Chunking maintains ~20MB segments for reliable API uploads
- Processing time depends on file size and API response
- Watch mode checks every 60 seconds to minimize API calls

## Troubleshooting

1. **Authentication Issues**:
   - Delete `~/.credentials/token.json` and re-authenticate
   - Verify `drive_credentials.json` has correct permissions

2. **Transcription Failures**:
   - Check OpenAI API key and credits
   - Verify file format is supported

3. **Compression Issues**:
   - Ensure ffmpeg is installed: `ffmpeg -version`
   - Check available disk space in temp directory

4. **Large Files Still Failing**:
   - Script automatically chunks files that remain >25MB
   - Check logs for specific error messages

## Statistics

The script tracks and reports:
- Files processed successfully
- Files failed
- Total original size
- Total compressed size
- Overall compression ratio

## Example Output

```
2024-01-15 10:30:45 - INFO - Processing: meeting_recording.mp3
2024-01-15 10:30:46 - INFO - Original size: 87.34 MB
2024-01-15 10:30:48 - INFO - Compression successful: 87.34MB → 19.85MB (77.3% reduction)
2024-01-15 10:30:49 - INFO - Transcribing: compressed_meeting_recording.mp3
2024-01-15 10:31:15 - INFO - Transcript saved: meeting_recording_transcript.md
2024-01-15 10:31:16 - INFO - Archived original file
2024-01-15 10:31:16 - INFO - ✓ Successfully processed: meeting_recording.mp3

============================================================
PROCESSING SUMMARY
============================================================
Files processed: 3
Files failed: 0
Total original size: 245.67 MB
Total compressed size: 58.34 MB
Overall compression: 76.3%
============================================================
```