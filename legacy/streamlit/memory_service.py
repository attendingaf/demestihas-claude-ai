"""
Demestihas AI Memory Service
Persistent memory integration for DemestiChat Streamlit agent
Version: 1.0 Production
"""
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryService:
    """Memory service client for DemestiChat Streamlit integration."""
    
    def __init__(
        self, 
        api_url: str = "http://agent:8000",  # Internal Docker network
        user_id: str = "mene"
    ):
        self.api_url = api_url.rstrip('/')
        self.user_id = user_id
        self.token = None
        self.token_expiry = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Get JWT token for authentication"""
        try:
            response = requests.post(
                f"{self.api_url}/auth/token",
                params={"user_id": self.user_id},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            self.token = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logger.info(f"✅ Memory service authenticated as {self.user_id}")
        except Exception as e:
            logger.error(f"❌ Memory authentication failed: {e}")
            raise
    
    def _check_token(self) -> None:
        """Check if token needs refresh"""
        if self.token_expiry and datetime.now() >= self.token_expiry - timedelta(minutes=5):
            logger.info("🔄 Refreshing token")
            self._authenticate()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        self._check_token()
        return {"Authorization": f"Bearer {self.token}"}
    
    def _detect_contexts(self, content: str) -> List[str]:
        """Auto-detect contexts from content"""
        contexts = []
        lower = content.lower()
        
        keywords = {
            'medical': ['doctor', 'medication', 'health', 'patient', 'diagnosis', 'blood pressure'],
            'family': ['family', 'cindy', 'child', 'kids', 'persephone', 'stylianos', 'francisca'],
            'project': ['project', 'code', 'development', 'deadline', 'deliverable'],
            'schedule': ['meeting', 'appointment', 'calendar', 'tomorrow', 'next week'],
            'preference': ['prefer', 'like', 'favorite', 'always', 'never'],
            'adhd-optimization': ['energy', 'morning', 'focus', 'adhd', '15 minute']
        }
        
        for context, words in keywords.items():
            if any(word in lower for word in words):
                contexts.append(context)
        
        return contexts or ['general']
    
    def _detect_importance(self, content: str) -> int:
        """Auto-detect importance (1-10)"""
        score = 5
        lower = content.lower()
        
        if any(w in lower for w in ['urgent', 'critical', 'important', 'emergency']):
            score += 3
        if any(w in lower for w in ['medical', 'doctor', 'medication']):
            score += 2
        if any(w in lower for w in ['password', 'credential', 'token']):
            return 10
        if any(w in lower for w in ['maybe', 'perhaps', 'possibly']):
            score -= 2
        
        return max(1, min(10, score))
    
    def save_memory(
        self,
        content: str,
        memory_type: str = "auto",
        importance: Optional[int] = None,
        contexts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Save memory with auto-detection"""
        try:
            contexts = contexts or self._detect_contexts(content)
            importance = importance or self._detect_importance(content)
            
            if memory_type == "auto":
                memory_type = "system" if "family" in contexts else "private"
            
            enriched = {
                "content": content,
                "metadata": {
                    "contexts": contexts,
                    "importance": importance,
                    "tags": contexts,
                    "created_at": datetime.utcnow().isoformat(),
                    "source": "demestichat"
                }
            }
            
            response = requests.post(
                f"{self.api_url}/memory/store",
                params={
                    "content": json.dumps(enriched),
                    "memory_type": memory_type
                },
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Memory stored (importance: {importance})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            raise
    
    def search_memories(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search memories with relevance scoring"""
        try:
            response = requests.get(
                f"{self.api_url}/memory/list",
                params={"memory_type": "all", "limit": 100},
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            
            memories = response.json().get("memories", [])
            query_terms = query.lower().split()
            scored = []
            
            for mem in memories:
                try:
                    if mem["content"].startswith("{"):
                        parsed = json.loads(mem["content"])
                        content = parsed.get("content", "")
                        metadata = parsed.get("metadata", {})
                    else:
                        content = mem["content"]
                        metadata = {}
                    
                    content_lower = content.lower()
                    score = sum(1 for term in query_terms if term in content_lower)
                    
                    if query.lower() in content_lower:
                        score += 5
                    
                    importance = metadata.get("importance", 5)
                    if importance >= 8:
                        score += 2
                    
                    if score > 0:
                        scored.append({
                            "content": content,
                            "score": score,
                            "metadata": metadata,
                            "memory_id": mem.get("id"),
                            "created_at": mem.get("created_at")
                        })
                except:
                    continue
            
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit]
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent memories"""
        try:
            response = requests.get(
                f"{self.api_url}/memory/list",
                params={"memory_type": "all", "limit": limit},
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            
            memories = response.json().get("memories", [])
            recent = []
            
            for mem in memories[:limit]:
                try:
                    if mem["content"].startswith("{"):
                        parsed = json.loads(mem["content"])
                        content = parsed.get("content", "")
                        metadata = parsed.get("metadata", {})
                    else:
                        content = mem["content"]
                        metadata = {}
                    
                    recent.append({
                        "content": content,
                        "metadata": metadata,
                        "memory_id": mem.get("id"),
                        "created_at": mem.get("created_at")
                    })
                except:
                    continue
            
            return recent
            
        except Exception as e:
            logger.error(f"❌ Get recent failed: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        try:
            response = requests.get(
                f"{self.api_url}/memory/stats",
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Stats failed: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check if memory API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def format_context_for_llm(self, memories: List[Dict], max_memories: int = 5) -> str:
        """Format memories for LLM context"""
        if not memories:
            return ""
        
        lines = ["Relevant context from memory:"]
        
        for mem in memories[:max_memories]:
            content = mem.get("content", "")
            importance = mem.get("metadata", {}).get("importance", 5)
            contexts = mem.get("metadata", {}).get("contexts", [])
            
            indicator = "🔴" if importance >= 8 else "🟡" if importance >= 5 else "⚪"
            context_tags = f"[{', '.join(contexts)}]" if contexts else ""
            
            lines.append(f"{indicator} {content} {context_tags}")
        
        return "\n".join(lines)


# Singleton for Streamlit caching
_memory_instance = None

def get_memory_service() -> MemoryService:
    """Get or create singleton memory service (use with st.cache_resource)"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryService()
    return _memory_instance
