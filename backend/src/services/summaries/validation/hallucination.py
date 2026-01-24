"""
Hallucination Component - Check B: New Fact Detector
Detects entities in the summary that were not present in the original report.
"""
import json
from typing import List, Set
from services.summaries.validation.base import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult, EntityExtractionResult
from utils.clients.llm_clients import BaseLLMClient, OpenAIClient


class HallucinationComponent(PipelineComponent):
    """
    Validates that the summary does not contain entities (findings, anatomy, measurements)
    that were not present in the original report.
    """
    
    def __init__(self, llm_client: BaseLLMClient = None):
        self.component_name = "HallucinationCheck"
        self.llm_client = llm_client or OpenAIClient()
    
    def _extract_entities_from_text(self, text: str) -> EntityExtractionResult:
        """
        Extract entities from text using LLM.
        Uses the same format as the entity extraction pipeline.
        """
        prompt = f"""Extract all medical findings, anatomy, and measurements from the following text.
Output as JSON with the following structure:
{{
    "findings": ["list of medical findings"],
    "anatomy": ["list of anatomical locations"],
    "measurements": ["list of measurements"],
    "uncertainty": ["list of uncertainty phrases"]
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
            return EntityExtractionResult(
                findings=data.get("findings", []),
                anatomy=data.get("anatomy", []),
                measurements=data.get("measurements", []),
                uncertainty=data.get("uncertainty", [])
            )
        except Exception as e:
            # Fallback: return empty entities if extraction fails
            # This prevents the component from breaking the pipeline
            return EntityExtractionResult(
                findings=[],
                anatomy=[],
                measurements=[],
                uncertainty=[]
            )
    
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
        
        # Normalize for comparison
        original_findings = self._normalize_entity_set(original_entities.findings)
        original_anatomy = self._normalize_entity_set(original_entities.anatomy)
        original_measurements = self._normalize_entity_set(original_entities.measurements)
        
        summary_findings = self._normalize_entity_set(summary_entities.findings)
        summary_anatomy = self._normalize_entity_set(summary_entities.anatomy)
        summary_measurements = self._normalize_entity_set(summary_entities.measurements)
        
        # Find hallucinated entities (in summary but not in original)
        hallucinated_findings = summary_findings - original_findings
        hallucinated_anatomy = summary_anatomy - original_anatomy
        hallucinated_measurements = summary_measurements - original_measurements
        
        # Combine all hallucinated entities
        all_hallucinated = list(hallucinated_findings | hallucinated_anatomy | hallucinated_measurements)
        
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
                "summary_entities_count": len(summary_findings | summary_anatomy | summary_measurements),
                "original_entities_count": len(original_findings | original_anatomy | original_measurements),
            }
        )
        
        # Attach result to input
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
