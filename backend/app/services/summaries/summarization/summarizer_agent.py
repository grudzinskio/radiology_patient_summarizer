"""
Self-Correction Loop - Step 4: The Refiner
Automatically refines summaries when validation fails by providing specific error feedback.
"""
from typing import Optional
import logging
from backend.app.schemas.validation import EntityExtractionResult
from backend.app.utils.clients.llm_clients import BaseLLMClient, OpenAIClient

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """
    Orchestrates the summarization process.
    Generates an initial plain language summary of a medical report.
    """
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """
        Initialize the summarizer agent.
        
        Args:
            llm_client: LLM client for generating summaries (defaults to OpenAIClient)
        """
        self.llm_client = llm_client or OpenAIClient()
    
    def generate_summary(self, original_report: str, extracted_entities: EntityExtractionResult, retrieved_definitions: Optional[dict] = None) -> str:
        """
        Generate a summary of the medical report.
        
        Args:
            original_report: The original medical report
            extracted_entities: The entities extracted from the original report
            retrieved_definitions: The dictionary of medical term definitions
            
        Returns:
            The summary text
        """
        # Collect all error messages
        summary_prompt = self._build_summary_prompt(
            original_report=original_report,
            extracted_entities=extracted_entities,
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
                "content": summary_prompt
            }
        ]
        
        try:
            summary = self.llm_client.generate(messages)
            logger.info(f"Generated summary (length: {len(summary)} chars)")
            return summary.strip()
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return ""
    
    def _build_summary_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the summary prompt."""
        
        prompt_parts = [
            "Your previous summary failed validation. Please rewrite it to fix the following errors:",
            "",
            "VALIDATION ERRORS:",
        ]
        
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
            "Please generate a patient-friendly summary of the original report.",
        ])
        
        if retrieved_definitions:
            prompt_parts.extend([
                "",
                "MEDICAL TERM DEFINITIONS (use these when explaining terms):",
            ])
            for term, definition in list(retrieved_definitions.items())[:10]:  # Limit to first 10
                prompt_parts.append(f"- {term}: {definition}")
        
        return "\n".join(prompt_parts)