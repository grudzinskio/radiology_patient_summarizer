"""
Provenance Component - Validates and enriches provenance mappings for summary statements.

This component:
1. Verifies that cited source quotes exist in the original report
2. Calculates exact character/line positions for each citation
3. Computes per-statement confidence scores based on source matching
4. Aggregates validation results into confidence factors
"""
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz
from services.summaries.validation.base import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
from schemas.provenance import (
    SourceSpan,
    StatementProvenance,
    ProvenanceReport,
    SummaryWithProvenance,
)


class ProvenanceComponent(PipelineComponent):
    """
    Validates provenance mappings and calculates confidence scores.
    Enriches summary statements with verified source spans.
    """
    
    def __init__(self, fuzzy_match_threshold: int = 70):
        """
        Initialize the provenance component.
        
        Args:
            fuzzy_match_threshold: Minimum fuzzy match ratio (0-100) to consider a match valid
        """
        self.component_name = "ProvenanceCheck"
        self.fuzzy_match_threshold = fuzzy_match_threshold
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Process the validation input to verify and enrich provenance mappings.
        
        Args:
            input: ValidationInput containing original report, entities, and draft summary
            
        Returns:
            ValidationInput with provenance validation result attached
        """
        original_text = input.original_report
        summary_text = input.draft_summary
        
        # Get or create provenance data
        provenance_report = self._get_or_create_provenance(input, summary_text, original_text)
        
        # Verify each statement's source citations
        verified_count = 0
        total_confidence = 0.0
        unverified_statements = []
        
        for mapping in provenance_report.mappings:
            # Try to find source spans for this statement
            verified = self._verify_statement_sources(mapping, original_text)
            
            if verified:
                verified_count += 1
                mapping.has_source_backing = True
            else:
                unverified_statements.append(mapping.statement_text[:50] + "...")
            
            # Calculate confidence for this statement
            self._calculate_statement_confidence(mapping, input)
            total_confidence += mapping.confidence_score
        
        # Update provenance report metrics
        provenance_report.calculate_metrics()
        
        # Store provenance report on input for downstream use
        input._provenance_report = provenance_report
        
        # Create validation result
        coverage = provenance_report.validation_coverage
        passed = coverage >= 0.5  # At least 50% of statements need source backing
        
        error_messages = []
        if not passed:
            error_messages.append(
                f"Only {coverage*100:.0f}% of summary statements have verified source backing. "
                f"Target is at least 50%."
            )
        if unverified_statements:
            error_messages.append(
                f"{len(unverified_statements)} statements lack source verification"
            )
        
        validation_result = ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=error_messages,
            metadata={
                "total_statements": provenance_report.total_statements,
                "backed_statements": provenance_report.backed_statements,
                "validation_coverage": round(coverage, 3),
                "overall_confidence": round(provenance_report.overall_confidence, 3),
                "unverified_statements": unverified_statements[:5],  # First 5
            }
        )
        
        # Attach result to input
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
    
    def _get_or_create_provenance(
        self, 
        input: ValidationInput, 
        summary_text: str, 
        original_text: str
    ) -> ProvenanceReport:
        """
        Get existing provenance from input or create new one by parsing summary.
        """
        # Check if provenance already exists
        if hasattr(input, '_provenance_report') and input._provenance_report:
            return input._provenance_report
        
        # Check if summary with provenance exists
        if hasattr(input, '_summary_with_provenance') and input._summary_with_provenance:
            return input._summary_with_provenance.provenance
        
        # Create new provenance by parsing summary into statements
        summary_with_prov = SummaryWithProvenance.from_text(summary_text)
        input._summary_with_provenance = summary_with_prov
        
        return summary_with_prov.provenance
    
    def _verify_statement_sources(
        self, 
        mapping: StatementProvenance, 
        original_text: str
    ) -> bool:
        """
        Verify that a statement has valid source backing in the original text.
        Updates the mapping's source_spans with verified spans.
        
        Returns True if at least one source span is verified.
        """
        verified_spans = []
        
        # First, try to find source spans from provided quotes
        for quote in mapping.source_quotes:
            span = SourceSpan.from_quote(quote, original_text)
            if span:
                verified_spans.append(span)
        
        # If no quotes or quotes not found, try to match statement content
        if not verified_spans:
            # Extract key phrases from the statement to search for
            key_phrases = self._extract_key_phrases(mapping.statement_text)
            
            for phrase in key_phrases:
                span = self._fuzzy_find_in_text(phrase, original_text)
                if span:
                    verified_spans.append(span)
        
        # Update mapping with verified spans
        mapping.source_spans = verified_spans
        mapping.has_source_backing = len(verified_spans) > 0
        
        return mapping.has_source_backing
    
    def _extract_key_phrases(self, statement: str) -> List[str]:
        """
        Extract key phrases from a statement that are likely to appear in the source.
        Focuses on medical terms, measurements, and specific findings.
        """
        import re
        
        phrases = []
        
        # Find measurements (e.g., "5mm", "2.3cm")
        measurements = re.findall(r'\d+(?:\.\d+)?\s*(?:mm|cm|ml|mg|%)', statement, re.IGNORECASE)
        phrases.extend(measurements)
        
        # Find quoted terms or specific medical-sounding phrases
        # Look for noun phrases with medical terminology
        words = statement.split()
        for i in range(len(words)):
            # Two-word phrases
            if i < len(words) - 1:
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 5 and not phrase.lower().startswith(('the ', 'a ', 'an ', 'your ', 'this ')):
                    phrases.append(phrase)
            
            # Three-word phrases
            if i < len(words) - 2:
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(phrase) > 8:
                    phrases.append(phrase)
        
        # Limit to most promising phrases
        return phrases[:10]
    
    def _fuzzy_find_in_text(self, phrase: str, text: str) -> Optional[SourceSpan]:
        """
        Do a fuzzy search for a phrase in the text.
        Returns a SourceSpan if a good match is found.
        """
        phrase_lower = phrase.lower().strip()
        text_lower = text.lower()
        
        # First try exact match
        idx = text_lower.find(phrase_lower)
        if idx != -1:
            return self._create_span_at_position(idx, len(phrase), text)
        
        # Try fuzzy matching against sliding windows
        words = text.split()
        phrase_word_count = len(phrase.split())
        
        best_match = None
        best_ratio = 0
        best_start = 0
        
        for i in range(len(words) - phrase_word_count + 1):
            window = ' '.join(words[i:i + phrase_word_count])
            ratio = fuzz.ratio(phrase_lower, window.lower())
            
            if ratio > best_ratio and ratio >= self.fuzzy_match_threshold:
                best_ratio = ratio
                best_match = window
                # Approximate start position
                best_start = text.find(words[i])
        
        if best_match and best_start >= 0:
            return self._create_span_at_position(best_start, len(best_match), text)
        
        return None
    
    def _create_span_at_position(self, start: int, length: int, text: str) -> SourceSpan:
        """Create a SourceSpan at the given position in the text."""
        end = start + length
        
        # Calculate line numbers
        lines_before = text[:start].count('\n')
        start_line = lines_before + 1
        lines_in_span = text[start:end].count('\n')
        end_line = start_line + lines_in_span
        
        return SourceSpan(
            start_char=start,
            end_char=end,
            start_line=start_line,
            end_line=end_line,
            text=text[start:end]
        )
    
    def _calculate_statement_confidence(
        self, 
        mapping: StatementProvenance, 
        input: ValidationInput
    ) -> None:
        """
        Calculate confidence score for a statement based on multiple factors.
        Updates the mapping's confidence_factors and confidence_score.
        """
        factors = {}
        
        # Factor 1: Source match quality (0.0 - 1.0)
        if mapping.source_spans:
            # More spans = higher confidence, up to 3
            span_count = min(len(mapping.source_spans), 3)
            factors['source_match'] = 0.4 + (span_count / 3) * 0.6
        else:
            factors['source_match'] = 0.2  # Low but not zero if no span found
        
        # Factor 2: Entity coverage - check if statement contains extracted entities
        entities_in_statement = self._count_entities_in_text(
            mapping.statement_text, 
            input.extracted_entities
        )
        if entities_in_statement > 0:
            factors['entity_coverage'] = min(0.3 + entities_in_statement * 0.2, 1.0)
        else:
            factors['entity_coverage'] = 0.5  # Neutral if no entities expected
        
        # Factor 3: Statement length - longer statements need more verification
        word_count = len(mapping.statement_text.split())
        if word_count < 10:
            factors['statement_complexity'] = 0.9  # Short statements are easier to verify
        elif word_count < 30:
            factors['statement_complexity'] = 0.7
        else:
            factors['statement_complexity'] = 0.5  # Long statements are harder to verify
        
        # Store factors and calculate weighted score
        mapping.confidence_factors = factors
        mapping.calculate_confidence()
    
    def _count_entities_in_text(self, text: str, entities) -> int:
        """Count how many extracted entities appear in the given text."""
        text_lower = text.lower()
        count = 0

        for entity in entities.entities:
            original_text = getattr(entity, "original_text", "") or ""
            canonical_name = getattr(entity, "canonical_name", "") or ""
            if original_text and original_text.lower() in text_lower:
                count += 1
            if canonical_name and canonical_name.lower() in text_lower:
                count += 1

        return count
