"""
Step 2: The Summarizer
Generates an initial plain language summary of a medical report.

Supports two modes:
1. Standard mode: Returns plain text summary
2. Provenance mode: Returns structured JSON with citations for explainability
"""
from typing import Optional, Tuple, List, Dict, Any
import json
import logging
from schemas.validation import EntityExtractionResult
from schemas.provenance import SummaryWithProvenance, StatementProvenance, ProvenanceReport
from utils.clients.llm_clients import BaseLLMClient, OpenAIClient

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """
    Orchestrates the summarization process.
    Generates an initial plain language summary of a medical report.
    Supports provenance tracking for explainability.
    """
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """
        Initialize the summarizer agent.
        
        Args:
            llm_client: LLM client for generating summaries (defaults to OpenAIClient)
        """
        self.llm_client = llm_client or OpenAIClient()
    
    def generate_summary(
        self, 
        original_report: str, 
        extracted_entities: EntityExtractionResult, 
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """
        Generate a plain text summary of the medical report.
        
        Args:
            original_report: The original medical report
            extracted_entities: The entities extracted from the original report
            retrieved_definitions: The dictionary of medical term definitions
            
        Returns:
            The summary text
        """
        summary_prompt = self._build_summary_prompt(
            original_report=original_report,
            extracted_entities=extracted_entities,
            retrieved_definitions=retrieved_definitions
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a warm, caring medical translator who helps patients understand their medical reports. "
                    "Write like you're having a friendly conversation with someone who is anxious about their results. "
                    "Be reassuring and natural—never robotic or clinical. "
                    "Avoid repeating the same information in different ways. "
                    "Group related findings together into flowing sentences rather than listing each fact separately."
                )
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
    
    def generate_summary_with_provenance(
        self, 
        original_report: str, 
        extracted_entities: EntityExtractionResult, 
        retrieved_definitions: Optional[dict] = None
    ) -> SummaryWithProvenance:
        """
        Generate a summary with provenance tracking for explainability.
        Returns structured data with citations linking summary statements to source text.
        
        Args:
            original_report: The original medical report
            extracted_entities: The entities extracted from the original report
            retrieved_definitions: The dictionary of medical term definitions
            
        Returns:
            SummaryWithProvenance containing the summary and citation mappings
        """
        summary_prompt = self._build_provenance_prompt(
            original_report=original_report,
            extracted_entities=extracted_entities,
            retrieved_definitions=retrieved_definitions
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a warm, caring medical translator who helps patients understand their medical reports. "
                    "Write like you're having a friendly conversation with someone who is anxious about their results. "
                    "Be reassuring and natural—never robotic or clinical. "
                    "Avoid repeating the same information in different ways. "
                    "Group related findings together into flowing sentences rather than listing each fact separately. "
                    "You MUST respond with valid JSON only, no additional text."
                )
            },
            {
                "role": "user",
                "content": summary_prompt
            }
        ]
        
        try:
            response = self.llm_client.generate(messages)
            logger.info(f"Generated provenance response (length: {len(response)} chars)")
            
            # Parse JSON response
            parsed = self._parse_provenance_response(response, original_report)
            return parsed
            
        except Exception as e:
            logger.error(f"Error generating summary with provenance: {str(e)}")
            # Fallback to standard summary without provenance
            plain_summary = self.generate_summary(original_report, extracted_entities, retrieved_definitions)
            return SummaryWithProvenance.from_text(plain_summary)
    
    def _parse_provenance_response(self, response: str, original_report: str) -> SummaryWithProvenance:
        """
        Parse the LLM's JSON response into a SummaryWithProvenance object.
        
        Args:
            response: The raw LLM response (should be JSON)
            original_report: The original report for reference
            
        Returns:
            SummaryWithProvenance object with parsed provenance data
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
        
        # Try to find JSON block if it's buried in other text
        if "{" in response and "}" in response:
            try:
                start_idx = response.find("{")
                end_idx = response.rfind("}") + 1
                json_part = response[start_idx:end_idx]
                data = json.loads(json_part)
            except json.JSONDecodeError:
                # Fallback to standard cleaning
                try:
                    data = json.loads(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}. Using fallback parsing.")
                    return SummaryWithProvenance.from_text(response)
        else:
            try:
                data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}. Using fallback parsing.")
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
                # Simple string format
                statement_text = stmt_data
                source_quotes = []
            elif isinstance(stmt_data, dict):
                # Full format with citations
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
        
        # Build the full summary text from statements
        plain_language_report = "\n\n".join(statements)
        
        provenance_report = ProvenanceReport(mappings=mappings)
        provenance_report.calculate_metrics()
        
        return SummaryWithProvenance(
            plain_language_report=plain_language_report,
            statements=statements,
            provenance=provenance_report
        )
    
    def _build_summary_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the standard summary prompt (plain text output)."""
        
        prompt_parts = [
            "TASK: Create a warm, natural summary of this medical report for a patient.",
            "",
            "CRITICAL - USE PLAIN LANGUAGE ONLY:",
            "- You MUST replace ALL medical terms with their plain language definitions below.",
            "- NEVER use jargon like 'acute infarct', 'hemorrhage', 'ischemic change', 'diffusion restriction'.",
            "- Instead say things like 'stroke', 'bleeding', 'small blood vessel changes', etc.",
            "- If a definition is provided below, USE IT - don't keep the medical term.",
            "",
            "WRITING STYLE:",
            "- Write like you're talking to a friend who is nervous about their results.",
            "- Sound human and warm, NOT like a robot listing facts.",
            "- NEVER repeat the same finding in different words.",
            "- Group related findings naturally (e.g., 'The good news is there's no sign of stroke, bleeding, or tumors').",
            "- Start with WHY the scan was done conversationally.",
            "- Use contractions and natural phrasing (it's, there's, you're).",
        ]
        
        prompt_parts.extend([
            "",
            "ACCURACY REQUIREMENTS:",
            "1. Include all key findings from the extracted entities list below.",
            "2. Do NOT invent any findings not in the original report.",
            "3. Use 6th grade reading level with simple, everyday words.",
            "4. Keep sentences short (under 15 words).",
            "5. Do NOT give medical advice or use alarming language.",
            "",
            "AVOID THESE COMMON MISTAKES:",
            "- Using medical jargon when a plain definition is available.",
            "- Saying 'Reason: X. Also: X' - that's redundant and robotic.",
            "- Listing the same finding multiple ways.",
            "- Starting every sentence similarly.",
            "",
            "ORIGINAL REPORT:",
            original_report,
            "",
            "KEY FINDINGS TO INCLUDE (mention each once, in plain language):",
            _format_entity_list(extracted_entities),
            "",
        ])
        
        if retrieved_definitions:
            prompt_parts.extend([
                "PLAIN LANGUAGE TRANSLATIONS (YOU MUST USE THESE instead of medical terms):",
            ])
            for term, definition in list(retrieved_definitions.items())[:15]:
                prompt_parts.append(f"- Instead of '{term}', say: {definition}")
            prompt_parts.append("")
        
        prompt_parts.append("Now write a friendly, natural summary using ONLY plain language that any patient can understand.")
        
        return "\n".join(prompt_parts)
    
    def _build_provenance_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the provenance-aware summary prompt (JSON output with citations)."""
        
        prompt_parts = [
            "TASK: Create a warm, natural summary of this medical report WITH SOURCE CITATIONS.",
            "",
            "CRITICAL - USE PLAIN LANGUAGE ONLY:",
            "- You MUST replace ALL medical terms with their plain language definitions below.",
            "- NEVER use jargon like 'acute infarct', 'hemorrhage', 'ischemic change', 'diffusion restriction'.",
            "- Instead say things like 'stroke', 'bleeding', 'small blood vessel changes', etc.",
            "- If a definition is provided below, USE IT - don't keep the medical term.",
            "",
            "WRITING STYLE:",
            "- Write like you're talking to a friend who is nervous about their results.",
            "- Sound human and warm, NOT like a robot listing facts.",
            "- NEVER repeat the same finding in different words.",
            "- Group related findings naturally (e.g., 'The good news is there's no sign of stroke, bleeding, or tumors').",
            "- Start with WHY the scan was done conversationally.",
            "- Use contractions and natural phrasing.",
            "",
            "You must respond with valid JSON in this exact format:",
            "{",
            '  "statements": [',
            '    {',
            '      "text": "Your summary sentence in warm, PLAIN language (no medical jargon).",',
            '      "source_quotes": ["exact quote from original report"]',
            '    }',
            '  ]',
            "}",
            "",
            "REQUIREMENTS:",
            "1. Each statement must use plain language from the definitions below.",
            "2. Cite specific text from the original report for each statement.",
            "3. Include all key findings (but mention each only ONCE).",
            "4. Do NOT invent findings. Do NOT give medical advice.",
            "5. Use 6th grade reading level. Sentences under 15 words.",
            "",
            "ORIGINAL REPORT:",
            original_report,
            "",
            "KEY FINDINGS TO INCLUDE (translate each to plain language):",
            _format_entity_list(extracted_entities),
        ]
        
        if retrieved_definitions:
            prompt_parts.extend([
                "",
                "PLAIN LANGUAGE TRANSLATIONS (YOU MUST USE THESE instead of medical terms):",
            ])
            for term, definition in list(retrieved_definitions.items())[:15]:
                prompt_parts.append(f"- Instead of '{term}', say: {definition}")
        
        prompt_parts.extend([
            "",
            "Respond ONLY with valid JSON, no other text."
        ])
        
        return "\n".join(prompt_parts)


def _format_entity_list(extracted_entities: EntityExtractionResult) -> str:
    """
    Format entities for inclusion in prompts.
    
    Note: Only includes original_text and canonical_name to keep the list concise.
    Aliases are NOT included to avoid flooding the prompt with synonyms.
    """
    items: list[str] = []
    for entity in extracted_entities.entities:
        original_text = getattr(entity, "original_text", "") or ""
        canonical_name = getattr(entity, "canonical_name", "") or ""
        
        # Only add original text
        if original_text:
            items.append(original_text)
        
        # Add canonical name only if it's meaningfully different (not just case change)
        if canonical_name and canonical_name.lower() != original_text.lower():
            # Skip if canonical name looks like a worse link (e.g. "Cancer" when original is "contrast")
            if len(canonical_name) > len(original_text) * 3:
                continue  # Skip overly long canonical names
            items.append(canonical_name)
    
    # Deduplicate while preserving order
    unique_items = list(dict.fromkeys([item.strip() for item in items if item.strip()]))
    return ", ".join(unique_items) if unique_items else "None"