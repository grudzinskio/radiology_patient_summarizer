from backend.app.services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
from typing import Any

class EntityMatchingComponent(PipelineComponent):
    """
    Component for matching entities in the summary to the medical report, ensuring that all entities (should be laymans terms but can be technical) from the original report are present in the summary.
    """
    
    def __init__(self):
        self.component_name = "EntityMatchingComponent"
    
    def process(self, input: Any) -> Any:
        """
        Process the input and return the output
        """
        return self.match_entities(input)

    def match_entities(self, summary: str, original_report: str) -> Any:
        """
        Match entities in the summary to the medical report
        """
        return summary, original_report