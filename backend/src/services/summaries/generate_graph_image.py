"""
Script to generate an image visualization of the LangGraph pipeline.
Exports the graph as PNG using the draw_mermaid_png method.
"""
import sys
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_src))

from plain_language_report_agent import PlainLanguageReportAgent


def generate_graph_image(output_path: str = None):
    """
    Generate a PNG image of the LangGraph pipeline.
    
    Args:
        output_path: Path to save the image. Defaults to 'pipeline_graph.png' in docs folder.
    """
    if output_path is None:
        # Save to docs folder in repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        docs_folder = repo_root / "docs"
        docs_folder.mkdir(exist_ok=True)
        output_path = str(docs_folder / "pipeline_graph.png")
    
    print("Initializing PlainLanguageReportAgent...")
    agent = PlainLanguageReportAgent(enable_provenance=True)
    
    # Get the compiled graph
    compiled_graph = agent.graph
    
    # Try to get the graph visualization
    print("Generating graph visualization...")
    
    try:
        # Method 1: Try draw_mermaid_png (requires additional dependencies)
        png_data = compiled_graph.get_graph().draw_mermaid_png()
        
        with open(output_path, "wb") as f:
            f.write(png_data)
        print(f"Graph image saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Could not generate PNG directly: {e}")
        print("Trying Mermaid text output instead...")
        
        try:
            # Method 2: Get Mermaid diagram as text
            mermaid_text = compiled_graph.get_graph().draw_mermaid()
            mermaid_path = output_path.replace(".png", ".mmd")
            
            with open(mermaid_path, "w") as f:
                f.write(mermaid_text)
            print(f"Mermaid diagram saved to: {mermaid_path}")
            print("\nMermaid diagram content:")
            print(mermaid_text)
            return mermaid_path
            
        except Exception as e2:
            print(f"Could not generate Mermaid output: {e2}")
            
            # Method 3: Just print the graph structure
            try:
                graph = compiled_graph.get_graph()
                print("\nGraph Structure:")
                print(f"Nodes: {list(graph.nodes.keys())}")
                print(f"Edges: {list(graph.edges)}")
            except Exception as e3:
                print(f"Could not inspect graph: {e3}")
            
            return None


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    generate_graph_image(output_path)
