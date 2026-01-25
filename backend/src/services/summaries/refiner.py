"""
Self-Correction Loop - Step 4: The Refiner
Automatically refines summaries when validation fails by providing specific error feedback.
"""
from typing import Optional, Tuple
import logging
from schemas.validation import (
    ValidationInput,
    ValidationReport,
    EntityExtractionResult,
)
from services.summaries.validation.pipeline import ValidationPipeline
from services.summaries.validation.config import MAX_RETRY_ATTEMPTS
from utils.clients.llm_clients import BaseLLMClient, OpenAIClient

logger = logging.getLogger(__name__)


class RefinerAgent:
    """
    Orchestrates the validation and refinement process.
    Automatically refines summaries when validation fails.
    """
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """
        Initialize the refiner agent.
        
        Args:
            validation_pipeline: Configured ValidationPipeline instance
            llm_client: LLM client for generating refined summaries (defaults to OpenAIClient)
        """
        self.llm_client = llm_client or OpenAIClient()
    
    def refine_summary(self, original_report: str, extracted_entities: EntityExtractionResult, current_summary: str, validation_report: ValidationReport, retrieved_definitions: Optional[dict] = None) -> str:
        """
        Refine the summary based on validation errors.
        
        Args:
            original_report: The original medical report
            extracted_entities: The entities extracted from the original report
            current_summary: The current summary that failed validation
            validation_report: The validation report containing error details
            retrieved_definitions: The dictionary of medical term definitions
            
        Returns:
            The refined summary text
        """
        # Collect all error messages
        error_messages = validation_report.get_all_errors()
        failed_components = [r.component_name for r in validation_report.get_failed_components()]
        
        # Build refinement prompt
        refinement_prompt = self._build_refinement_prompt(
            original_report=original_report,
            extracted_entities=extracted_entities,
            current_summary=current_summary,
            error_messages=error_messages,
            failed_components=failed_components,
            retrieved_definitions=retrieved_definitions
        )
        
        # Generate refined summary
        messages = [
            {
                "role": "system",
                "content": "You are an empathetic medical translator. Your job is to create patient-friendly summaries of medical reports that are accurate, safe, and easy to understand."
            },
            {
                "role": "user",
                "content": refinement_prompt
            }
        ]
        
        try:
            refined_summary = self.llm_client.generate(messages)
            logger.info(f"Generated refined summary (length: {len(refined_summary)} chars)")
            return refined_summary.strip()
        except Exception as e:
            logger.error(f"Error generating refined summary: {str(e)}")
            # Return original summary if refinement fails
            return current_summary
    
    def _build_refinement_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        current_summary: str,
        error_messages: list,
        failed_components: list,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the refinement prompt with specific error feedback."""
        
        prompt_parts = [
            "Your previous summary failed validation. Please rewrite it to fix the following errors:",
            "",
            "VALIDATION ERRORS:",
        ]
        
        for i, error in enumerate(error_messages, 1):
            prompt_parts.append(f"{i}. {error}")
        
        prompt_parts.extend([
            "",
            "REQUIREMENTS:",
            "1. You MUST include every item from the extracted entities list below.",
            "2. You MUST NOT include any clinical entities that were not in the original report.",
            "3. Use 6th-8th grade reading level (simple, clear language).",
            "4. Do NOT give medical advice or recommendations.",
            "5. Do NOT use alarmist language or emergency phrases.",
            "6. Be empathetic and reassuring in tone.",
            "",
            "ORIGINAL REPORT:",
            original_report,
            "",
            "EXTRACTED ENTITIES (you must include all of these):",
            _format_entity_list(extracted_entities),
            "",
            "CURRENT SUMMARY (that failed validation):",
            current_summary,
        ])
        
        if retrieved_definitions:
            prompt_parts.extend([
                "",
                "MEDICAL TERM DEFINITIONS (use these when explaining terms):",
            ])
            for term, definition in list(retrieved_definitions.items())[:10]:  # Limit to first 10
                prompt_parts.append(f"- {term}: {definition}")
        
        prompt_parts.extend([
            "",
            "Please generate a revised patient-friendly summary that addresses all the validation errors above."
        ])
        
        return "\n".join(prompt_parts)


def _format_entity_list(extracted_entities: EntityExtractionResult) -> str:
    items: list[str] = []
    for entity in extracted_entities.entities:
        original_text = getattr(entity, "original_text", "") or ""
        canonical_name = getattr(entity, "canonical_name", "") or ""
        if original_text:
            items.append(original_text)
        if canonical_name and canonical_name.lower() != original_text.lower():
            items.append(canonical_name)
    unique_items = list(dict.fromkeys([item.strip() for item in items if item.strip()]))
    return ", ".join(unique_items) if unique_items else "None"