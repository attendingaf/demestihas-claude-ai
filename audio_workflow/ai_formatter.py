import logging
from typing import Dict, Optional
import json
from anthropic import Anthropic
import os

logger = logging.getLogger(__name__)

class AIScriptFormatter:
    """Format raw transcripts into narrative/script format using AI with context"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-haiku-20240307"  # Use Haiku for cost efficiency
        
    async def get_relevant_context(self, transcript: str, limit: int = 5) -> str:
        """Retrieve relevant context - simplified for now"""
        
        try:
            # Extract key terms for context search
            key_terms = self.extract_key_terms(transcript[:1000])  # First 1000 chars
            
            # For now, return basic context - can be enhanced with Supabase later
            context = f"Key terms identified: {key_terms}"
            
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return "Context retrieval failed."
    
    def extract_key_terms(self, text: str) -> str:
        """Extract key terms from text for context search"""
        # Simple extraction - can be enhanced with NLP
        import re
        
        # Find capitalized words (likely names, places)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        # Common meeting-related terms
        meeting_terms = re.findall(r'\b(project|deadline|budget|meeting|decision|action)\b', text, re.I)
        
        return " ".join(set(proper_nouns[:10] + meeting_terms[:5]))
    
    async def format_transcript(self, transcript: str, context: Dict) -> str:
        """Format transcript into narrative/script format"""
        
        # Get relevant context
        memory_context = await self.get_relevant_context(transcript)
        
        prompt = f"""You are a professional meeting transcript formatter with access to the user's context.

USER CONTEXT:
{memory_context}

METADATA:
- File: {context.get('file_name', 'Unknown')}
- Date: {context.get('date', 'Unknown')}
- Session: {context.get('session_id', 'Unknown')}

YOUR TASK:
Transform the raw transcript below into a well-formatted narrative/script format.

FORMATTING REQUIREMENTS:
1. Identify and label speakers consistently (use context to identify people when possible)
2. Add proper paragraph breaks and formatting
3. Clean up filler words and false starts while preserving meaning
4. Add scene/context markers where appropriate [e.g., [Phone rings], [Pause], [Laughter]]
5. Preserve the authentic voice and tone of speakers
6. Format as a readable script/narrative with clear speaker labels

OUTPUT FORMAT:
**Speaker Name:** Their dialogue here.

[Context or action markers in brackets]

**Next Speaker:** Their response.

---

RAW TRANSCRIPT:
{transcript}

---

FORMATTED SCRIPT:
"""
        
        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.3,  # Lower temperature for consistency
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            formatted_script = response.content[0].text
            
            # Add metadata header
            header = f"""# Meeting Transcript
**File:** {context.get('file_name', 'Unknown')}  
**Date:** {context.get('date', 'Unknown')}  
**Session ID:** {context.get('session_id', 'Unknown')}

---

"""
            
            return header + formatted_script
            
        except Exception as e:
            logger.error(f"Error formatting transcript: {e}")
            return f"# Formatting Error\n\nOriginal transcript preserved:\n\n{transcript}"
