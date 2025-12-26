import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict
import math

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handle audio compression and chunking"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # Assumes ffmpeg is in PATH
    
    async def compress_audio(self, input_path: Path, output_dir: Path) -> Path:
        """Compress audio to mono 16kHz MP3"""
        
        output_path = output_dir / f"compressed_{input_path.name}"
        
        # Change extension to .mp3 if different
        if output_path.suffix != '.mp3':
            output_path = output_path.with_suffix('.mp3')
        
        cmd = [
            self.ffmpeg_path,
            '-i', str(input_path),
            '-ac', '1',           # Mono
            '-ar', '16000',       # 16kHz sample rate
            '-b:a', '32k',        # Lower bitrate for speech
            '-y',                 # Overwrite output
            str(output_path)
        ]
        
        logger.info(f"Compressing: {input_path.name}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg compression failed: {result.stderr}")
        
        # Log size reduction
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        compressed_size = os.path.getsize(output_path) / (1024 * 1024)
        reduction = (1 - compressed_size/original_size) * 100
        
        logger.info(f"Compressed {original_size:.1f}MB → {compressed_size:.1f}MB ({reduction:.1f}% reduction)")
        
        return output_path
    
    async def chunk_audio(
        self, 
        input_path: Path, 
        max_size_mb: int = 20,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """Split audio into chunks smaller than max_size_mb"""
        
        if output_dir is None:
            output_dir = input_path.parent / "chunks"
        output_dir.mkdir(exist_ok=True)
        
        # Get duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(input_path)
        ]
        
        result = subprocess.run(duration_cmd, capture_output=True, text=True)
        total_duration = float(result.stdout.strip())
        
        # Calculate chunk duration based on file size
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        num_chunks = math.ceil(file_size_mb / max_size_mb)
        chunk_duration = total_duration / num_chunks
        
        logger.info(f"Splitting into {num_chunks} chunks of ~{chunk_duration:.1f} seconds")
        
        chunks = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            output_path = output_dir / f"{input_path.stem}_chunk_{i:03d}.mp3"
            
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-c', 'copy',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to create chunk {i}: {result.stderr}")
                continue
            
            chunks.append(output_path)
            logger.info(f"Created chunk {i+1}/{num_chunks}: {output_path.name}")
        
        return chunks
    
    async def get_audio_info(self, file_path: Path) -> Dict:
        """Get audio file information"""
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            return {}
