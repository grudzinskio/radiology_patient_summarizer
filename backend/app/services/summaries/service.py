"""
Service layer for summary generation with validation and self-correction.
"""
import uuid
from typing import Optional
import logging

from backend.app.schemas.summaries import (
    SummarizeRequest,
    SummarizeResponse,
    ApproveRequest,
    ApproveResponse,
    ImproveRequest,
    ImproveResponse,
    DownloadResponse,
)
from backend.app.schemas.validation import EntityExtractionResult
from backend.app.services.summaries.validation.validation_pipeline import ValidationPipeline
from backend.app.services.summaries.validation.self_correction_loop import SelfCorrectionLoop
from backend.app.services.summaries.validation.pipeline_components.fidelity_component import FidelityComponent
from backend.app.services.summaries.validation.pipeline_components.hallucination_component import HallucinationComponent
from backend.app.services.summaries.validation.pipeline_components.readability_component import ReadabilityComponent
from backend.app.services.summaries.validation.pipeline_components.safety_component import SafetyComponent
from backend.app.services.summaries.validation.config import (
    ENABLE_FIDELITY_CHECK,
    ENABLE_HALLUCINATION_CHECK,
    ENABLE_READABILITY_CHECK,
    ENABLE_SAFETY_CHECK,
)
from backend.app.utils.clients.llm_clients import OpenAIClient

logger = logging.getLogger(__name__)

# In-memory storage for summaries (replace with database in production)
_summaries_store: dict[str, dict] = {}


def _create_validation_pipeline() -> ValidationPipeline:
    """
    Create and configure the validation pipeline with all enabled components.
    """
    pipeline = ValidationPipeline()
    
    if ENABLE_FIDELITY_CHECK:
        pipeline.add_component(FidelityComponent())
    
    if ENABLE_HALLUCINATION_CHECK:
        pipeline.add_component(HallucinationComponent())
    
    if ENABLE_READABILITY_CHECK:
        pipeline.add_component(ReadabilityComponent())
    
    if ENABLE_SAFETY_CHECK:
        pipeline.add_component(SafetyComponent())
    
    return pipeline


