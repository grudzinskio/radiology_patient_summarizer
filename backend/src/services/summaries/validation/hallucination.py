"""
Hallucination Component - Check B: New Fact Detector
Detects entities in the summary that were not present in the original report.
"""
import json
from typing import List, Set
from services.summaries.validation.base import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
from utils.clients.llm_clients import BaseLLMClient, OpenAIClient


class HallucinationComponent(PipelineComponent):
    """
    Validates that the summary does not contain clinical entities
    that were not present in the original report.
    """
    
    def __init__(self, llm_client: BaseLLMClient = None):
        self.component_name = "HallucinationCheck"
        self.llm_client = llm_client or OpenAIClient()
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """
        Extract entities from text using LLM.
        Uses the same format as the entity extraction pipeline.
        """
        prompt = f"""Extract all clinical entities from the following text.
Output as JSON with the following structure:
{{
    "entities": ["list of clinical entity strings"]
}}

Text to analyze:
{text}

Return only valid JSON, no additional text."""

        try:
            messages = [
                {"role": "system", "content": "You are a medical entity extraction system. Extract entities and return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_client.generate(messages)
            
            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            entities = data.get("entities", [])
            return entities if isinstance(entities, list) else []
        except Exception as e:
            # Fallback: return empty entities if extraction fails
            # This prevents the component from breaking the pipeline
            return []
    
    def _normalize_entity_set(self, entities: List[str]) -> Set[str]:
        """
        Normalize entities for comparison (lowercase, remove duplicates, filter empty).
        """
        normalized = set()
        for entity in entities:
            entity_clean = entity.strip().lower()
            if entity_clean and len(entity_clean) > 1:  # Filter out single characters
                normalized.add(entity_clean)
        return normalized
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Check if summary contains entities not present in the original report.
        Returns ValidationInput with validation result attached.
        """
        # Get original entities (already extracted)
        original_entities = input.extracted_entities
        
        # Extract entities from summary
        summary_entities = self._extract_entities_from_text(input.draft_summary)
        
        original_terms = []
        for entity in original_entities.entities:
            original_text = getattr(entity, "original_text", "") or ""
            canonical_name = getattr(entity, "canonical_name", "") or ""
            if original_text:
                original_terms.append(original_text)
            if canonical_name and canonical_name.lower() != original_text.lower():
                original_terms.append(canonical_name)

        original_set = self._normalize_entity_set(original_terms)
        summary_set = self._normalize_entity_set(summary_entities)
        
        # Find hallucinated entities (in summary but not in original)
        all_hallucinated = list(summary_set - original_set)
        
        # Create validation result
        passed = len(all_hallucinated) == 0
        error_messages = []
        
        if not passed:
            error_messages.append(
                f"Found {len(all_hallucinated)} entities in summary not present in original report: "
                + ", ".join(all_hallucinated[:5])
                + (f" and {len(all_hallucinated) - 5} more" if len(all_hallucinated) > 5 else "")
            )
        
        validation_result = ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=error_messages,
            metadata={
                "hallucinated_count": len(all_hallucinated),
                "hallucinated_entities": all_hallucinated,
                "summary_entities_count": len(summary_set),
                "original_entities_count": len(original_set),
            }
        )
        
        # Attach result to input
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
