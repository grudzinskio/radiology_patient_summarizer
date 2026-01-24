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
                    "You are an empathetic medical translator. Your job is to create patient-friendly "
                    "summaries of medical reports that are accurate, safe, and easy to understand. "
                    "You MUST respond with valid JSON only, no additional text."
                )
            },
            {
                "role": "user",
                "content": summary_prompt
            }
        ]
        
        try:
            response = self.llm_client.generate(messages, temperature=0.3)
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
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}. Using fallback parsing.")
            # Fallback: treat entire response as plain text
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
            "You are an empathetic medical translator. Your job is to create patient-friendly summaries of medical reports that are accurate, safe, and easy to understand.",
            "",
            "TASK: Create a plain language summary of the medical report below.",
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
            for term, definition in list(retrieved_definitions.items())[:10]:
                prompt_parts.append(f"- {term}: {definition}")
        
        return "\n".join(prompt_parts)
    
    def _build_provenance_prompt(
        self,
        original_report: str,
        extracted_entities: EntityExtractionResult,
        retrieved_definitions: Optional[dict] = None
    ) -> str:
        """Build the provenance-aware summary prompt (JSON output with citations)."""
        
        prompt_parts = [
            "TASK: Create a plain language summary of the medical report below WITH SOURCE CITATIONS.",
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
            "1. Each statement should be a complete, standalone sentence in plain language.",
            "2. Each statement MUST cite the specific text from the original report that supports it.",
            "3. source_quotes should be EXACT or near-exact quotes from the original report.",
            "4. You MUST include every item from the extracted entities list.",
            "5. You MUST NOT invent any medical findings, anatomy, or measurements.",
            "6. Use 6th-8th grade reading level (simple, clear language).",
            "7. Do NOT give medical advice or use alarmist language.",
            "8. Be empathetic and reassuring in tone.",
            "",
            "ORIGINAL REPORT:",
            original_report,
            "",
            "EXTRACTED ENTITIES (you must include all of these):",
            f"Findings: {', '.join(extracted_entities.findings) if extracted_entities.findings else 'None'}",
            f"Anatomy: {', '.join(extracted_entities.anatomy) if extracted_entities.anatomy else 'None'}",
            f"Measurements: {', '.join(extracted_entities.measurements) if extracted_entities.measurements else 'None'}",
        ]
        
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