"""
Self-Correction Loop - Step 4: The Refiner
Automatically refines summaries when validation fails by providing specific error feedback.
"""
from typing import Optional, Tuple
import logging
from backend.app.schemas.validation import (
    ValidationInput,
    ValidationReport,
    EntityExtractionResult,
)
from backend.app.services.summaries.validation.validation_pipeline import ValidationPipeline
from backend.app.services.summaries.validation.config import MAX_RETRY_ATTEMPTS
from backend.app.utils.clients.llm_clients import BaseLLMClient, OpenAIClient

logger = logging.getLogger(__name__)


class SelfCorrectionLoop:
    """
    Orchestrates the validation and refinement process.
    Automatically refines summaries when validation fails.
    """
    
    def __init__(
        self,
        validation_pipeline: ValidationPipeline,
        llm_client: Optional[BaseLLMClient] = None
    ):
        """
        Initialize the self-correction loop.
        
        Args:
            validation_pipeline: Configured ValidationPipeline instance
            llm_client: LLM client for generating refined summaries (defaults to OpenAIClient)
        """
        self.validation_pipeline = validation_pipeline
        self.llm_client = llm_client or OpenAIClient()
    
    def refine_summary(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        current_summary: str,
        validation_report: ValidationReport,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """
        Generate a refined summary based on validation errors.
        
        Args:
            original_report: The original medical report
            extracted_entities: Entities extracted from the original report
            current_summary: The current summary that failed validation
            validation_report: ValidationReport containing error details
            retrieved_definitions: Optional dictionary of medical term definitions
            
        Returns:
            Refined summary text
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
            refined_summary = self.llm_client.generate(messages, temperature=0.3)
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
            "2. You MUST NOT include any medical findings, anatomy, or measurements that were not in the original report.",
            "3. Use 6th-8th grade reading level (simple, clear language).",
            "4. Do NOT give medical advice or recommendations.",
            "5. Do NOT use alarmist language or emergency phrases.",
            "6. Be empathetic and reassuring in tone.",
            "",
            "ORIGINAL REPORT:",
            original_report,
            "",
            "EXTRACTED ENTITIES (you must include all of these):",
            f"Findings: {', '.join(extracted_entities.findings) if extracted_entities.findings else 'None'}",
            f"Anatomy: {', '.join(extracted_entities.anatomy) if extracted_entities.anatomy else 'None'}",
            f"Measurements: {', '.join(extracted_entities.measurements) if extracted_entities.measurements else 'None'}",
            "",
            "CURRENT SUMMARY (that failed validation):",
            current_summary,
        ]
        
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
    
    def validate_and_refine(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        draft_summary: str,
        retrieved_definitions: Optional[dict] = None,
        max_retries: int = MAX_RETRY_ATTEMPTS
    ) -> Tuple[str, ValidationReport]:
        """
        Validate a summary and automatically refine it if validation fails.
        
        Args:
            original_report: The original medical report
            extracted_entities: Entities extracted from the original report
            draft_summary: Initial draft summary to validate
            retrieved_definitions: Optional dictionary of medical term definitions
            max_retries: Maximum number of refinement attempts (default from config)
            
        Returns:
            Tuple of (final_summary, final_validation_report)
        """
        current_summary = draft_summary
        attempt = 0
        
        while attempt <= max_retries:
            # Create validation input
            validation_input = ValidationInput(
                original_report=original_report,
                extracted_entities=extracted_entities,
                draft_summary=current_summary,
                retrieved_definitions=retrieved_definitions
            )
            
            # Run validation
            validation_report = self.validation_pipeline.validate(validation_input)
            
            logger.info(
                f"Validation attempt {attempt + 1}: "
                f"{'PASSED' if validation_report.overall_passed else 'FAILED'} "
                f"({len(validation_report.get_failed_components())} failed components)"
            )
            
            # If validation passed, return
            if validation_report.overall_passed:
                return current_summary, validation_report
            
            # If we've reached max retries, return current summary with failed validation
            if attempt >= max_retries:
                logger.warning(f"Reached max retry attempts ({max_retries}). Returning summary with validation failures.")
                return current_summary, validation_report
            
            # Refine the summary
            logger.info(f"Refining summary (attempt {attempt + 1}/{max_retries})...")
            current_summary = self.refine_summary(
                original_report=original_report,
                extracted_entities=extracted_entities,
                current_summary=current_summary,
                validation_report=validation_report,
                retrieved_definitions=retrieved_definitions
            )
            
            attempt += 1
        
        # Should not reach here, but return anyway
        return current_summary, validation_report
