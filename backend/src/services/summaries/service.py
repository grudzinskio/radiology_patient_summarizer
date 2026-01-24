from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

from services.summaries.plain_language_report_agent import PlainLanguageReportAgent
from schemas.provenance import ProvenanceReport
from schemas.validation import EntityExtractionResult
import logging

logger = logging.getLogger(__name__)



@dataclass
class SummaryRecord:
    """In-memory storage for summary records."""
    summary_id: str
    plain_language_report: str
    status: str
    medical_report: str  # Store original report
    patient_id: str | None = None
    report_id: str | None = None
    radiologist_notes: str | None = None
    provenance_report: Optional[ProvenanceReport] = None
    extracted_entities: Optional[EntityExtractionResult] = None
    overall_confidence: float = 0.0
    validation_checks: list[dict[str, Any]] = field(default_factory=list)  # Store validation checks
    sentence_mapping: list[dict[str, Any]] = field(default_factory=list)  # Store sentence mapping
    validation_passed: bool = False


_SUMMARY_STORE: dict[str, SummaryRecord] = {}


def summarize_report(
    *, 
    medical_report: str, 
    patient_id: str | None = None, 
    report_id: str | None = None
) -> dict[str, Any]:
    """
    Generate a patient-friendly summary of a medical report with provenance tracking.
    
    Returns a dictionary containing the summary, validation results, and explainability data.
    """
    logger.info(f"Received request to summarize report (length: {len(medical_report)} chars)")
    
    logger.info("Initializing PlainLanguageReportAgent...")
    agent = PlainLanguageReportAgent(enable_provenance=True)
    
    logger.info("Running agent...")
    state = agent.run(medical_report, patient_id=patient_id, report_id=report_id)
    logger.info("Agent execution completed.")


    plain_language_report = state.get("plain_language_report") or ""
    validation_passed = _validation_passed(state)
    status = "approved" if validation_passed else "draft"
    validation_reasons = state.get("validation_reasons") or []
    
    # Extract provenance and confidence
    provenance_report = state.get("provenance_report")
    overall_confidence = state.get("overall_confidence", 0.0)
    extracted_entities = state.get("extracted_entities")
    
    # Build sentence mapping for frontend
    sentence_mapping = _build_sentence_mapping(state)
    
    # Build validation check results
    validation_checks = _build_validation_checks(state)

    summary_id = str(uuid4())
    _SUMMARY_STORE[summary_id] = SummaryRecord(
        summary_id=summary_id,
        plain_language_report=plain_language_report,
        status=status,
        medical_report=medical_report,  # Store original report
        patient_id=patient_id,
        report_id=report_id,
        provenance_report=provenance_report,
        extracted_entities=extracted_entities,
        overall_confidence=overall_confidence,
        validation_checks=validation_checks,  # Store validation checks
        sentence_mapping=sentence_mapping,  # Store sentence mapping
        validation_passed=validation_passed,  # Store validation status
    )

    return {
        "summary_id": summary_id,
        "plain_language_report": plain_language_report,
        "status": status,
        "validation_passed": validation_passed,
        "validation_notes": validation_reasons,
        "validation_checks": validation_checks,
        "sentence_mapping": sentence_mapping,
        "overall_confidence": overall_confidence,
        "provenance": provenance_report,
        "extracted_entities": extracted_entities,
    }


