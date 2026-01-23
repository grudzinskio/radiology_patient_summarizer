from fastapi import APIRouter

from backend.services import summaries_service
from backend.app.schemas.summaries import (
    ApproveRequest,
    ApproveResponse,
    DownloadResponse,
    ImproveRequest,
    ImproveResponse,
    SummarizeRequest,
    SummarizeResponse,
)


router = APIRouter(prefix="/summaries", tags=["summaries"])


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
