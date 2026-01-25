from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field


class ClinicalEntity(BaseModel):
    """Structured representation of a clinical entity with context."""
    original_text: str = Field(..., description="The original text of the entity")
    canonical_name: str = Field(..., description="The canonical name of the entity")
    definition: Optional[str] = Field(default=None, description="The definition of the entity")
    semantic_types: list[str] = Field(default_factory=list, description="The semantic types of the entity")
    confidence: float = Field(..., description="The confidence score of the entity")
    
    # MedSpaCy context attributes
    section: Optional[str] = Field(default=None, description="The section of the entity")
    is_negated: bool = Field(..., description="Whether the entity is negated")
    is_uncertain: bool = Field(..., description="Whether the entity is uncertain")
    is_family: bool = Field(..., description="Whether the entity is a family history")
    is_historical: bool = Field(..., description="Whether the entity is historical")

    # Position in text
    start_char: int = Field(..., description="The start character of the entity in the text")
    end_char: int = Field(..., description="The end character of the entity in the text")
    
    # MeSH identifiers
    mesh_id: str = Field(..., description="The MeSH ID of the entity")
    aliases: list[str] = Field(default_factory=list, description="The aliases of the entity")


class EntityExtractionResult(BaseModel):
    """
    Structure matching the entity extraction output format.
    Contains all medical facts extracted from the original report.
    """
    entities: List[ClinicalEntity] = Field(
        default_factory=list,
        description="Raw entities extracted from the report",
    )


class ValidationInput(BaseModel):
    """
    Input structure for validation pipeline.
    Contains all necessary data to validate a summary.
    """
    original_report: str = Field(..., description="Raw radiology/medical report text")
    extracted_entities: EntityExtractionResult = Field(..., description="Structured entities extracted from the original report")
    draft_summary: str = Field(..., description="The patient-friendly summary to validate")
    retrieved_definitions: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Optional dictionary of medical term definitions from RAG pipeline"
    )


class ValidationResult(BaseModel):
    """
    Result from a single validation component.
    """
    component_name: str = Field(..., description="Name of the validation component")
    passed: bool = Field(..., description="Whether this check passed")
    error_messages: List[str] = Field(default_factory=list, description="Detailed error messages if validation failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (e.g., scores, counts)")


class ValidationReport(BaseModel):
    """
    Aggregated results from all validation components.
    """
    overall_passed: bool = Field(..., description="Whether all validation checks passed")
    component_results: List[ValidationResult] = Field(default_factory=list, description="Results from each validation component")
    summary: str = Field(..., description="Human-readable summary of validation results")
    
    def get_failed_components(self) -> List[ValidationResult]:
        """Get all failed validation components."""
        return [result for result in self.component_results if not result.passed]
    
    def get_all_errors(self) -> List[str]:
        """Get all error messages from failed components."""
        errors = []
        for result in self.get_failed_components():
            errors.extend(result.error_messages)
        return errors
