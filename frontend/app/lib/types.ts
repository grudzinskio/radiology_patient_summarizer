// TypeScript types matching backend Pydantic schemas

export interface SummarizeRequest {
  medical_report: string;
  patient_id?: string | null;
  report_id?: string | null;
}

export interface SentenceMapping {
  summary: number;
  original: number[];
  confidence: number;
}

export interface ValidationCheckResult {
  name: string;
  status: "pass" | "fail" | "warning";
  description: string;
}

export interface EntityExtractionResult {
  findings: string[];
  anatomy: string[];
  measurements: string[];
  uncertainty: string[];
}

export interface SummarizeResponse {
  summary_id: string;
  plain_language_report: string;
  status: "draft" | "approved";
  validation_passed: boolean;
  validation_notes: string[];
  validation_checks: ValidationCheckResult[];
  sentence_mapping: SentenceMapping[];
  overall_confidence: number;
  provenance?: any | null;
  extracted_entities?: EntityExtractionResult | null;
}

export interface GetSummaryResponse extends SummarizeResponse {
  medical_report: string;
  patient_id?: string | null;
  report_id?: string | null;
}

export interface SummaryListItem {
  id: string;
  patient_id: string;
  patient_name: string;
  date: string;
  status: "pending" | "approved" | "rejected";
}

export interface SummaryListResponse {
  summaries: SummaryListItem[];
}

export interface ApproveRequest {
  radiologist_notes?: string | null;
}

export interface ApproveResponse {
  summary_id: string;
  status: "approved";
}

export interface ImproveRequest {
  plain_language_report: string;
  radiologist_notes?: string | null;
}

export interface ImproveResponse {
  summary_id: string;
  plain_language_report: string;
  status: "draft" | "approved";
}

export interface DownloadResponse {
  summary_id: string;
  file_name: string;
  plain_language_report: string;
}
