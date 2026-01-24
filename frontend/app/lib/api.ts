// API client for backend communication

import type {
  SummarizeRequest,
  SummarizeResponse,
  GetSummaryResponse,
  SummaryListResponse,
  ApproveRequest,
  ApproveResponse,
  ImproveRequest,
  ImproveResponse,
  DownloadResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `API request failed: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // If response is not JSON, use status text
      }
      throw new ApiError(errorMessage, response.status, response);
    }

    return response.json();
  } catch (error) {
    // Handle network errors (backend not running, CORS issues, etc.)
    if (error instanceof ApiError) {
      throw error;
    }
    // Network error or other fetch errors
    throw new ApiError(
      `Network error: ${error instanceof Error ? error.message : "Unable to connect to backend"}`,
      0,
      undefined
    );
  }
}

export const api = {
  /**
   * Generate a patient-friendly summary of a medical report.
   */
  async summarizeReport(
    medicalReport: string,
    patientId?: string | null,
    reportId?: string | null
  ): Promise<SummarizeResponse> {
    const payload: SummarizeRequest = {
      medical_report: medicalReport,
      patient_id: patientId || null,
      report_id: reportId || null,
    };
    return fetchApi<SummarizeResponse>("/summaries/summarize", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Get a single summary by ID.
   */
  async getSummary(summaryId: string): Promise<GetSummaryResponse> {
    return fetchApi<GetSummaryResponse>(`/summaries/${summaryId}`);
  },

  /**
   * List all summaries with metadata.
   */
  async listSummaries(): Promise<SummaryListResponse> {
    return fetchApi<SummaryListResponse>("/summaries");
  },

  /**
   * Approve a summary for release.
   */
  async approveSummary(
    summaryId: string,
    radiologistNotes?: string | null
  ): Promise<ApproveResponse> {
    const payload: ApproveRequest = {
      radiologist_notes: radiologistNotes || null,
    };
    return fetchApi<ApproveResponse>(`/summaries/${summaryId}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Submit an improved version of a summary.
   */
  async improveSummary(
    summaryId: string,
    plainLanguageReport: string,
    radiologistNotes?: string | null
  ): Promise<ImproveResponse> {
    const payload: ImproveRequest = {
      plain_language_report: plainLanguageReport,
      radiologist_notes: radiologistNotes || null,
    };
    return fetchApi<ImproveResponse>(`/summaries/${summaryId}/improve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Download a summary as text.
   */
  async downloadSummary(summaryId: string): Promise<DownloadResponse> {
    return fetchApi<DownloadResponse>(`/summaries/${summaryId}/download`);
  },
};

export { ApiError };
