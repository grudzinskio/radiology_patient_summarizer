"""
Fidelity Component - Check A: Missing Fact Detector
Ensures all critical medical facts from the original report are present in the summary.
"""
from typing import List
from rapidfuzz import fuzz
from backend.app.services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
from backend.app.schemas.validation import ValidationInput, ValidationResult
from backend.app.services.summaries.validation.config import (
    ENTITY_FUZZY_MATCH_THRESHOLD,
    ENTITY_CASE_SENSITIVE,
)


class FidelityComponent(PipelineComponent):
    """
    Validates that all critical entities (findings, anatomy, measurements) 
    from the original report appear in the summary.
    """
    
    def __init__(self):
        self.component_name = "FidelityCheck"
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Check if all entities from the original report are present in the summary.
        Returns ValidationInput with validation result attached.
        """
        # Collect all critical entities
        all_entities = []
        all_entities.extend(input.extracted_entities.findings)
        all_entities.extend(input.extracted_entities.anatomy)
        all_entities.extend(input.extracted_entities.measurements)
        
        # Remove duplicates and empty strings
        all_entities = list(set([e.strip() for e in all_entities if e.strip()]))
        
        # Normalize summary text for matching
        summary_lower = input.draft_summary.lower() if not ENTITY_CASE_SENSITIVE else input.draft_summary
        
        # Check each entity
        missing_entities = []
        found_entities = []
        
        for entity in all_entities:
            entity_normalized = entity.lower() if not ENTITY_CASE_SENSITIVE else entity
            
            # First try exact match (case-insensitive if configured)
            if entity_normalized in summary_lower:
                found_entities.append(entity)
                continue
            
            # Try fuzzy matching for variations
            # Split entity into words and check if all words appear
            entity_words = entity_normalized.split()
            if len(entity_words) > 1:
                # For multi-word entities, check if all words appear in summary
                all_words_found = all(word in summary_lower for word in entity_words if len(word) > 2)
                if all_words_found:
                    found_entities.append(entity)
                    continue
            
            # Use fuzzy string matching as fallback
            best_match_ratio = 0
            summary_words = summary_lower.split()
            
            # Check against each word/phrase in summary
            for i in range(len(summary_words)):
                for j in range(i + 1, min(i + len(entity_words) + 2, len(summary_words) + 1)):
                    phrase = " ".join(summary_words[i:j])
                    ratio = fuzz.ratio(entity_normalized, phrase)
                    best_match_ratio = max(best_match_ratio, ratio)
            
            if best_match_ratio >= ENTITY_FUZZY_MATCH_THRESHOLD:
                found_entities.append(entity)
            else:
                missing_entities.append(entity)
        
        # Create validation result
        passed = len(missing_entities) == 0
        error_messages = []
        
        if not passed:
            error_messages.append(
                f"Missing {len(missing_entities)} critical entities in summary: {', '.join(missing_entities[:5])}"
                + (f" and {len(missing_entities) - 5} more" if len(missing_entities) > 5 else "")
            )
        
        validation_result = ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=error_messages,
            metadata={
                "total_entities": len(all_entities),
                "found_entities": len(found_entities),
                "missing_entities": len(missing_entities),
                "missing_entity_list": missing_entities,
            }
        )
        
        # Attach result to input (will be collected by pipeline)
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
