"""
Self-Correction Loop - Step 4: The Refiner
Automatically refines summaries when validation fails by providing specific error feedback.
"""
from typing import Optional, Tuple, List
import logging
import json
from schemas.validation import (
    ValidationInput,
    ValidationReport,
    EntityExtractionResult,
)
from schemas.provenance import SummaryWithProvenance, StatementProvenance, ProvenanceReport
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
            llm_client: LLM client for generating refined summaries (defaults to OpenAIClient)
        """
        self.llm_client = llm_client or OpenAIClient()
    
    def refine_summary(
        self, 
        original_report: str, 
        extracted_entities: EntityExtractionResult, 
        current_summary: str, 
        validation_report: ValidationReport, 
        retrieved_definitions: Optional[dict] = None
    ) -> SummaryWithProvenance:
        """
        Refine the summary based on validation errors.
        Returns a structured summary with provenance (citations).
        
        Args:
            original_report: The original medical report
            extracted_entities: The entities extracted from the original report
            current_summary: The current summary that failed validation
            validation_report: The validation report containing error details
            retrieved_definitions: The dictionary of medical term definitions
            
        Returns:
            The refined SummaryWithProvenance object
        """
        # Collect all error messages
        error_messages = validation_report.get_all_errors()
        failed_components = [r.component_name for r in validation_report.get_failed_components()]
        
        # Build refinement prompt
        refinement_prompt = self._build_refinement_provenance_prompt(
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
                "content": (
                    "You are an empathetic medical translator. Your job is to create patient-friendly "
                    "summaries of medical reports that are accurate, safe, and easy to understand. "
                    "You MUST respond with valid JSON only, no additional text."
                )
            },
            {
                "role": "user",
                "content": refinement_prompt
            }
        ]
        
        try:
            response = self.llm_client.generate(messages)
            logger.info(f"Generated refined summary response (length: {len(response)} chars)")
            
            # Parse JSON response
            return self._parse_refinement_response(response, original_report)
            
        except Exception as e:
            logger.error(f"Error generating refined summary: {str(e)}")
            # Fallback: return the original failed summary wrapped in provenance
            # This allows the pipeline to continue (though it will likely fail again)
            return SummaryWithProvenance.from_text(current_summary)

    def _parse_refinement_response(self, response: str, original_report: str) -> SummaryWithProvenance:
        """
        Parse the LLM's JSON response into a SummaryWithProvenance object.
        Reuses logic similar to SummarizerAgent.
        """
        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        data = {}
        try:
            # Try to find JSON block
            if "{" in response and "}" in response:
                start_idx = response.find("{")
                end_idx = response.rfind("}") + 1
                json_part = response[start_idx:end_idx]
                data = json.loads(json_part)
            else:
                data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON refinement response: {e}. Returning fallback text.")
            return SummaryWithProvenance.from_text(response)
        
        # Extract statements and build provenance
        statements_data = data.get("statements", [])
        if not statements_data:
            # Try alternative key names
            statements_data = data.get("sentences", []) or data.get("summary", [])
        
        statements: List[str] = []
        mappings: List[StatementProvenance] = []
        
        for i, stmt_data in enumerate(statements_data):
            if isinstance(stmt_data, str):
                statement_text = stmt_data
                source_quotes = []
            elif isinstance(stmt_data, dict):
                statement_text = stmt_data.get("text", "") or stmt_data.get("statement", "")
                source_quotes = stmt_data.get("source_quotes", []) or stmt_data.get("citations", []) or stmt_data.get("sources", [])
            else:
                continue
            
            if not statement_text:
                continue
            
            statements.append(statement_text)
            
            mapping = StatementProvenance(
                statement_index=i,
                statement_text=statement_text,
                source_quotes=source_quotes if isinstance(source_quotes, list) else [source_quotes],
                source_spans=[],  # Will be populated by ProvenanceComponent
                confidence_score=0.0,
                has_source_backing=len(source_quotes) > 0
            )
            mappings.append(mapping)
        
        # Build the full summary text
        plain_language_report = "\n\n".join(statements)
        
        provenance_report = ProvenanceReport(mappings=mappings)
        provenance_report.calculate_metrics()
        
        return SummaryWithProvenance(
            plain_language_report=plain_language_report,
            statements=statements,
            provenance=provenance_report
        )

    def _build_refinement_provenance_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        current_summary: str,
        error_messages: list,
        failed_components: list,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the refinement prompt requesting JSON output."""
        
        prompt_parts = [
            "Your previous summary failed validation. Please rewrite it to fix the errors below.",
            "",
            "VALIDATION ERRORS:",
        ]
        
        for i, error in enumerate(error_messages, 1):
            prompt_parts.append(f"{i}. {error}")
            
        # Add specific guidance for readability failures
        if "ReadabilityCheck" in failed_components:
            prompt_parts.extend([
                "",
                "⚠️ CRITICAL READABILITY FIX REQUIRED:",
                "Your previous summary was TOO COMPLEX. You MUST:",
                "- Break EVERY long sentence into 2-3 shorter ones (MAX 12-15 words each)",
                "- Replace ALL technical terms with simple words from the definitions below",
                "- Use everyday words: 'germ' not 'pathogen', 'found' not 'identified', 'study' not 'investigate'",
                "- Write as if explaining to a 12-year-old",
                "- One idea per sentence. No compound sentences.",
            ])

        prompt_parts.extend([
            "",
            "TASK: Create a REVISED plain language summary of the medical report below WITH SOURCE CITATIONS.",
            "",
            "You must respond with valid JSON in this exact format:",
            "{",
            '  "statements": [',
            '    {',
            '      "text": "Your first summary sentence in plain language.",',
            '      "source_quotes": ["exact quote from original report that supports this"]',
            '    },',
            '    {',
            '      "text": "Your second summary sentence.",',
            '      "source_quotes": ["supporting quote 1", "supporting quote 2"]',
            '    }',
            '  ]',
            "}",
            "",
            "REQUIREMENTS:",
            "1. Address ALL validation errors listed above.",
            "2. Each statement should be a complete, standalone sentence in plain language.",
            "3. Each statement MUST cite the specific text from the original report that supports it.",
            "4. source_quotes should be EXACT or near-exact quotes from the original report.",
            "5. You MUST include every item from the extracted entities list.",
            "6. You MUST NOT invent any clinical entities.",
            "7. Use 6th-8th grade reading level (simple, clear language).",
            "8. Do NOT give medical advice or use alarmist language.",
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
            for term, definition in list(retrieved_definitions.items())[:10]:
                prompt_parts.append(f"- {term}: {definition}")
        
        prompt_parts.extend([
            "",
            "Respond ONLY with valid JSON, no other text."
        ])
        
        return "\n".join(prompt_parts)


def _format_entity_list(extracted_entities: EntityExtractionResult) -> str:
    """Format entities for inclusion in prompts."""
    items: list[str] = []
    for entity in extracted_entities.entities:
        original_text = getattr(entity, "original_text", "") or ""
        canonical_name = getattr(entity, "canonical_name", "") or ""
        aliases = getattr(entity, "aliases", []) or []
        if original_text:
            items.append(original_text)
        if canonical_name and canonical_name.lower() != original_text.lower():
            items.append(canonical_name)
        original_lower = original_text.lower()
        canonical_lower = canonical_name.lower() if canonical_name else ""
        for alias in aliases:
            alias_lower = alias.lower() if alias else ""
            if alias_lower and alias_lower not in (original_lower, canonical_lower):
                items.append(alias)
    unique_items = list(dict.fromkeys([item.strip() for item in items if item.strip()]))
    return ", ".join(unique_items) if unique_items else "None"
