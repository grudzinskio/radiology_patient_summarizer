from typing import Literal

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    medical_report: str = Field(..., description="Raw clinical or radiology report.")
    patient_id: str | None = Field(
        default=None, description="Optional patient identifier."
    )
    report_id: str | None = Field(
        default=None, description="Optional source report identifier."
    )


class SummarizeResponse(BaseModel):
    summary_id: str
    plain_language_report: str
    status: Literal["draft", "approved"]


class ApproveRequest(BaseModel):
    radiologist_notes: str | None = Field(
        default=None, description="Optional approval notes."
    )


class ApproveResponse(BaseModel):
    summary_id: str
    status: Literal["approved"]


class ImproveRequest(BaseModel):
    plain_language_report: str = Field(
        ..., description="Revised plain-language report."
    )
    radiologist_notes: str | None = Field(
        default=None, description="Optional improvement notes."
    )


class ImproveResponse(BaseModel):
    summary_id: str
    plain_language_report: str
    status: Literal["draft", "approved"]


class DownloadResponse(BaseModel):
    summary_id: str
    file_name: str
    plain_language_report: str
