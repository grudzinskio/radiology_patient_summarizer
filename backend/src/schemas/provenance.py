"""
Provenance Schemas - Data structures for tracking source provenance and explainability.

These structures enable:
1. Tracing which parts of the original report support each summary statement
2. Confidence scoring for each statement based on validation results
3. Rich metadata for human-in-the-loop review
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    """
    A span of text in the original source document.
    Enables precise highlighting and traceability.
    """
    start_char: int = Field(..., description="Character offset start (0-indexed)")
    end_char: int = Field(..., description="Character offset end (exclusive)")
    start_line: int = Field(..., description="Line number start (1-indexed)")
    end_line: int = Field(..., description="Line number end (1-indexed, inclusive)")
    text: str = Field(..., description="The actual text content of this span")
    
    @classmethod
    def from_quote(cls, quote: str, full_text: str) -> Optional["SourceSpan"]:
        """
        Create a SourceSpan by finding a quote within the full text.
        Returns None if the quote is not found.
        """
        # Normalize whitespace for matching
        normalized_quote = ' '.join(quote.split()).lower()
        normalized_text = ' '.join(full_text.split()).lower()
        
        # Try to find in normalized form
        if normalized_quote in normalized_text:
            # Find the original position (approximate)
            idx = full_text.lower().find(quote.lower()[:20])  # Use first 20 chars
            if idx == -1:
                # Try word-by-word matching
                words = quote.split()[:3]  # First 3 words
                search_term = words[0] if words else quote
                idx = full_text.lower().find(search_term.lower())
            
            if idx != -1:
                # Calculate line numbers
                lines_before = full_text[:idx].count('\n')
                start_line = lines_before + 1
                end_char = min(idx + len(quote), len(full_text))
                lines_in_span = full_text[idx:end_char].count('\n')
                end_line = start_line + lines_in_span
                
                return cls(
                    start_char=idx,
                    end_char=end_char,
                    start_line=start_line,
                    end_line=end_line,
                    text=full_text[idx:end_char]
                )
        
        return None


class StatementProvenance(BaseModel):
    """
    Links a single summary statement to its supporting source spans.
    Includes confidence scoring for this specific statement.
    """
    statement_index: int = Field(..., description="Index of statement in summary (0-indexed)")
    statement_text: str = Field(..., description="The summary statement text")
    source_spans: List[SourceSpan] = Field(
        default_factory=list, 
        description="Source spans that support this statement"
    )
    source_quotes: List[str] = Field(
        default_factory=list,
        description="Original quotes cited by the summarizer (may not have exact span matches)"
    )
    confidence_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Overall confidence score for this statement (0.0-1.0)"
    )
    confidence_factors: Dict[str, float] = Field(
        default_factory=dict, 
        description="Breakdown of confidence by factor (e.g., 'source_match': 0.9, 'entity_coverage': 0.85)"
    )
    has_source_backing: bool = Field(
        default=False,
        description="Whether this statement has at least one verified source span"
    )
    
    def calculate_confidence(
        self,
        source_match_weight: float = 0.4,
        entity_coverage_weight: float = 0.3,
        validation_weight: float = 0.3
    ) -> float:
        """
        Calculate weighted confidence score from factors.
        Updates the confidence_score field and returns it.
        """
        if not self.confidence_factors:
            return 0.0
        
        weights = {
            'source_match': source_match_weight,
            'entity_coverage': entity_coverage_weight,
            'validation_score': validation_weight,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for factor, score in self.confidence_factors.items():
            weight = weights.get(factor, 0.1)  # Default weight for unknown factors
            weighted_sum += score * weight
            total_weight += weight
        
        self.confidence_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        return self.confidence_score


class ProvenanceReport(BaseModel):
    """
    Complete provenance report for a summary.
    Aggregates all statement-to-source mappings with overall metrics.
    """
    mappings: List[StatementProvenance] = Field(
        default_factory=list, 
        description="All statement-to-source provenance mappings"
    )
    overall_confidence: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Weighted average confidence across all statements"
    )
    validation_coverage: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Percentage of statements with verified source backing"
    )
    total_statements: int = Field(default=0, description="Total number of statements in summary")
    backed_statements: int = Field(default=0, description="Number of statements with source backing")
    
    def calculate_metrics(self) -> None:
        """
        Calculate overall metrics from individual statement mappings.
        Updates overall_confidence, validation_coverage, and counts.
        """
        if not self.mappings:
            self.overall_confidence = 0.0
            self.validation_coverage = 0.0
            self.total_statements = 0
            self.backed_statements = 0
            return
        
        self.total_statements = len(self.mappings)
        self.backed_statements = sum(1 for m in self.mappings if m.has_source_backing)
        
        # Calculate overall confidence as weighted average
        confidence_sum = sum(m.confidence_score for m in self.mappings)
        self.overall_confidence = confidence_sum / self.total_statements
        
        # Calculate validation coverage
        self.validation_coverage = self.backed_statements / self.total_statements
    
    def get_low_confidence_statements(self, threshold: float = 0.5) -> List[StatementProvenance]:
        """Get all statements with confidence below the threshold."""
        return [m for m in self.mappings if m.confidence_score < threshold]
    
    def get_unverified_statements(self) -> List[StatementProvenance]:
        """Get all statements without source backing."""
        return [m for m in self.mappings if not m.has_source_backing]
    
    def to_sentence_mapping_format(self) -> List[Dict]:
        """
        Convert to the frontend's expected sentenceMapping format.
        Returns a list of {summary: int, original: List[int]} for line-based mapping.
        """
        result = []
        for mapping in self.mappings:
            original_lines = set()
            for span in mapping.source_spans:
                original_lines.update(range(span.start_line - 1, span.end_line))  # 0-indexed for frontend
            
            result.append({
                "summary": mapping.statement_index,
                "original": sorted(list(original_lines))
            })
        
        return result


class SummaryWithProvenance(BaseModel):
    """
    A summary with full provenance information.
    Used as the internal representation during processing.
    """
    plain_language_report: str = Field(..., description="The complete plain-language summary text")
    statements: List[str] = Field(default_factory=list, description="Individual statements parsed from the summary")
    provenance: ProvenanceReport = Field(default_factory=ProvenanceReport, description="Provenance mappings for each statement")
    
    @classmethod
    def from_text(cls, text: str) -> "SummaryWithProvenance":
        """
        Create a SummaryWithProvenance from plain text.
        Splits text into statements (sentences/paragraphs).
        """
        # Split into paragraphs first, then sentences within paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        statements = []
        for para in paragraphs:
            # For short paragraphs, treat as single statement
            if len(para) < 200:
                statements.append(para)
            else:
                # Split longer paragraphs by sentence-ending punctuation
                import re
                sentences = re.split(r'(?<=[.!?])\s+', para)
                statements.extend([s.strip() for s in sentences if s.strip()])
        
        # Create provenance mappings for each statement
        mappings = [
            StatementProvenance(
                statement_index=i,
                statement_text=stmt,
                source_spans=[],
                confidence_score=0.0,
                has_source_backing=False
            )
            for i, stmt in enumerate(statements)
        ]
        
        provenance = ProvenanceReport(mappings=mappings)
        provenance.calculate_metrics()
        
        return cls(
            plain_language_report=text,
            statements=statements,
            provenance=provenance
        )
