"""
Visualization utilities for LangGraph Studio.

Provides graph visualization and debugging tools.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64


class GraphVisualizer:
    """Create visual representations of the Lyco workflow"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_colors = {
            "capture": "#4CAF50",    # Green
            "parse": "#2196F3",      # Blue
            "classify": "#FF9800",   # Orange
            "route": "#9C27B0",      # Purple
            "action": "#F44336",     # Red
            "storage": "#607D8B",    # Blue Grey
            "monitoring": "#795548"  # Brown
        }

    def build_graph_from_workflow(self, workflow_structure: Dict[str, Any]):
        """
        Build NetworkX graph from workflow structure.

        Args:
            workflow_structure: Graph structure from workflow
        """
        # Clear existing graph
        self.graph.clear()

        # Add nodes
        for node in workflow_structure.get("nodes", []):
            node_type = self._get_node_type(node)
            self.graph.add_node(
                node,
                type=node_type,
                color=self.node_colors.get(node_type, "#9E9E9E")
            )

        # Add edges
        for edge in workflow_structure.get("edges", []):
            self.graph.add_edge(
                edge["from"],
                edge["to"],
                condition=edge.get("condition", "")
            )

    def _get_node_type(self, node_name: str) -> str:
        """Determine node type from name"""
        if "capture" in node_name:
            return "capture"
        elif "parse" in node_name:
            return "parse"
        elif "classify" in node_name or "energy" in node_name or "quadrant" in node_name:
            return "classify"
        elif "route" in node_name or "decision" in node_name:
            return "route"
        elif "notify" in node_name or "schedule" in node_name or "delegate" in node_name or "park" in node_name or "archive" in node_name:
            return "action"
        elif "cache" in node_name or "database" in node_name or "notion" in node_name:
            return "storage"
        elif "health" in node_name or "stats" in node_name:
            return "monitoring"
        else:
            return "default"

    def generate_visualization(self, format: str = "png") -> str:
        """
        Generate graph visualization.

        Args:
            format: Output format (png, svg, dot)

        Returns:
            Base64 encoded image or DOT string
        """
        if format == "dot":
            return self._generate_dot()

        # Create matplotlib figure
        plt.figure(figsize=(16, 12))

        # Use hierarchical layout
        pos = nx.spring_layout(self.graph, k=2, iterations=50)

        # Draw nodes with colors
        node_colors = [self.graph.nodes[node].get("color", "#9E9E9E")
                      for node in self.graph.nodes()]
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=3000,
            alpha=0.9
        )

        # Draw edges
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color="#666666",
            arrows=True,
            arrowsize=20,
            arrowstyle="-|>",
            width=2,
            alpha=0.6
        )

        # Draw labels
        nx.draw_networkx_labels(
            self.graph, pos,
            font_size=10,
            font_weight="bold"
        )

        # Add title
        plt.title("Lyco LangGraph Workflow", fontsize=16, fontweight="bold")
        plt.axis("off")
        plt.tight_layout()

        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format=format, dpi=150, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return image_base64

    def _generate_dot(self) -> str:
        """Generate DOT format for Graphviz"""
        lines = ["digraph LycoWorkflow {"]
        lines.append('    rankdir=TB;')
        lines.append('    node [shape=box, style=rounded];')

        # Add nodes with colors
        for node in self.graph.nodes():
            color = self.graph.nodes[node].get("color", "#9E9E9E")
            lines.append(f'    "{node}" [fillcolor="{color}", style=filled];')

        # Add edges
        for edge in self.graph.edges():
            condition = self.graph.edges[edge].get("condition", "")
            if condition:
                lines.append(f'    "{edge[0]}" -> "{edge[1]}" [label="{condition}"];')
            else:
                lines.append(f'    "{edge[0]}" -> "{edge[1]}";')

        lines.append("}")
        return "\n".join(lines)

    def analyze_graph(self) -> Dict[str, Any]:
        """
        Analyze graph structure and provide insights.

        Returns:
            Graph analysis results
        """
        analysis = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "is_connected": nx.is_weakly_connected(self.graph),
            "has_cycles": not nx.is_directed_acyclic_graph(self.graph),
            "longest_path_length": 0,
            "bottleneck_nodes": [],
            "orphan_nodes": [],
            "node_types": {}
        }

        # Find longest path if DAG
        if not analysis["has_cycles"]:
            try:
                longest = nx.dag_longest_path(self.graph)
                analysis["longest_path_length"] = len(longest)
                analysis["longest_path"] = longest
            except:
                pass

        # Find bottleneck nodes (high betweenness centrality)
        if self.graph.number_of_nodes() > 0:
            centrality = nx.betweenness_centrality(self.graph)
            sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            analysis["bottleneck_nodes"] = [
                node for node, score in sorted_centrality[:3] if score > 0
            ]

        # Find orphan nodes
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0:
                analysis["orphan_nodes"].append(node)

        # Count node types
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get("type", "unknown")
            analysis["node_types"][node_type] = analysis["node_types"].get(node_type, 0) + 1

        return analysis