def _build_sentence_mapping(state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build sentence mapping from provenance report for frontend highlight-on-hover.
    
    Returns a list of mappings: {summary: int, original: List[int], confidence: float}
    """
    provenance_report = state.get("provenance_report")
    if not provenance_report:
        return []
    
    # Use the ProvenanceReport's built-in conversion method if available
    if hasattr(provenance_report, 'to_sentence_mapping_format'):
        base_mappings = provenance_report.to_sentence_mapping_format()
    else:
        base_mappings = []
    
    # Enhance with confidence scores
    result = []
    for i, mapping in enumerate(base_mappings):
        confidence = 0.0
        if provenance_report.mappings and i < len(provenance_report.mappings):
            confidence = provenance_report.mappings[i].confidence_score
        
        result.append({
            "summary": mapping.get("summary", i),
            "original": mapping.get("original", []),
            "confidence": round(confidence, 3),
        })
    
    return result


def _build_validation_checks(state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build detailed validation check results from the validation pipeline result.
    
    Returns a list of check results: {name: str, status: str, description: str}
    """
    validation_report = state.get("validation_pipeline_result")
    if not validation_report:
        return []
    
    checks = []
    component_results = getattr(validation_report, "component_results", [])
    
    for result in component_results:
        component_name = getattr(result, "component_name", "Unknown")
        passed = getattr(result, "passed", False)
        error_messages = getattr(result, "error_messages", [])
        metadata = getattr(result, "metadata", {})
        
        # Determine status
        status = "pass" if passed else "fail"
        
        # Build description
        if passed:
            # Try to extract a meaningful description from metadata
            if component_name == "ReadabilityCheck" and "flesch_kincaid_grade" in metadata:
                description = f"Grade level: {metadata['flesch_kincaid_grade']}"
            elif component_name == "FidelityCheck":
                found = metadata.get("found_entities", 0)
                total = metadata.get("total_entities", 0)
                description = f"Found {found}/{total} entities"
            elif component_name == "ProvenanceCheck":
                coverage = metadata.get("validation_coverage", 0)
                confidence = metadata.get("overall_confidence", 0)
                description = f"Coverage: {coverage*100:.0f}%, Confidence: {confidence*100:.0f}%"
            else:
                description = "Check passed"
        else:
            description = "; ".join(error_messages[:2]) if error_messages else "Check failed"
        
        checks.append({
            "name": component_name.replace("Check", ""),
            "status": status,
            "description": description,
        })
    
    return checks


def approve_summary(*, summary_id: str, radiologist_notes: str | None = None) -> dict[str, Any]:
    """Approve a summary for release to the patient."""
    record = _get_record(summary_id)
    record.status = "approved"
    record.radiologist_notes = radiologist_notes
    return {"summary_id": record.summary_id, "status": "approved"}


def improve_summary(
    *, 
    summary_id: str, 
    plain_language_report: str, 
    radiologist_notes: str | None = None
) -> dict[str, Any]:
    """Submit an improved version of a summary."""
    record = _get_record(summary_id)
    record.plain_language_report = plain_language_report
    record.radiologist_notes = radiologist_notes
    record.status = "draft"
    return {
        "summary_id": record.summary_id,
        "plain_language_report": record.plain_language_report,
        "status": record.status,
    }


def download_summary(*, summary_id: str) -> dict[str, Any]:
    """Download a summary as a text file."""
    record = _get_record(summary_id)
    return {
        "summary_id": record.summary_id,
        "file_name": f"{record.summary_id}.txt",
        "plain_language_report": record.plain_language_report,
    }


def get_summary(*, summary_id: str) -> dict[str, Any]:
    """Retrieve a full summary record by ID."""
    record = _get_record(summary_id)
    
    return {
        "summary_id": record.summary_id,
        "plain_language_report": record.plain_language_report,
        "medical_report": record.medical_report,
        "status": record.status,
        "validation_passed": record.validation_passed,
        "validation_notes": [],
        "validation_checks": record.validation_checks,
        "sentence_mapping": record.sentence_mapping,
        "overall_confidence": record.overall_confidence,
        "provenance": record.provenance_report,
        "extracted_entities": record.extracted_entities,
        "patient_id": record.patient_id,
        "report_id": record.report_id,
    }


def list_summaries() -> list[dict[str, Any]]:
    """List all summary records with metadata for the sidebar."""
    from datetime import datetime
    
    summaries = []
    for record in _SUMMARY_STORE.values():
        # Generate a date from summary_id (using first 8 chars as timestamp approximation)
        # In production, you'd store created_at timestamp
        summaries.append({
            "id": record.summary_id,
            "patient_id": record.patient_id or "Unknown",
            "patient_name": f"Patient {record.patient_id[-4:]}" if record.patient_id else "Unknown",
            "date": datetime.now().strftime("%Y-%m-%d"),  # Placeholder - should store actual date
            "status": "approved" if record.status == "approved" else "pending",
        })
    
    # Sort by summary_id (newest first, assuming UUIDs)
    summaries.sort(key=lambda x: x["id"], reverse=True)
    return summaries


def _get_record(summary_id: str) -> SummaryRecord:
    """Retrieve a summary record by ID."""
    record = _SUMMARY_STORE.get(summary_id)
    if record is None:
        raise KeyError(f"Summary '{summary_id}' not found.")
    return record


def _validation_passed(state: dict[str, Any]) -> bool:
    """Check if validation passed from the agent state."""
    if isinstance(state.get("validation_passed"), bool):
        return state["validation_passed"]

    validation_report = state.get("validation_pipeline_result")
    overall_passed = getattr(validation_report, "overall_passed", None)
    if isinstance(overall_passed, bool):
        return overall_passed

    return False

