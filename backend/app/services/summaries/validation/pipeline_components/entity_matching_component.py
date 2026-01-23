from backend.app.services.summaries.validation.pipeline_component import PipelineComponent
from typing import Any

class EntityMatchingComponent(PipelineComponent):
    """
    Component for matching entities in the summary to the medical report
    """
    def process(self, input: Any) -> Any:
        """
        Process the input and return the output
        """
        return input