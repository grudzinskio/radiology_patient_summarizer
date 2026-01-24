from services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
from schemas.validation import ValidationInput, ValidationReport, ValidationResult
from typing import Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """
    Validation pipeline for plain-language summaries of medical reports.
    Orchestrates multiple validation components and aggregates results.
    """
    
    def __init__(self, components: List[PipelineComponent] = []):
        self.components: List[PipelineComponent] = components

    def add_component(self, component: PipelineComponent):
        """
        Add a component to the pipeline.
        """
        self.components.append(component)
        logger.info(f"Added validation component: {component.component_name if hasattr(component, 'component_name') else type(component).__name__}")
    

    def remove_component(self, component_name: str) -> bool:
        """
        Remove a component from the pipeline by name.
        
        Args:
            component_name: Name of the component to remove
            
        Returns:
            True if component was found and removed, False otherwise
        """
        for i, component in enumerate(self.components):
            if hasattr(component, 'component_name') and component.component_name == component_name:
                removed = self.components.pop(i)
                logger.info(f"Removed validation component: {component_name}")
                return True
        return False
    
    def get_component(self, component_name: str) -> Optional[PipelineComponent]:
        """
        Retrieve a component by name.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            The component if found, None otherwise
        """
        for component in self.components:
            if hasattr(component, 'component_name') and component.component_name == component_name:
                return component
        return None
    
    def process(self, input: Any) -> Any:
        """
        Process the input through the pipeline (legacy method).
        For new code, use validate() instead.
        
        Args:
            input: Input to process
            
        Returns:
            Processed input
        """
        for component in self.components:
            input = component.process(input)
        return input
    
    def validate(self, validation_input: ValidationInput) -> ValidationReport:
        """
        Validate a summary by running all components and aggregating results.
        
        Args:
            validation_input: ValidationInput containing original report, entities, and summary
            
        Returns:
            ValidationReport with aggregated results from all components
        """
        # Initialize validation results list on input
        validation_input._validation_results = []
        
        # Run each component
        for component in self.components:
            try:
                validation_input = component.process(validation_input)
            except Exception as e:
                # Log error but continue with other components
                logger.error(f"Error in validation component {component.component_name if hasattr(component, 'component_name') else type(component).__name__}: {str(e)}")
                
                # Create error result for this component
                error_result = ValidationResult(
                    component_name=component.component_name if hasattr(component, 'component_name') else type(component).__name__,
                    passed=False,
                    error_messages=[f"Component error: {str(e)}"],
                    metadata={"error_type": type(e).__name__}
                )
                validation_input._validation_results.append(error_result)
        
        # Collect all results
        component_results = validation_input._validation_results if hasattr(validation_input, '_validation_results') else []
        
        # Determine overall pass/fail
        overall_passed = all(result.passed for result in component_results)
        
        # Generate summary
        if overall_passed:
            summary_text = "All validation checks passed."
        else:
            failed_count = sum(1 for result in component_results if not result.passed)
            summary_text = f"{failed_count} of {len(component_results)} validation checks failed."
        
        # Create validation report
        validation_report = ValidationReport(
            overall_passed=overall_passed,
            component_results=component_results,
            summary=summary_text
        )
        
        return validation_report