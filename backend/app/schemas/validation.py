from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field


class EntityExtractionResult(BaseModel):
    """
    Structure matching the entity extraction output format.
    Contains all medical facts extracted from the original report.
    """
    findings: List[str] = Field(default_factory=list, description="Medical findings (e.g., '5mm nodule', 'mild opacification')")
    anatomy: List[str] = Field(default_factory=list, description="Anatomical locations (e.g., 'right lower lobe', 'pleural space')")
    measurements: List[str] = Field(default_factory=list, description="Measurements (e.g., '5mm', '2.3cm')")
    uncertainty: List[str] = Field(default_factory=list, description="Uncertainty phrases (e.g., 'cannot rule out', 'suggestive of')")


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
