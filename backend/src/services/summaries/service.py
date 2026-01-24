from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from services.summaries.plain_language_report_agent import PlainLanguageReportAgent


@dataclass
class SummaryRecord:
    summary_id: str
    plain_language_report: str
    status: str
    patient_id: str | None = None
    report_id: str | None = None
    radiologist_notes: str | None = None


_SUMMARY_STORE: dict[str, SummaryRecord] = {}


def summarize_report(*, medical_report: str, patient_id: str | None = None, report_id: str | None = None) -> dict[str, Any]:
    agent = PlainLanguageReportAgent()
    state = agent.run(medical_report, patient_id=patient_id, report_id=report_id)

    plain_language_report = state.get("plain_language_report") or ""
    status = "approved" if _validation_passed(state) else "draft"

    summary_id = str(uuid4())
    _SUMMARY_STORE[summary_id] = SummaryRecord(
        summary_id=summary_id,
        plain_language_report=plain_language_report,
        status=status,
        patient_id=patient_id,
        report_id=report_id,
    )

    return {
        "summary_id": summary_id,
        "plain_language_report": plain_language_report,
        "status": status,
    }


def approve_summary(*, summary_id: str, radiologist_notes: str | None = None) -> dict[str, Any]:
    record = _get_record(summary_id)
    record.status = "approved"
    record.radiologist_notes = radiologist_notes
    return {"summary_id": record.summary_id, "status": "approved"}


def improve_summary(*, summary_id: str, plain_language_report: str, radiologist_notes: str | None = None) -> dict[str, Any]:
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
    record = _get_record(summary_id)
    return {
        "summary_id": record.summary_id,
        "file_name": f"{record.summary_id}.txt",
        "plain_language_report": record.plain_language_report,
    }


def _get_record(summary_id: str) -> SummaryRecord:
    record = _SUMMARY_STORE.get(summary_id)
    if record is None:
        raise KeyError(f"Summary '{summary_id}' not found.")
    return record


def _validation_passed(state: dict[str, Any]) -> bool:
    if isinstance(state.get("validation_passed"), bool):
        return state["validation_passed"]

    validation_report = state.get("validation_pipeline_result")
    overall_passed = getattr(validation_report, "overall_passed", None)
    if isinstance(overall_passed, bool):
        return overall_passed

    return False
