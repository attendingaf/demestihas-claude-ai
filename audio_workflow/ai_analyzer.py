import logging
from typing import Dict, List
import json
from anthropic import Anthropic
import os

logger = logging.getLogger(__name__)

class MeetingAnalyzer:
    """Analyze meetings using the 5-question framework"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"  # Use Sonnet for deeper analysis
        
    async def get_meeting_context(self, script: str) -> str:
        """Get relevant context for meeting analysis - simplified for now"""
        
        try:
            # For now, return basic context - can be enhanced with Supabase later
            return "Historical meeting context: No previous meetings indexed yet."
            
        except Exception as e:
            logger.error(f"Error retrieving meeting context: {e}")
            return "Context retrieval failed."
    
    async def analyze_meeting(self, formatted_script: str, original_transcript: str) -> Dict:
        """Analyze meeting using 5-question framework"""
        
        # Get historical context
        historical_context = await self.get_meeting_context(formatted_script)
        
        prompt = f"""You are an expert meeting analyst with access to the user's historical context.

HISTORICAL CONTEXT:
{historical_context}

USER PROFILE:
- Name: Mene Demestihas
- Role: Physician executive, startup leader
- Focus: Emergency medicine, telehealth, AI-driven healthcare
- Family: Spouse (also ADHD), children (Stelios, Percy)
- Work style: ADHD-optimized, execution-focused

ANALYZE THIS MEETING using the following framework:

1. **What Happened** - Provide a clear, executive summary of the meeting's content and outcomes
2. **What Was Really Being Said** - Analyze subtext, unspoken concerns, political dynamics, and underlying messages
3. **What Surprises Occurred** - Identify unexpected revelations, sudden topic changes, or surprising reactions
4. **What Objectives Were Accomplished** - List completed objectives vs. unaccomplished ones, and any new objectives that emerged
5. **What Could Be Done Better Next Time** - Specific, actionable improvements for future meetings

FORMATTED SCRIPT:
{formatted_script}

PROVIDE YOUR ANALYSIS AS A JSON OBJECT with this structure:
{{
    "what_happened": "Executive summary here",
    "what_was_really_said": "Subtext and dynamics analysis",
    "surprises": ["surprise 1", "surprise 2"],
    "objectives_completed": ["objective 1", "objective 2"],
    "objectives_not_completed": ["objective 1", "objective 2"],
    "objectives_emerged": ["new objective 1"],
    "improvements": ["improvement 1", "improvement 2"],
    "action_items": [
        {{"task": "description", "owner": "name", "due": "date"}},
    ],
    "key_dates": [
        {{"date": "when", "event": "what"}},
    ],
    "participants": ["name1", "name2"],
    "sentiment": "overall positive/neutral/negative",
    "follow_up_required": true,
    "key_decisions": ["decision 1", "decision 2"]
}}

Ensure the JSON is valid and complete.
"""
        
        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            
            # Try to parse JSON (handle potential formatting issues)
            try:
                # Look for JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Fallback structure
                analysis = {
                    "what_happened": response_text[:500],
                    "error": "Failed to parse complete analysis",
                    "raw_response": response_text
                }
            
            # Store analysis for future reference (simplified for now)
            await self.store_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing meeting: {e}")
            return {
                "error": str(e),
                "what_happened": "Analysis failed - see error message"
            }
    
    async def store_analysis(self, analysis: Dict):
        """Store analysis for future reference - simplified for now"""
        try:
            logger.info("Analysis completed - storage to be implemented")
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
