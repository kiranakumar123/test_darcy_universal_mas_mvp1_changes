#!/usr/bin/env python3
"""
Universal Framework Workflow Visualizer

Creates comprehensive workflow visualizations without Docker dependency.
Generates Mermaid diagrams, ASCII representations, and workflow analysis.

Usage:
    python visualize_workflow.py [--output-dir OUTPUT] [--format FORMAT]

Formats:
    - mermaid: Interactive Mermaid diagram
    - ascii: Terminal-friendly ASCII representation
    - analysis: Detailed workflow structure analysis
    - all: Generate all formats (default)
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "src"))

from langgraph.graph import END, StateGraph

from universal_framework.contracts.state import UniversalWorkflowState


def create_workflow_graph() -> StateGraph:
    """Create a simplified workflow graph for visualization"""
    workflow = StateGraph(UniversalWorkflowState)

    # Add core workflow phases
    phases = [
        "initialization",
        "discovery",
        "analysis",
        "generation",
        "review",
        "delivery",
    ]

    # Add nodes
    for phase in phases:
        workflow.add_node(phase, lambda state: state)

    # Create linear workflow progression
    workflow.set_entry_point("initialization")
    for i in range(len(phases) - 1):
        workflow.add_edge(phases[i], phases[i + 1])

    workflow.add_edge("delivery", END)

    return workflow


def generate_mermaid_diagram(workflow: StateGraph, output_dir: Path) -> str:
    """Generate Mermaid diagram and save to file"""
    compiled_workflow = workflow.compile()

    try:
        mermaid_code = compiled_workflow.get_graph().draw_mermaid()

        # Save to file
        mermaid_file = output_dir / "universal_workflow.mmd"
        mermaid_file.write_text(mermaid_code)

        print(f"✅ Mermaid diagram saved to: {mermaid_file}")
        print("\n🎯 Mermaid Diagram Code:")
        print("=" * 60)
        print(mermaid_code)
        print("=" * 60)

        print("\n💡 How to View:")
        print("1. Copy the code above")
        print("2. Go to https://mermaid.live")
        print("3. Paste to see interactive diagram")
        print("4. Or use Mermaid Preview in VS Code")

        return mermaid_code

    except Exception as e:
        print(f"❌ Error generating Mermaid diagram: {e}")
        return ""


def generate_ascii_diagram(workflow: StateGraph) -> str:
    """Generate ASCII representation of workflow"""
    compiled_workflow = workflow.compile()

    try:
        ascii_graph = compiled_workflow.get_graph().draw_ascii()

        print("\n🔍 ASCII Workflow Representation:")
        print("=" * 60)
        print(ascii_graph)
        print("=" * 60)

        return ascii_graph

    except Exception as e:
        print(f"❌ Error generating ASCII diagram: {e}")
        return ""


def analyze_workflow_structure(workflow: StateGraph, output_dir: Path):
    """Analyze and document workflow structure"""
    compiled_workflow = workflow.compile()
    graph = compiled_workflow.get_graph()

    analysis = []
    analysis.append("# Universal Framework Workflow Analysis")
    analysis.append("=" * 50)
    analysis.append("")

    # Basic metrics
    analysis.append(f"**Total Nodes:** {len(graph.nodes)}")
    analysis.append(f"**Total Edges:** {len(graph.edges)}")
    analysis.append("")

    # Workflow phases
    analysis.append("## Workflow Phases")
    phases = [
        "initialization",
        "discovery",
        "analysis",
        "generation",
        "review",
        "delivery",
    ]
    for i, phase in enumerate(phases, 1):
        analysis.append(f"{i}. **{phase.title()}**")
    analysis.append("")

    # Flow diagram
    analysis.append("## Workflow Flow")
    analysis.append("```")
    analysis.append(
        "START → initialization → discovery → analysis → generation → review → delivery → END"
    )
    analysis.append("```")
    analysis.append("")

    # Node details
    analysis.append("## Node Details")
    for node_id in graph.nodes:
        analysis.append(f"- **{node_id}**")
    analysis.append("")

    # Edge relationships
    analysis.append("## Edge Relationships")
    for edge in graph.edges:
        analysis.append(f"- {edge}")
    analysis.append("")

    # Save analysis
    analysis_text = "\n".join(analysis)
    analysis_file = output_dir / "workflow_analysis.md"
    analysis_file.write_text(analysis_text)

    print("📋 Workflow Structure Analysis:")
    print("=" * 60)
    print(analysis_text)

    print(f"\n📁 Analysis saved to: {analysis_file}")


def scan_actual_framework_components(output_dir: Path):
    """Scan and document actual framework components"""
    framework_root = project_root / "src" / "universal_framework"

    components = {"agents": [], "nodes": [], "workflow": [], "api": [], "contracts": []}

    # Scan each component directory
    for component_type in components.keys():
        component_dir = framework_root / component_type
        if component_dir.exists():
            for file in component_dir.iterdir():
                if file.suffix == ".py" and not file.name.startswith("__"):
                    name = file.stem.replace("_", " ").title()
                    components[component_type].append(name)

    # Generate component report
    report = []
    report.append("# Universal Framework Components Inventory")
    report.append("=" * 50)
    report.append("")

    for component_type, items in components.items():
        if items:
            report.append(f"## {component_type.title()}")
            for item in sorted(items):
                report.append(f"- {item}")
            report.append("")

    report_text = "\n".join(report)
    report_file = output_dir / "framework_components.md"
    report_file.write_text(report_text)

    print("🏗️ Framework Components Inventory:")
    print("=" * 60)
    print(report_text)

    print(f"📁 Component inventory saved to: {report_file}")


def main():
    """Main visualization function"""
    parser = argparse.ArgumentParser(
        description="Universal Framework Workflow Visualizer"
    )
    parser.add_argument(
        "--output-dir",
        default="./visualizations",
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--format",
        choices=["mermaid", "ascii", "analysis", "all"],
        default="all",
        help="Visualization format to generate",
    )

    args = parser.parse_args()

    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("🚀 Universal Framework Workflow Visualizer")
    print(f"📁 Output Directory: {output_dir.absolute()}")
    print("=" * 60)

    try:
        # Create workflow graph
        print("🔧 Building workflow graph...")
        workflow = create_workflow_graph()
        print("✅ Workflow graph created successfully!")

        # Generate requested formats
        if args.format in ["mermaid", "all"]:
            generate_mermaid_diagram(workflow, output_dir)

        if args.format in ["ascii", "all"]:
            generate_ascii_diagram(workflow)

        if args.format in ["analysis", "all"]:
            analyze_workflow_structure(workflow, output_dir)
            scan_actual_framework_components(output_dir)

        print("\n✅ Visualization complete!")
        print(f"📁 Files saved to: {output_dir.absolute()}")

        print("\n💡 Next Steps:")
        print("• View Mermaid diagrams at https://mermaid.live")
        print("• Use ASCII diagrams for quick reference")
        print("• Review analysis for workflow understanding")
        print("• When Docker is available, use: langgraph up")

    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
