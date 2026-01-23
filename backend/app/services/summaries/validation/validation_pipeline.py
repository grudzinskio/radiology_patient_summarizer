from backend.app.services.summaries.validation.pipeline_component import PipelineComponent
from typing import Any

class ValidationPipeline:
    """
    Validation pipeline for plain-language summaries of medical reports
    """
    def __init__(self):
        self.components = []
    
    def add_component(self, component: PipelineComponent):
        """
        Add a component to the pipeline
        """
        self.components.append(component)
    
    def process(self, input: Any) -> Any:
        """
        Process the input through the pipeline
        """
        for component in self.components:
            input = component.process(input)
        return input