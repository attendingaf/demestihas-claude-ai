"""
Lyco 2.0 Phase 4: Adaptive Intelligence Engine
Learns from usage patterns and dynamically adjusts system behavior
"""
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import hashlib

from .database import DatabaseManager
from .models import Task

logger = logging.getLogger(__name__)


class AdaptiveIntelligence:
    """Engine that learns from user behavior and optimizes system performance"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.db = DatabaseManager()
        self.anthropic_api_key = anthropic_api_key

        # Pattern detection thresholds
        self.PATTERN_MIN_OCCURRENCES = 3
        self.ANALYSIS_WINDOW_DAYS = 30
        self.CONFIDENCE_THRESHOLD = 0.7

        # Performance targets
        self.TARGET_COMPLETION_RATE = 0.6  # 60%
        self.TARGET_SKIP_RATE_MAX = 0.3    # 30%

    async def analyze_skip_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze skip patterns from the last N days to identify improvement opportunities"""
        logger.info(f"Analyzing skip patterns for last {days} days")

        try:
            # Get skip data with pattern analysis
            skip_data = await self._get_skip_pattern_data(days)

            # Identify consistent skip patterns
            patterns = await self._identify_skip_patterns(skip_data)

            # Analyze energy mismatches
            energy_analysis = await self._analyze_energy_mismatches(skip_data)

            # Detect context failures
            context_failures = await self._analyze_context_failures(skip_data)

            # Calculate improvement opportunities
            improvements = await self._calculate_improvement_opportunities(patterns, energy_analysis, context_failures)

            analysis = {
                "analysis_date": datetime.now().isoformat(),
                "window_days": days,
                "total_skips": len(skip_data),
                "patterns_detected": len(patterns),
                "energy_mismatches": energy_analysis,
                "context_failures": context_failures,
                "improvement_opportunities": improvements,
                "confidence_score": self._calculate_analysis_confidence(skip_data, patterns)
            }

            # Store analysis results
            await self._store_analysis_results(analysis)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing skip patterns: {e}")
            return {"error": str(e), "analysis_date": datetime.now().isoformat()}

    async def _get_skip_pattern_data(self, days: int) -> List[Dict[str, Any]]:
        """Get skip data with task content analysis"""
        query = """
        SELECT
            id, content, skipped_reason, energy_level, time_estimate,
            skipped_at, created_at, context_required, metadata,
            EXTRACT(HOUR FROM skipped_at) as skip_hour,
            EXTRACT(DOW FROM skipped_at) as skip_dow
        FROM tasks
        WHERE skipped_at IS NOT NULL
        AND skipped_at >= NOW() - INTERVAL '%s days'
        ORDER BY skipped_at DESC
        """ % days

        results = await self.db.fetch_all(query)
        return [dict(row) for row in results]

    async def _identify_skip_patterns(self, skip_data: List[Dict]) -> List[Dict[str, Any]]:
        """Identify patterns in skip behavior"""
        patterns = []

        # Group by various pattern types
        pattern_groups = {
            "content_keywords": {},
            "time_patterns": {},
            "energy_mismatches": {},
            "context_issues": {}
        }

        for skip in skip_data:
            # Content-based patterns
            content_hash = self._extract_content_pattern(skip["content"])
            if content_hash not in pattern_groups["content_keywords"]:
                pattern_groups["content_keywords"][content_hash] = []
            pattern_groups["content_keywords"][content_hash].append(skip)

            # Time-based patterns
            time_key = f"{skip['skip_hour']}h_dow{skip['skip_dow']}"
            if time_key not in pattern_groups["time_patterns"]:
                pattern_groups["time_patterns"][time_key] = []
            pattern_groups["time_patterns"][time_key].append(skip)

            # Energy mismatch patterns
            energy_key = f"{skip['energy_level']}_at_{skip['skip_hour']}h"
            if energy_key not in pattern_groups["energy_mismatches"]:
                pattern_groups["energy_mismatches"][energy_key] = []
            pattern_groups["energy_mismatches"][energy_key].append(skip)

        # Identify significant patterns
        for pattern_type, groups in pattern_groups.items():
            for pattern_key, skips in groups.items():
                if len(skips) >= self.PATTERN_MIN_OCCURRENCES:
                    pattern = {
                        "type": pattern_type,
                        "pattern": pattern_key,
                        "occurrences": len(skips),
                        "skip_reasons": list(set(s["skipped_reason"] for s in skips)),
                        "sample_tasks": [s["content"][:50] for s in skips[:3]],
                        "confidence": min(len(skips) / 10.0, 1.0),  # Confidence based on frequency
                        "suggested_action": self._suggest_pattern_action(pattern_type, skips)
                    }
                    patterns.append(pattern)

        return sorted(patterns, key=lambda x: x["occurrences"], reverse=True)

    def _extract_content_pattern(self, content: str) -> str:
        """Extract pattern from task content using keyword hashing"""
        # Simple keyword extraction - could be enhanced with NLP
        words = content.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in ['the', 'and', 'for', 'with', 'this', 'that']]

        # Create a pattern hash from top keywords
        if keywords:
            pattern_string = "_".join(sorted(keywords)[:3])  # Top 3 keywords
            return hashlib.md5(pattern_string.encode()).hexdigest()[:8]

        return "generic"

    def _suggest_pattern_action(self, pattern_type: str, skips: List[Dict]) -> str:
        """Suggest action based on pattern analysis"""
        most_common_reason = max(set(s["skipped_reason"] for s in skips),
                               key=lambda x: sum(1 for s in skips if s["skipped_reason"] == x))

        if pattern_type == "energy_mismatches":
            return f"Reschedule similar tasks to avoid {most_common_reason} periods"
        elif pattern_type == "time_patterns":
            return f"Adjust scheduling for tasks skipped with reason: {most_common_reason}"
        elif pattern_type == "content_keywords":
            return f"Improve task decomposition for similar content (reason: {most_common_reason})"
        else:
            return f"Address {most_common_reason} issues in task processing"

    async def _analyze_energy_mismatches(self, skip_data: List[Dict]) -> Dict[str, Any]:
        """Analyze energy level vs. skip time mismatches"""
        mismatches = {
            "high_energy_skips": [],
            "low_energy_attempts": [],
            "optimal_windows_missed": []
        }

        for skip in skip_data:
            hour = skip["skip_hour"]
            energy = skip["energy_level"]

            # High energy tasks skipped during low energy times
            if energy == "high" and hour > 16:
                mismatches["high_energy_skips"].append(skip)

            # Low energy tasks attempted during high energy times
            if energy == "low" and 9 <= hour <= 11:
                mismatches["low_energy_attempts"].append(skip)

            # Tasks skipped during their optimal energy window
            if ((energy == "high" and 9 <= hour <= 11) or
                (energy == "medium" and 14 <= hour <= 16)):
                mismatches["optimal_windows_missed"].append(skip)

        return {
            "high_energy_misplaced": len(mismatches["high_energy_skips"]),
            "low_energy_misplaced": len(mismatches["low_energy_attempts"]),
            "optimal_window_skips": len(mismatches["optimal_windows_missed"]),
            "mismatch_rate": len([m for mismatches_list in mismatches.values()
                                for m in mismatches_list]) / max(len(skip_data), 1)
        }

    async def _analyze_context_failures(self, skip_data: List[Dict]) -> Dict[str, Any]:
        """Analyze context-related skip patterns"""
        context_skips = [s for s in skip_data if s["skipped_reason"] in ["missing-context", "need-someone"]]

        context_analysis = {
            "total_context_skips": len(context_skips),
            "context_skip_rate": len(context_skips) / max(len(skip_data), 1),
            "common_missing_contexts": {},
            "delegation_opportunities": 0
        }

        for skip in context_skips:
            context_req = skip.get("context_required", [])
            for context in context_req:
                if context not in context_analysis["common_missing_contexts"]:
                    context_analysis["common_missing_contexts"][context] = 0
                context_analysis["common_missing_contexts"][context] += 1

            if skip["skipped_reason"] == "need-someone":
                context_analysis["delegation_opportunities"] += 1

        return context_analysis

    async def _calculate_improvement_opportunities(self, patterns: List[Dict],
                                                energy_analysis: Dict,
                                                context_failures: Dict) -> List[Dict[str, Any]]:
        """Calculate specific improvement opportunities"""
        opportunities = []

        # Energy optimization opportunities
        if energy_analysis["mismatch_rate"] > 0.2:  # 20% mismatch threshold
            opportunities.append({
                "type": "energy_optimization",
                "priority": "high",
                "impact_estimate": energy_analysis["mismatch_rate"] * 0.7,  # 70% of mismatches could be fixed
                "description": "Optimize task scheduling based on energy levels",
                "action": "update_energy_scheduling_prompts"
            })

        # Pattern-based opportunities
        for pattern in patterns:
            if pattern["confidence"] > self.CONFIDENCE_THRESHOLD:
                opportunities.append({
                    "type": "pattern_optimization",
                    "priority": "medium" if pattern["occurrences"] > 5 else "low",
                    "impact_estimate": pattern["occurrences"] / len(patterns),
                    "description": f"Address {pattern['type']} pattern: {pattern['pattern']}",
                    "action": pattern["suggested_action"]
                })

        # Context improvement opportunities
        if context_failures["context_skip_rate"] > 0.15:  # 15% threshold
            opportunities.append({
                "type": "context_improvement",
                "priority": "medium",
                "impact_estimate": context_failures["context_skip_rate"] * 0.5,
                "description": "Improve context detection and task preparation",
                "action": "enhance_context_prompts"
            })

        return sorted(opportunities, key=lambda x: x["impact_estimate"], reverse=True)

    def _calculate_analysis_confidence(self, skip_data: List[Dict], patterns: List[Dict]) -> float:
        """Calculate confidence in the analysis based on data quality and quantity"""
        data_size_factor = min(len(skip_data) / 50.0, 1.0)  # Optimal at 50+ skips
        pattern_quality_factor = sum(p["confidence"] for p in patterns) / max(len(patterns), 1)

        return (data_size_factor * 0.6 + pattern_quality_factor * 0.4)

    async def generate_prompt_adjustments(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific LLM prompt adjustments based on analysis"""
        adjustments = []

        for opportunity in analysis.get("improvement_opportunities", []):
            if opportunity["action"] == "update_energy_scheduling_prompts":
                adjustments.append({
                    "prompt_type": "energy_assessment",
                    "adjustment_type": "enhancement",
                    "description": "Improve energy level detection and scheduling",
                    "new_content": self._generate_energy_prompt_improvement(analysis),
                    "expected_impact": opportunity["impact_estimate"]
                })

            elif opportunity["action"] == "enhance_context_prompts":
                adjustments.append({
                    "prompt_type": "context_detection",
                    "adjustment_type": "enhancement",
                    "description": "Better context requirement detection",
                    "new_content": self._generate_context_prompt_improvement(analysis),
                    "expected_impact": opportunity["impact_estimate"]
                })

        return adjustments

    def _generate_energy_prompt_improvement(self, analysis: Dict) -> str:
        """Generate improved energy assessment prompt"""
        base_prompt = """
        When analyzing tasks for energy levels, pay special attention to:

        HIGH ENERGY (9-11am optimal):
        - Strategic planning and analysis
        - Creative work and design
        - Complex problem-solving
        - Important decisions

        MEDIUM ENERGY (2-4pm optimal):
        - Communication and meetings
        - Reviews and feedback
        - Routine but important tasks

        LOW ENERGY (4pm+ optimal):
        - Administrative tasks
        - Reading and research
        - Organizing and filing
        """

        # Add specific insights from analysis
        energy_mismatches = analysis.get("energy_mismatches", {})
        if energy_mismatches.get("optimal_window_skips", 0) > 0:
            base_prompt += "\n\nIMPORTANT: Even optimal energy tasks are being skipped. Consider if tasks are too complex or poorly defined."

        return base_prompt

    def _generate_context_prompt_improvement(self, analysis: Dict) -> str:
        """Generate improved context detection prompt"""
        context_failures = analysis.get("context_failures", {})
        common_contexts = context_failures.get("common_missing_contexts", {})

        base_prompt = """
        When analyzing tasks, carefully identify required context:

        COMPUTER REQUIRED:
        - Email tasks, document creation, research
        - Any task involving software or online tools

        PHONE REQUIRED:
        - Calls, text messages, voice communications

        QUIET ENVIRONMENT:
        - Deep work, analysis, writing
        - Tasks requiring concentration
        """

        if common_contexts:
            most_common = max(common_contexts.items(), key=lambda x: x[1])
            base_prompt += f"\n\nNOTE: '{most_common[0]}' context is frequently missing. Be more careful detecting this requirement."

        return base_prompt

    async def update_processor_prompts(self, adjustments: List[Dict]) -> Dict[str, Any]:
        """Apply prompt adjustments with version tracking"""
        results = {
            "updated_prompts": 0,
            "version_changes": [],
            "errors": []
        }

        for adjustment in adjustments:
            try:
                # Create new prompt version
                version_name = f"adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Store new prompt version
                await self._store_prompt_version(
                    version_name,
                    adjustment["prompt_type"],
                    adjustment["new_content"],
                    adjustment.get("expected_impact", 0.0)
                )

                # Activate new version
                await self._activate_prompt_version(version_name, adjustment["prompt_type"])

                results["updated_prompts"] += 1
                results["version_changes"].append({
                    "type": adjustment["prompt_type"],
                    "version": version_name,
                    "description": adjustment["description"]
                })

                logger.info(f"Updated {adjustment['prompt_type']} prompt to version {version_name}")

            except Exception as e:
                error_msg = f"Failed to update {adjustment['prompt_type']}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        return results

    async def _store_prompt_version(self, version_name: str, prompt_type: str,
                                  content: str, expected_impact: float):
        """Store new prompt version in database"""
        query = """
        INSERT INTO prompt_versions (version_name, prompt_type, prompt_content, performance_metrics)
        VALUES ($1, $2, $3, $4)
        """

        metrics = {"expected_impact": expected_impact, "created_by": "adaptive_intelligence"}

        await self.db.execute(query, version_name, prompt_type, content, json.dumps(metrics))

    async def _activate_prompt_version(self, version_name: str, prompt_type: str):
        """Activate a prompt version and deactivate previous ones"""
        # Deactivate current version
        await self.db.execute("""
            UPDATE prompt_versions
            SET is_active = false, deactivated_at = NOW()
            WHERE prompt_type = $1 AND is_active = true
        """, prompt_type)

        # Activate new version
        await self.db.execute("""
            UPDATE prompt_versions
            SET is_active = true, activated_at = NOW()
            WHERE version_name = $1 AND prompt_type = $2
        """, version_name, prompt_type)

    async def measure_improvement(self, baseline_days: int = 7) -> Dict[str, Any]:
        """Measure improvement in system performance after adaptations"""
        # Get current performance metrics
        current_metrics = await self._get_performance_metrics(baseline_days)

        # Get historical performance for comparison
        historical_metrics = await self._get_performance_metrics(
            baseline_days,
            offset_days=baseline_days
        )

        improvement = {
            "measurement_date": datetime.now().isoformat(),
            "baseline_days": baseline_days,
            "current_period": current_metrics,
            "comparison_period": historical_metrics,
            "improvements": {},
            "regressions": {}
        }

        # Calculate improvements
        for metric, current_value in current_metrics.items():
            if metric in historical_metrics:
                historical_value = historical_metrics[metric]
                if historical_value > 0:  # Avoid division by zero
                    change_pct = ((current_value - historical_value) / historical_value) * 100

                    if change_pct > 5:  # Significant improvement
                        improvement["improvements"][metric] = {
                            "change_percent": round(change_pct, 1),
                            "current": current_value,
                            "previous": historical_value
                        }
                    elif change_pct < -5:  # Significant regression
                        improvement["regressions"][metric] = {
                            "change_percent": round(change_pct, 1),
                            "current": current_value,
                            "previous": historical_value
                        }

        # Store measurement results
        await self._store_improvement_measurement(improvement)

        return improvement

    async def _get_performance_metrics(self, days: int, offset_days: int = 0) -> Dict[str, float]:
        """Get performance metrics for a specific time period"""
        end_date = datetime.now() - timedelta(days=offset_days)
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed_count,
            COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped_count,
            COUNT(*) as total_count,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) FILTER (WHERE completed_at IS NOT NULL) as avg_completion_time,
            COUNT(*) FILTER (WHERE energy_level = 'high' AND completed_at IS NOT NULL) as high_energy_completed,
            COUNT(*) FILTER (WHERE energy_level = 'high') as high_energy_total
        FROM tasks
        WHERE created_at >= $1 AND created_at <= $2
        """

        result = await self.db.fetch_one(query, start_date, end_date)

        if not result or result["total_count"] == 0:
            return {}

        metrics = {
            "completion_rate": result["completed_count"] / result["total_count"],
            "skip_rate": result["skipped_count"] / result["total_count"],
            "avg_completion_time": result["avg_completion_time"] or 0,
            "high_energy_accuracy": (result["high_energy_completed"] / max(result["high_energy_total"], 1))
        }

        return {k: round(v, 3) for k, v in metrics.items()}

    async def _store_analysis_results(self, analysis: Dict[str, Any]):
        """Store analysis results for future reference"""
        # This could be enhanced to store in a dedicated analysis_results table
        logger.info(f"Analysis completed: {len(analysis.get('patterns_detected', 0))} patterns found")

    async def _store_improvement_measurement(self, measurement: Dict[str, Any]):
        """Store improvement measurement results"""
        # This could be enhanced to store in a dedicated measurements table
        logger.info(f"Improvement measurement: {len(measurement.get('improvements', {}))} metrics improved")
