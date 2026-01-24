from typing import Literal, Optional, List, Dict, Any

from pydantic import BaseModel, Field

from schemas.provenance import ProvenanceReport
from schemas.validation import EntityExtractionResult


class SummarizeRequest(BaseModel):
    """Request to generate a patient-friendly summary of a medical report."""
    medical_report: str = Field(..., description="Raw clinical or radiology report.")
    patient_id: str | None = Field(
        default=None, description="Optional patient identifier."
    )
    report_id: str | None = Field(
        default=None, description="Optional source report identifier."
    )


class SentenceMapping(BaseModel):
    """Maps a summary sentence to its source lines in the original report."""
    summary: int = Field(..., description="Index of the sentence in the summary (0-indexed)")
    original: List[int] = Field(default_factory=list, description="Line indices in the original report (0-indexed)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score for this sentence")


class ValidationCheckResult(BaseModel):
    """Result of a single validation check."""
    name: str = Field(..., description="Name of the validation check")
    status: Literal["pass", "fail", "warning"] = Field(..., description="Status of the check")
    description: str = Field(default="", description="Description or details about the check result")


class SummarizeResponse(BaseModel):
    """Response containing the patient-friendly summary with explainability data."""
    
    # Core fields
    summary_id: str
    plain_language_report: str
    status: Literal["draft", "approved"]
    
    # Validation
    validation_passed: bool = Field(default=True, description="Whether all validation checks passed.")
    validation_notes: list[str] = Field(default_factory=list, description="List of validation warnings or errors.")
    validation_checks: list[ValidationCheckResult] = Field(
        default_factory=list, 
        description="Detailed results of each validation check."
    )
    
    # Explainability - Provenance (NEW)
    sentence_mapping: list[SentenceMapping] = Field(
        default_factory=list,
        description="Maps each summary sentence to its source lines for highlight-on-hover."
    )
    overall_confidence: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Overall confidence score for the summary (0.0-1.0)."
    )
    provenance: Optional[ProvenanceReport] = Field(
        default=None,
        description="Full provenance report with detailed statement-to-source mappings."
    )
    
    # Extracted data (NEW)
    extracted_entities: Optional[EntityExtractionResult] = Field(
        default=None,
        description="Medical entities extracted from the original report."
    )


class ApproveRequest(BaseModel):
    """Request to approve a summary for release."""
    radiologist_notes: str | None = Field(
        default=None, description="Optional approval notes."
    )


class ApproveResponse(BaseModel):
    """Response after approving a summary."""
    summary_id: str
    status: Literal["approved"]


class ImproveRequest(BaseModel):
    """Request to submit an improved version of a summary."""
    plain_language_report: str = Field(
        ..., description="Revised plain-language report."
    )
    radiologist_notes: str | None = Field(
        default=None, description="Optional improvement notes."
    )


class ImproveResponse(BaseModel):
    """Response after improving a summary."""
    summary_id: str
    plain_language_report: str
    status: Literal["draft", "approved"]


class DownloadResponse(BaseModel):
    """Response for downloading a summary."""
    summary_id: str
    file_name: str
    plain_language_report: str

