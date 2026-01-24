from services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
import logging

logger = logging.getLogger(__name__)

class EntityMatchingComponent(PipelineComponent):
    """
    Component for matching entities in the summary to the medical report, ensuring that all entities (should be laymans terms but can be technical) from the original report are present in the summary.
    """
    
    def __init__(self):
        self.component_name = "EntityMatchingComponent"
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Process the input and return the output
        """
        result = self.match_entities(input)
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(result)
        return input

    def match_entities(self, input: ValidationInput) -> ValidationResult:
        """
        Match entities in the summary to the medical report
        """
        summary = input.draft_summary.lower()
        extracted_entities = input.extracted_entities
        
        missing_entities = []
        
        # Check findings
        for finding in extracted_entities.findings:
            if finding.lower() not in summary:
                # Ideally use fuzzy matching here, but simple string match for now as per previous placeholder
                # Or if the config suggests fuzzy match threshold, we should use rapidfuzz.
                # For now, let's just log it as missing if not exact substring.
                missing_entities.append(f"Finding not mentioned: {finding}")
                
        # Check anatomy
        for anatomy in extracted_entities.anatomy:
            if anatomy.lower() not in summary:
                 missing_entities.append(f"Anatomy not mentioned: {anatomy}")

        passed = len(missing_entities) == 0
        
        return ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=missing_entities,
            metadata={"found_count": len(extracted_entities.findings) + len(extracted_entities.anatomy) - len(missing_entities)}
        )