def _extract_entities_from_report(medical_report: str) -> EntityExtractionResult:
    """
    Extract entities from the medical report.
    This is a placeholder - should be replaced with actual entity extraction pipeline.
    """
    # TODO: Replace with actual entity extraction pipeline
    # For now, using LLM to extract entities
    llm_client = OpenAIClient()
    
    prompt = f"""Extract all medical findings, anatomy, and measurements from the following radiology report.
Output as JSON with the following structure:
{{
    "findings": ["list of medical findings"],
    "anatomy": ["list of anatomical locations"],
    "measurements": ["list of measurements"],
    "uncertainty": ["list of uncertainty phrases"]
}}

Report:
{medical_report}

Return only valid JSON, no additional text."""

    try:
        messages = [
            {"role": "system", "content": "You are a medical entity extraction system. Extract entities and return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.generate(messages, temperature=0.1)
        
        # Clean response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        import json
        data = json.loads(response)
        return EntityExtractionResult(
            findings=data.get("findings", []),
            anatomy=data.get("anatomy", []),
            measurements=data.get("measurements", []),
            uncertainty=data.get("uncertainty", [])
        )
    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        # Return empty entities if extraction fails
        return EntityExtractionResult(
            findings=[],
            anatomy=[],
            measurements=[],
            uncertainty=[]
        )


def _generate_initial_summary(
    medical_report: str,
    extracted_entities: EntityExtractionResult,
    retrieved_definitions: Optional[dict] = None
) -> str:
    """
    Generate initial patient-friendly summary.
    This is a placeholder - should be replaced with actual summarizer agent.
    """
    # TODO: Replace with actual summarizer agent
    llm_client = OpenAIClient()
    
    prompt_parts = [
        "You are an empathetic medical translator. Translate the following radiology report into patient-friendly language.",
        "",
        "REQUIREMENTS:",
        "1. Use 6th-8th grade reading level (simple, clear language).",
        "2. Include all findings, anatomy, and measurements from the extracted entities list.",
        "3. Do NOT give medical advice or recommendations.",
        "4. Do NOT use alarmist language or emergency phrases.",
        "5. Be empathetic and reassuring in tone.",
        "",
        "ORIGINAL REPORT:",
        medical_report,
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
    
    prompt_parts.append("")
    prompt_parts.append("Generate a patient-friendly summary:")
    
    prompt = "\n".join(prompt_parts)
    
    messages = [
        {"role": "system", "content": "You are an empathetic medical translator."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        summary = llm_client.generate(messages, temperature=0.3)
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating summary. Please try again."


def summarize_report(
    medical_report: str,
    patient_id: Optional[str] = None,
    report_id: Optional[str] = None
) -> SummarizeResponse:
    """
    Generate a validated patient-friendly summary from a medical report.
    
    This function:
    1. Extracts entities from the report
    2. Generates an initial summary
    3. Validates the summary
    4. Automatically refines if validation fails
    5. Returns the final validated summary
    """
    # Generate summary ID
    summary_id = str(uuid.uuid4())
    
    # Step 1: Extract entities
    logger.info("Extracting entities from report...")
    extracted_entities = _extract_entities_from_report(medical_report)
    
    # Step 2: Generate initial summary
    # TODO: Integrate with RAG pipeline for retrieved_definitions
    retrieved_definitions = None
    logger.info("Generating initial summary...")
    initial_summary = _generate_initial_summary(
        medical_report=medical_report,
        extracted_entities=extracted_entities,
        retrieved_definitions=retrieved_definitions
    )
    
    # Step 3 & 4: Validate and refine
    logger.info("Validating and refining summary...")
    validation_pipeline = _create_validation_pipeline()
    self_correction_loop = SelfCorrectionLoop(
        validation_pipeline=validation_pipeline,
        llm_client=OpenAIClient()
    )
    
    final_summary, validation_report = self_correction_loop.validate_and_refine(
        original_report=medical_report,
        extracted_entities=extracted_entities,
        draft_summary=initial_summary,
        retrieved_definitions=retrieved_definitions
    )
    
    # Store summary
    _summaries_store[summary_id] = {
        "summary_id": summary_id,
        "patient_id": patient_id,
        "report_id": report_id,
        "original_report": medical_report,
        "plain_language_report": final_summary,
        "status": "draft",
        "validation_report": validation_report.model_dump() if hasattr(validation_report, 'model_dump') else (validation_report.dict() if hasattr(validation_report, 'dict') else None),
        "extracted_entities": extracted_entities.model_dump() if hasattr(extracted_entities, 'model_dump') else (extracted_entities.dict() if hasattr(extracted_entities, 'dict') else None),
    }
    
    logger.info(f"Summary generated: {summary_id} (validation: {'PASSED' if validation_report.overall_passed else 'FAILED'})")
    
    return SummarizeResponse(
        summary_id=summary_id,
        plain_language_report=final_summary,
        status="draft"
    )


def approve_summary(
    summary_id: str,
    radiologist_notes: Optional[str] = None
) -> ApproveResponse:
    """
    Approve a summary (mark as approved by radiologist).
    """
    if summary_id not in _summaries_store:
        raise ValueError(f"Summary {summary_id} not found")
    
    _summaries_store[summary_id]["status"] = "approved"
    if radiologist_notes:
        _summaries_store[summary_id]["radiologist_notes"] = radiologist_notes
    
    return ApproveResponse(
        summary_id=summary_id,
        status="approved"
    )


def improve_summary(
    summary_id: str,
    plain_language_report: str,
    radiologist_notes: Optional[str] = None
) -> ImproveResponse:
    """
    Improve/update a summary with radiologist feedback.
    """
    if summary_id not in _summaries_store:
        raise ValueError(f"Summary {summary_id} not found")
    
    # Update the summary
    _summaries_store[summary_id]["plain_language_report"] = plain_language_report
    _summaries_store[summary_id]["status"] = "draft"
    if radiologist_notes:
        _summaries_store[summary_id]["radiologist_notes"] = radiologist_notes
    
    return ImproveResponse(
        summary_id=summary_id,
        plain_language_report=plain_language_report,
        status="draft"
    )


def download_summary(summary_id: str) -> DownloadResponse:
    """
    Download a summary as a file.
    """
    if summary_id not in _summaries_store:
        raise ValueError(f"Summary {summary_id} not found")
    
    summary_data = _summaries_store[summary_id]
    
    return DownloadResponse(
        summary_id=summary_id,
        file_name=f"summary_{summary_id}.txt",
        plain_language_report=summary_data["plain_language_report"]
    )
