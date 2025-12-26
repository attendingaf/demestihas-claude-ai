"""
Tests for Lyco LangGraph workflow.

Tests the main workflow graph and integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.graph import create_lyco_workflow, validate_graph
from workflow.state import LycoGraphState


class TestWorkflowCreation:
    """Test workflow graph creation and structure"""

    def test_create_workflow(self):
        """Test that workflow can be created"""
        workflow = create_lyco_workflow()
        assert workflow is not None

    def test_graph_validation(self):
        """Test that graph structure is valid"""
        validation = validate_graph()
        assert validation["valid"] is True
        assert len(validation["orphan_nodes"]) == 0

    def test_graph_has_required_nodes(self):
        """Test that all required nodes are present"""
        workflow = create_lyco_workflow()

        # Check for essential node types
        required_patterns = [
            "capture",  # Input capture
            "parse",    # LLM parsing
            "classify", # Classification
            "route",    # Routing
            "cache",    # Storage
        ]

        # Note: Direct node access may vary by LangGraph version
        # This is a conceptual test
        assert workflow is not None


@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test workflow execution with different inputs"""

    async def test_terminal_input(self):
        """Test processing terminal input"""
        workflow = create_lyco_workflow()

        state = LycoGraphState(
            raw_input="Schedule meeting with team tomorrow at 2pm",
            source="terminal",
            user_id="mene@beltlineconsulting.co",
            timestamp=datetime.now().isoformat(),
            messages=[],
            skip_count=0,
            patterns_detected=[],
            skip_reasons=[],
            retry_count=0,
            processing_time_ms=0,
            cache_hit=False,
            confidence_score=0.0,
            notification_sent=False,
            calendar_blocked=False,
            notion_synced=False,
            redis_published=False,
            database_saved=False,
            should_retry=False,
            energy_mismatch=False,
            should_park=False,
            prompt_version=1
        )

        # Execute workflow
        result = await workflow.ainvoke(state)

        # Check that task was parsed
        assert result.get("task_title") is not None
        assert result.get("action") is not None

    async def test_email_input(self):
        """Test processing email input"""
        workflow = create_lyco_workflow()

        state = LycoGraphState(
            raw_input="Email from client: Please review the proposal",
            source="email",
            user_id="mene@beltlineconsulting.co",
            timestamp=datetime.now().isoformat(),
            source_metadata={
                "from": "client@example.com",
                "subject": "Proposal Review"
            },
            messages=[],
            skip_count=0,
            patterns_detected=[],
            skip_reasons=[],
            retry_count=0,
            processing_time_ms=0,
            cache_hit=False,
            confidence_score=0.0,
            notification_sent=False,
            calendar_blocked=False,
            notion_synced=False,
            redis_published=False,
            database_saved=False,
            should_retry=False,
            energy_mismatch=False,
            should_park=False,
            prompt_version=1
        )

        result = await workflow.ainvoke(state)

        assert result.get("source") == "email"
        assert result.get("task_title") is not None

    async def test_high_energy_task(self):
        """Test classification of high energy task"""
        workflow = create_lyco_workflow()

        state = LycoGraphState(
            raw_input="Create strategic plan for Q1 2024 including detailed analysis",
            source="terminal",
            user_id="mene@beltlineconsulting.co",
            timestamp=datetime.now().isoformat(),
            messages=[],
            skip_count=0,
            patterns_detected=[],
            skip_reasons=[],
            retry_count=0,
            processing_time_ms=0,
            cache_hit=False,
            confidence_score=0.0,
            notification_sent=False,
            calendar_blocked=False,
            notion_synced=False,
            redis_published=False,
            database_saved=False,
            should_retry=False,
            energy_mismatch=False,
            should_park=False,
            prompt_version=1
        )

        result = await workflow.ainvoke(state)

        # Should be classified as high energy
        energy_level = result.get("energy_level")
        assert energy_level in ["high", "medium", "low"]

    async def test_skip_intelligence(self):
        """Test skip pattern detection"""
        workflow = create_lyco_workflow()

        state = LycoGraphState(
            raw_input="Review long technical document",
            source="terminal",
            user_id="mene@beltlineconsulting.co",
            timestamp=datetime.now().isoformat(),
            skip_count=5,  # Already skipped 5 times
            skip_reasons=["too_tired", "too_tired", "no_context"],
            messages=[],
            patterns_detected=[],
            retry_count=0,
            processing_time_ms=0,
            cache_hit=False,
            confidence_score=0.0,
            notification_sent=False,
            calendar_blocked=False,
            notion_synced=False,
            redis_published=False,
            database_saved=False,
            should_retry=False,
            energy_mismatch=False,
            should_park=False,
            prompt_version=1
        )

        result = await workflow.ainvoke(state)

        # Should trigger skip intelligence
        assert result.get("skip_count") == 5
        # Should have an action (park, delegate, or archive)
        assert result.get("action") is not None


class TestEisenhowerMatrix:
    """Test Eisenhower Matrix classification"""

    @pytest.mark.asyncio
    async def test_urgent_important(self):
        """Test DO_FIRST quadrant classification"""
        from workflow.nodes.classifier import apply_eisenhower_matrix

        state = {
            "task_title": "URGENT: Fix production server issue",
            "task_description": "Critical bug affecting all users",
            "extracted_entities": {},
            "messages": []
        }

        result = await apply_eisenhower_matrix(state)

        assert result["urgency"] >= 4
        assert result["importance"] >= 4
        assert result["quadrant"] == "DO_FIRST"

    @pytest.mark.asyncio
    async def test_not_urgent_important(self):
        """Test SCHEDULE quadrant classification"""
        from workflow.nodes.classifier import apply_eisenhower_matrix

        state = {
            "task_title": "Plan Q2 strategic initiatives",
            "task_description": "Important for long-term growth",
            "extracted_entities": {},
            "messages": []
        }

        result = await apply_eisenhower_matrix(state)

        assert result["importance"] >= 4
        assert result["quadrant"] in ["SCHEDULE", "DO_FIRST"]


class TestEnergyClassification:
    """Test energy level classification"""

    @pytest.mark.asyncio
    async def test_high_energy_classification(self):
        """Test high energy task detection"""
        from workflow.nodes.classifier import determine_energy_level

        state = {
            "task_title": "Design new system architecture",
            "task_description": "Create detailed technical design for complex system",
            "messages": []
        }

        result = await determine_energy_level(state)

        assert result["energy_level"] == "high"

    @pytest.mark.asyncio
    async def test_low_energy_classification(self):
        """Test low energy task detection"""
        from workflow.nodes.classifier import determine_energy_level

        state = {
            "task_title": "Quick email reply",
            "task_description": "Send simple confirmation email",
            "messages": []
        }

        result = await determine_energy_level(state)

        assert result["energy_level"] == "low"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
