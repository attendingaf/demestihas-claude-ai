"""
Meeting processing module for Pluma agent
Integrates with Hermes audio processing and generates meeting summaries
"""

import os
import json
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)

@dataclass
class MeetingNotes:
    """Structured meeting notes with metadata"""
    id: str
    title: str
    date: datetime
    duration_minutes: Optional[int]
    participants: List[str]
    transcript: str
    summary: str
    key_decisions: List[str]
    action_items: List[Dict[str, str]]  # [{"task": "", "owner": "", "due": ""}]
    follow_ups: List[str]
    audio_url: Optional[str] = None
    confidence_score: float = 0.0

class MeetingProcessor:
    """Process meetings through Hermes audio and generate intelligent summaries"""
    
    def __init__(self, anthropic_client: anthropic.Client):
        self.claude = anthropic_client
        self.hermes_url = self._get_hermes_url()
    
    def _get_hermes_url(self) -> str:
        """Get Hermes audio service URL"""
        # In container environment, use service name
        hermes_host = os.getenv('HERMES_HOST', 'hermes_audio')
        hermes_port = os.getenv('HERMES_PORT', '8000')
        return f"http://{hermes_host}:{hermes_port}"
    
    async def process_meeting_audio(self, audio_url: str, meeting_title: str = "") -> MeetingNotes:
        """
        Process meeting audio through full pipeline:
        1. Send to Hermes for transcription
        2. Use Claude for intelligent summary
        3. Extract action items and decisions
        4. Generate follow-up recommendations
        """
        try:
            logger.info(f"🎵 Processing meeting audio: {audio_url}")
            
            # Step 1: Get transcription from Hermes
            transcript = await self._get_transcript_from_hermes(audio_url)
            
            if not transcript or len(transcript.strip()) < 50:
                logger.warning("Transcript too short or empty, creating placeholder")
                return self._create_placeholder_notes(audio_url, meeting_title)
            
            # Step 2: Generate comprehensive summary with Claude
            analysis = await self._analyze_meeting_content(transcript)
            
            # Step 3: Create structured notes
            notes = MeetingNotes(
                id=self._generate_meeting_id(),
                title=meeting_title or analysis.get('suggested_title', 'Meeting Notes'),
                date=datetime.now(),
                duration_minutes=analysis.get('duration_estimate'),
                participants=analysis.get('participants', []),
                transcript=transcript,
                summary=analysis.get('summary', ''),
                key_decisions=analysis.get('key_decisions', []),
                action_items=analysis.get('action_items', []),
                follow_ups=analysis.get('follow_ups', []),
                audio_url=audio_url,
                confidence_score=analysis.get('confidence_score', 0.8)
            )
            
            logger.info(f"✅ Meeting processing complete: {notes.id}")
            return notes
            
        except Exception as e:
            logger.error(f"❌ Meeting processing failed: {e}")
            return self._create_error_notes(audio_url, meeting_title, str(e))
    
    async def _get_transcript_from_hermes(self, audio_url: str) -> str:
        """Send audio to Hermes for transcription"""
        try:
            async with aiohttp.ClientSession() as session:
                # Hermes API call for transcription
                payload = {
                    'audio_url': audio_url,
                    'language': 'en',  # Default to English, could be parameterized
                    'format': 'text'
                }
                
                async with session.post(
                    f"{self.hermes_url}/transcribe",
                    json=payload,
                    timeout=300  # 5 minute timeout for audio processing
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        transcript = result.get('transcript', '')
                        
                        if transcript:
                            logger.info(f"✅ Hermes transcription complete: {len(transcript)} chars")
                            return transcript
                        else:
                            logger.warning("Hermes returned empty transcript")
                            return ""
                    else:
                        logger.error(f"Hermes API error: {response.status}")
                        return ""
                        
        except aiohttp.ClientTimeout:
            logger.error("Hermes transcription timeout (>5 minutes)")
            return ""
        except Exception as e:
            logger.error(f"Hermes integration failed: {e}")
            return ""
    
    async def _analyze_meeting_content(self, transcript: str) -> Dict:
        """Use Claude to analyze meeting transcript comprehensively"""
        
        analysis_prompt = f"""Analyze this meeting transcript and provide a comprehensive structured summary.

TRANSCRIPT:
{transcript}

Please provide a JSON response with the following structure:
{{
    "suggested_title": "Brief meeting title based on content",
    "summary": "2-3 sentence executive summary of the meeting",
    "key_decisions": ["List of concrete decisions made during the meeting"],
    "action_items": [
        {{
            "task": "Specific action item description",
            "owner": "Person responsible (if mentioned)",
            "due": "Due date or timeframe (if mentioned)",
            "priority": "high|medium|low"
        }}
    ],
    "follow_ups": ["Items requiring future attention or follow-up meetings"],
    "participants": ["Names of people who spoke or were mentioned"],
    "topics_discussed": ["Main topics or agenda items covered"],
    "duration_estimate": "Estimated meeting length in minutes (integer)",
    "meeting_type": "standup|planning|review|decision|brainstorm|other",
    "confidence_score": "0.0-1.0 confidence in analysis quality",
    "next_steps": ["Immediate actions needed post-meeting"],
    "key_quotes": ["Important quotes or statements (max 3)"],
    "concerns_raised": ["Issues or concerns mentioned"],
    "outcomes": ["Concrete outcomes or results achieved"]
}}

Guidelines:
- Extract specific, actionable items rather than vague statements
- Identify owners only if clearly stated in transcript
- Include due dates only if explicitly mentioned
- Focus on business-relevant content
- Be concise but comprehensive
- If transcript quality is poor, lower the confidence_score"""

        try:
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=3000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            analysis = json.loads(response.content[0].text)
            logger.info(f"✅ Meeting analysis complete with confidence: {analysis.get('confidence_score', 0)}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude analysis JSON: {e}")
            return self._fallback_analysis(transcript)
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return self._fallback_analysis(transcript)
    
    def _fallback_analysis(self, transcript: str) -> Dict:
        """Fallback analysis when Claude fails"""
        return {
            "suggested_title": "Meeting Notes",
            "summary": f"Meeting transcript available ({len(transcript)} characters). Automated analysis failed.",
            "key_decisions": [],
            "action_items": [],
            "follow_ups": ["Review transcript manually for action items"],
            "participants": [],
            "topics_discussed": [],
            "duration_estimate": max(5, len(transcript) // 100),  # Rough estimate
            "meeting_type": "other",
            "confidence_score": 0.2,
            "next_steps": ["Manual review required"],
            "key_quotes": [],
            "concerns_raised": [],
            "outcomes": []
        }
    
    async def generate_follow_up_emails(self, notes: MeetingNotes) -> List[Dict[str, str]]:
        """Generate follow-up email drafts based on meeting notes"""
        if not notes.action_items and not notes.follow_ups:
            return []
        
        try:
            email_prompt = f"""Based on these meeting notes, generate follow-up email drafts for key stakeholders.

MEETING: {notes.title}
DATE: {notes.date.strftime('%Y-%m-%d')}
PARTICIPANTS: {', '.join(notes.participants)}

SUMMARY: {notes.summary}

ACTION ITEMS:
{chr(10).join([f"- {item['task']} ({item.get('owner', 'TBD')})" for item in notes.action_items])}

FOLLOW-UPS:
{chr(10).join([f"- {item}" for item in notes.follow_ups])}

Generate 1-3 follow-up email drafts as JSON:
[
    {{
        "recipient_type": "all_participants|action_owners|specific_stakeholder",
        "subject": "Email subject line",
        "body": "Complete email body with appropriate tone",
        "priority": "high|medium|low",
        "send_timing": "immediate|next_day|before_due_date"
    }}
]

Make emails:
- Professional but concise
- Include specific action items for recipients
- Reference key decisions from the meeting
- Include relevant deadlines
- Use a helpful, collaborative tone"""

            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": email_prompt}]
            )
            
            email_drafts = json.loads(response.content[0].text)
            logger.info(f"✅ Generated {len(email_drafts)} follow-up email drafts")
            return email_drafts
            
        except Exception as e:
            logger.error(f"Follow-up email generation failed: {e}")
            return []
    
    async def create_summary_document(self, notes: MeetingNotes, format: str = "markdown") -> str:
        """Generate formatted summary document"""
        if format == "markdown":
            return self._create_markdown_summary(notes)
        elif format == "html":
            return self._create_html_summary(notes)
        else:
            return self._create_text_summary(notes)
    
    def _create_markdown_summary(self, notes: MeetingNotes) -> str:
        """Create markdown-formatted meeting summary"""
        md = f"""# {notes.title}

**Date:** {notes.date.strftime('%B %d, %Y at %I:%M %p')}
**Duration:** {notes.duration_minutes or 'Unknown'} minutes
**Participants:** {', '.join(notes.participants) if notes.participants else 'Not specified'}

## Executive Summary
{notes.summary}

## Key Decisions
"""
        
        if notes.key_decisions:
            for decision in notes.key_decisions:
                md += f"- {decision}\n"
        else:
            md += "- None recorded\n"
        
        md += "\n## Action Items\n"
        if notes.action_items:
            for item in notes.action_items:
                owner = item.get('owner', 'TBD')
                due = item.get('due', 'No deadline')
                priority = item.get('priority', 'medium')
                md += f"- **{item['task']}** (Owner: {owner}, Due: {due}, Priority: {priority})\n"
        else:
            md += "- None assigned\n"
        
        md += "\n## Follow-up Items\n"
        if notes.follow_ups:
            for follow_up in notes.follow_ups:
                md += f"- {follow_up}\n"
        else:
            md += "- None identified\n"
        
        if notes.transcript:
            md += f"\n## Full Transcript\n```\n{notes.transcript[:2000]}{'...' if len(notes.transcript) > 2000 else ''}\n```\n"
        
        md += f"\n---\n*Generated by Pluma Agent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Confidence: {notes.confidence_score:.1%})*\n"
        
        return md
    
    def _create_text_summary(self, notes: MeetingNotes) -> str:
        """Create plain text summary"""
        return f"""MEETING SUMMARY: {notes.title}
Date: {notes.date.strftime('%Y-%m-%d %H:%M')}
Participants: {', '.join(notes.participants)}

SUMMARY:
{notes.summary}

KEY DECISIONS:
{chr(10).join([f"- {d}" for d in notes.key_decisions]) if notes.key_decisions else "- None"}

ACTION ITEMS:
{chr(10).join([f"- {item['task']} ({item.get('owner', 'TBD')})" for item in notes.action_items]) if notes.action_items else "- None"}

FOLLOW-UPS:
{chr(10).join([f"- {f}" for f in notes.follow_ups]) if notes.follow_ups else "- None"}
"""
    
    def _create_html_summary(self, notes: MeetingNotes) -> str:
        """Create HTML-formatted summary"""
        # Basic HTML template for meeting notes
        return f"""
        <html>
        <head><title>{notes.title}</title></head>
        <body>
            <h1>{notes.title}</h1>
            <p><strong>Date:</strong> {notes.date.strftime('%B %d, %Y')}</p>
            <p><strong>Participants:</strong> {', '.join(notes.participants)}</p>
            
            <h2>Summary</h2>
            <p>{notes.summary}</p>
            
            <h2>Key Decisions</h2>
            <ul>
            {''.join([f'<li>{d}</li>' for d in notes.key_decisions]) if notes.key_decisions else '<li>None</li>'}
            </ul>
            
            <h2>Action Items</h2>
            <ul>
            {''.join([f'<li><strong>{item["task"]}</strong> - {item.get("owner", "TBD")}</li>' for item in notes.action_items]) if notes.action_items else '<li>None</li>'}
            </ul>
        </body>
        </html>
        """
    
    def _generate_meeting_id(self) -> str:
        """Generate unique meeting ID"""
        return f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _create_placeholder_notes(self, audio_url: str, title: str) -> MeetingNotes:
        """Create placeholder notes when transcription fails"""
        return MeetingNotes(
            id=self._generate_meeting_id(),
            title=title or "Meeting Notes (Transcription Failed)",
            date=datetime.now(),
            duration_minutes=None,
            participants=[],
            transcript="Transcription not available",
            summary="Meeting audio could not be processed. Manual review required.",
            key_decisions=[],
            action_items=[],
            follow_ups=["Manually review audio recording", "Contact participants for notes"],
            audio_url=audio_url,
            confidence_score=0.0
        )
    
    def _create_error_notes(self, audio_url: str, title: str, error: str) -> MeetingNotes:
        """Create error notes when processing completely fails"""
        return MeetingNotes(
            id=self._generate_meeting_id(),
            title=title or "Meeting Notes (Processing Error)",
            date=datetime.now(),
            duration_minutes=None,
            participants=[],
            transcript=f"Processing error: {error}",
            summary="Meeting processing failed due to technical error.",
            key_decisions=[],
            action_items=[{"task": "Retry meeting processing", "owner": "Admin", "due": "ASAP", "priority": "high"}],
            follow_ups=["Check Hermes audio service", "Verify audio file format"],
            audio_url=audio_url,
            confidence_score=0.0
        )

# Utility functions for meeting management

def estimate_reading_time(text: str) -> int:
    """Estimate reading time for transcript in minutes"""
    words = len(text.split())
    reading_speed = 200  # words per minute average
    return max(1, words // reading_speed)

def extract_time_mentions(text: str) -> List[str]:
    """Extract time/date mentions from transcript"""
    import re
    time_patterns = [
        r'\b\d{1,2}:\d{2}\b',  # 2:30, 14:30
        r'\b\d{1,2}/\d{1,2}\b',  # 3/15
        r'\bnext\s+week\b',
        r'\btomorrow\b',
        r'\bMonday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday\b'
    ]
    
    matches = []
    for pattern in time_patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    
    return list(set(matches))  # Remove duplicates

def calculate_talk_time_distribution(transcript: str, participants: List[str]) -> Dict[str, float]:
    """Estimate how much each participant spoke"""
    if not participants:
        return {}
    
    # Simple heuristic: count lines that start with participant names
    lines = transcript.split('\n')
    speaker_counts = {p: 0 for p in participants}
    
    for line in lines:
        for participant in participants:
            if line.strip().lower().startswith(participant.lower() + ':'):
                speaker_counts[participant] += len(line)
                break
    
    total_chars = sum(speaker_counts.values())
    if total_chars == 0:
        return {p: 1.0/len(participants) for p in participants}
    
    return {p: count/total_chars for p, count in speaker_counts.items()}