class ExecutionTracer:
    """Trace and visualize workflow execution"""

    def __init__(self):
        self.traces = []
        self.current_trace = None

    def start_trace(self, execution_id: str, input_data: Dict[str, Any]):
        """Start a new execution trace"""
        self.current_trace = {
            "execution_id": execution_id,
            "start_time": datetime.now().isoformat(),
            "input": input_data,
            "steps": [],
            "errors": [],
            "output": None,
            "end_time": None
        }

    def add_step(self, node_name: str, state: Dict[str, Any], duration_ms: int):
        """Add a step to the current trace"""
        if not self.current_trace:
            return

        step = {
            "node": node_name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "state_snapshot": {
                "action": state.get("action"),
                "confidence": state.get("confidence_score"),
                "energy_level": state.get("energy_level"),
                "quadrant": state.get("quadrant")
            }
        }

        self.current_trace["steps"].append(step)

    def add_error(self, node_name: str, error: str):
        """Add an error to the current trace"""
        if not self.current_trace:
            return

        self.current_trace["errors"].append({
            "node": node_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def end_trace(self, output: Dict[str, Any]):
        """Complete the current trace"""
        if not self.current_trace:
            return

        self.current_trace["output"] = output
        self.current_trace["end_time"] = datetime.now().isoformat()
        self.traces.append(self.current_trace)
        self.current_trace = None

    def get_trace(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trace by ID"""
        for trace in self.traces:
            if trace["execution_id"] == execution_id:
                return trace
        return None

    def generate_trace_visualization(self, execution_id: str) -> str:
        """Generate HTML visualization of execution trace"""
        trace = self.get_trace(execution_id)
        if not trace:
            return "<p>Trace not found</p>"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, sans-serif; padding: 20px; }}
                .trace-header {{ background: #f5f5f5; padding: 15px; border-radius: 8px; }}
                .step {{ border-left: 3px solid #2196F3; padding: 10px; margin: 10px 0; }}
                .error {{ border-left: 3px solid #F44336; background: #ffebee; }}
                .metric {{ display: inline-block; margin: 5px 10px; }}
                .metric-label {{ font-size: 12px; color: #666; }}
                .metric-value {{ font-size: 18px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Execution Trace: {execution_id}</h2>
            <div class="trace-header">
                <div class="metric">
                    <div class="metric-label">Start Time</div>
                    <div class="metric-value">{trace['start_time']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Steps</div>
                    <div class="metric-value">{len(trace['steps'])}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Errors</div>
                    <div class="metric-value">{len(trace['errors'])}</div>
                </div>
            </div>

            <h3>Execution Steps</h3>
        """

        for step in trace["steps"]:
            html += f"""
            <div class="step">
                <strong>{step['node']}</strong> - {step['duration_ms']}ms
                <br>State: {json.dumps(step['state_snapshot'], indent=2)}
            </div>
            """

        if trace["errors"]:
            html += "<h3>Errors</h3>"
            for error in trace["errors"]:
                html += f"""
                <div class="step error">
                    <strong>{error['node']}</strong>
                    <br>Error: {error['error']}
                </div>
                """

        html += """
        </body>
        </html>
        """

        return html


# Example usage
def create_sample_visualization():
    """Create a sample visualization"""
    visualizer = GraphVisualizer()

    # Sample workflow structure
    workflow = {
        "nodes": [
            "capture_email", "capture_terminal", "parse_task",
            "classify_energy", "assign_quadrant", "route_action",
            "notify_user", "schedule_calendar", "cache_task",
            "save_database"
        ],
        "edges": [
            {"from": "capture_email", "to": "parse_task"},
            {"from": "capture_terminal", "to": "parse_task"},
            {"from": "parse_task", "to": "classify_energy"},
            {"from": "classify_energy", "to": "assign_quadrant"},
            {"from": "assign_quadrant", "to": "route_action"},
            {"from": "route_action", "to": "notify_user", "condition": "urgent"},
            {"from": "route_action", "to": "schedule_calendar", "condition": "schedule"},
            {"from": "notify_user", "to": "cache_task"},
            {"from": "schedule_calendar", "to": "cache_task"},
            {"from": "cache_task", "to": "save_database"}
        ]
    }

    visualizer.build_graph_from_workflow(workflow)

    # Generate DOT format
    dot = visualizer._generate_dot()
    print("DOT Format:\n", dot)

    # Analyze graph
    analysis = visualizer.analyze_graph()
    print("\nGraph Analysis:")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    create_sample_visualization()
