"""
Readability Component - Check C: Readability Score
Validates that the summary meets readability requirements (6th-8th grade level).
"""
import textstat
from services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
from services.summaries.validation.config import READABILITY_MAX_GRADE_LEVEL


class ReadabilityComponent(PipelineComponent):
    """
    Validates that the summary meets readability requirements using Flesch-Kincaid Grade Level.
    Target: 6th-8th grade reading level (score <= 8.0).
    """
    
    def __init__(self):
        self.component_name = "ReadabilityCheck"
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Calculate Flesch-Kincaid Grade Level and validate it meets the threshold.
        Returns ValidationInput with validation result attached.
        """
        summary_text = input.draft_summary
        
        # Calculate Flesch-Kincaid Grade Level
        try:
            grade_level = textstat.flesch_kincaid_grade(summary_text)
            reading_ease = textstat.flesch_reading_ease(summary_text)
            
            # Check if grade level is acceptable
            passed = grade_level <= READABILITY_MAX_GRADE_LEVEL
            
            error_messages = []
            if not passed:
                error_messages.append(
                    f"Readability score ({grade_level:.1f}) exceeds maximum allowed grade level ({READABILITY_MAX_GRADE_LEVEL}). "
                    f"Target: 6th-8th grade reading level."
                )
            
            validation_result = ValidationResult(
                component_name=self.component_name,
                passed=passed,
                error_messages=error_messages,
                metadata={
                    "flesch_kincaid_grade": round(grade_level, 2),
                    "flesch_reading_ease": round(reading_ease, 2),
                    "max_allowed_grade": READABILITY_MAX_GRADE_LEVEL,
                    "word_count": len(summary_text.split()),
                    "sentence_count": textstat.sentence_count(summary_text),
                }
            )
        except Exception as e:
            # If calculation fails, fail the check but don't break the pipeline
            validation_result = ValidationResult(
                component_name=self.component_name,
                passed=False,
                error_messages=[f"Failed to calculate readability score: {str(e)}"],
                metadata={"error": str(e)}
            )
        
        # Attach result to input
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
