from fastapi import APIRouter

from services.summaries import service as summaries_service
from schemas.summaries import (
    ApproveRequest,
    ApproveResponse,
    DownloadResponse,
    ImproveRequest,
    ImproveResponse,
    SummarizeRequest,
    SummarizeResponse,
    SummaryListResponse,
    GetSummaryResponse,
)
from fastapi import HTTPException


router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("", response_model=SummaryListResponse)
def list_summaries() -> SummaryListResponse:
    """List all summaries with metadata for the sidebar."""
    summaries = summaries_service.list_summaries()
    return SummaryListResponse(summaries=summaries)


@router.get("/{summary_id}", response_model=GetSummaryResponse)
def get_summary(summary_id: str) -> GetSummaryResponse:
    """Get a single summary by ID."""
    try:
        summary_data = summaries_service.get_summary(summary_id=summary_id)
        return GetSummaryResponse(**summary_data)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/summarize", response_model=SummarizeResponse)
def summarize_report(payload: SummarizeRequest) -> SummarizeResponse:
    return summaries_service.summarize_report(
        medical_report=payload.medical_report,
        patient_id=payload.patient_id,
        report_id=payload.report_id,
    )


@router.post("/{summary_id}/approve", response_model=ApproveResponse)
def approve_summary(summary_id: str, payload: ApproveRequest) -> ApproveResponse:
    return summaries_service.approve_summary(
        summary_id=summary_id,
        radiologist_notes=payload.radiologist_notes,
    )


@router.post("/{summary_id}/improve", response_model=ImproveResponse)
def improve_summary(summary_id: str, payload: ImproveRequest) -> ImproveResponse:
    return summaries_service.improve_summary(
        summary_id=summary_id,
        plain_language_report=payload.plain_language_report,
        radiologist_notes=payload.radiologist_notes,
    )


@router.get("/{summary_id}/download", response_model=DownloadResponse)
def download_summary(summary_id: str) -> DownloadResponse:
    return summaries_service.download_summary(summary_id=summary_id)
