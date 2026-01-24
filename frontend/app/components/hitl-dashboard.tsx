"use client";

import { useState, useMemo, useEffect } from "react";
import { ChevronLeft, ChevronRight, User, FileText, Check, AlertCircle, Lightbulb, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReportPanel } from "./report-panel";
import { ValidationBadges } from "./validation-badges";
import { ActionButtons } from "./action-buttons";
import { EditPanel } from "./edit-panel";
import { EntityList } from "./entity-list";
import { ReportsSidebar, type ReportListItem } from "./reports-sidebar";
import { SubmitReportForm } from "./submit-report-form";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import type { GetSummaryResponse, SummaryListItem } from "@/lib/types";
import { toast } from "sonner";

type ReviewStatus = "pending" | "approved" | "rejected";

interface ReportData {
  id: string;
  patientId: string;
  patientName: string;
  date: string;
  originalReport: string;
  aiSummary: string;
  entities: {
    findings: string[];
    anatomy: string[];
    measurements: string[];
    uncertainty: string[];
  };
  validationChecks: Array<{
    name: string;
    status: "pass" | "fail" | "warning";
    description: string;
  }>;
  sentenceMapping: Array<{
    summary: number;
    original: number[];
    confidence?: number;
  }>;
}

export function HITLDashboard() {
  const [hoveredSentence, setHoveredSentence] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState("");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [queuePosition] = useState({ current: 3, total: 12 });
  const [status, setStatus] = useState<ReviewStatus>("pending");
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  
  // API state
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [currentReport, setCurrentReport] = useState<ReportData | null>(null);
  const [loadingReports, setLoadingReports] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Function to refresh reports list
  const refreshReports = async (newSummaryId?: string) => {
    try {
      setError(null);
      const response = await api.listSummaries();
      setReports(response.summaries);
      // Select newly created report, or first report if available and none selected
      if (newSummaryId) {
        setSelectedReportId(newSummaryId);
      } else if (response.summaries.length > 0 && !selectedReportId) {
        setSelectedReportId(response.summaries[0].id);
      }
    } catch (err) {
      let message = "Failed to load reports";
      if (err instanceof ApiError) {
        if (err.status === 0) {
          message = "Backend server is not running. Please start the backend server.";
        } else {
          message = err.message;
        }
      }
      setError(message);
    }
  };

  // Fetch reports list on mount
  useEffect(() => {
    const fetchReports = async () => {
      try {
        setLoadingReports(true);
        await refreshReports();
      } catch (err) {
        // Error already handled in refreshReports
      } finally {
        setLoadingReports(false);
      }
    };
    fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch selected report when selection changes
  useEffect(() => {
    if (!selectedReportId) return;

    const fetchReport = async () => {
      try {
        setLoadingReport(true);
        setError(null);
        const response: GetSummaryResponse = await api.getSummary(selectedReportId);
        
        // Map backend response to frontend format
        const mappedReport: ReportData = {
          id: response.summary_id,
          patientId: response.patient_id || "Unknown",
          patientName: response.patient_id ? `Patient ${response.patient_id.slice(-4)}` : "Unknown",
          date: new Date().toISOString().split("T")[0], // Use current date as placeholder
          originalReport: response.medical_report,
          aiSummary: response.plain_language_report,
          entities: response.extracted_entities || {
            findings: [],
            anatomy: [],
            measurements: [],
            uncertainty: [],
          },
          validationChecks: response.validation_checks.map(check => ({
            name: check.name,
            status: check.status === "pass" ? "pass" : check.status === "fail" ? "fail" : "warning",
            description: check.description,
          })),
          sentenceMapping: response.sentence_mapping.map(m => ({
            summary: m.summary,
            original: m.original,
            confidence: m.confidence,
          })),
        };
        
        setCurrentReport(mappedReport);
        setEditedSummary(mappedReport.aiSummary);
      } catch (err) {
        let message = "Failed to load report";
        if (err instanceof ApiError) {
          if (err.status === 0) {
            message = "Backend server is not running";
          } else {
            message = err.message;
          }
        }
        setError(message);
        // Only show toast if we have other reports to show
        if (reports.length > 0) {
          toast.error("Failed to load report", {
            description: message,
          });
        }
      } finally {
        setLoadingReport(false);
      }
    };
    fetchReport();
  }, [selectedReportId, reports.length]);

  const getHighlightedOriginalSentences = (): number[] => {
    if (hoveredSentence === null || !currentReport) return [];
    const mapping = currentReport.sentenceMapping.find(m => m.summary === hoveredSentence);
    return mapping?.original || [];
  };

  const getHighlightedSummarySentences = (): number[] => {
    if (hoveredSentence === null) return [];
    return [hoveredSentence];
  };

  const handleApprove = async () => {
    if (!selectedReportId) return;
    
    try {
      await api.approveSummary(selectedReportId);
      setStatus("approved");
      toast.success("Summary approved successfully");
      // Refresh reports list to update status
      const response = await api.listSummaries();
      setReports(response.summaries);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to approve summary";
      toast.error("Failed to approve summary", {
        description: message,
      });
    }
  };

  const handleEdit = () => {
    if (!currentReport) return;
    setIsEditing(true);
    setEditedSummary(currentReport.aiSummary);
  };

  const handleReject = () => {
    setStatus("rejected");
    toast.info("Summary flagged for review");
  };

  const handleSaveEdit = async () => {
    if (!selectedReportId) return;
    
    try {
      await api.improveSummary(selectedReportId, editedSummary);
      setIsEditing(false);
      toast.success("Summary updated successfully");
      // Refresh current report
      const response = await api.getSummary(selectedReportId);
      const mappedReport: ReportData = {
        id: response.summary_id,
        patientId: response.patient_id || "Unknown",
        patientName: response.patient_id ? `Patient ${response.patient_id.slice(-4)}` : "Unknown",
        date: new Date().toISOString().split("T")[0],
        originalReport: response.medical_report,
        aiSummary: response.plain_language_report,
        entities: response.extracted_entities || {
          findings: [],
          anatomy: [],
          measurements: [],
          uncertainty: [],
        },
        validationChecks: response.validation_checks.map(check => ({
          name: check.name,
          status: check.status === "pass" ? "pass" : check.status === "fail" ? "fail" : "warning",
          description: check.description,
        })),
        sentenceMapping: response.sentence_mapping.map(m => ({
          summary: m.summary,
          original: m.original,
          confidence: m.confidence,
        })),
      };
      setCurrentReport(mappedReport);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to save changes";
      toast.error("Failed to save changes", {
        description: message,
      });
    }
  };

  const handleCancelEdit = () => {
    if (!currentReport) return;
    setIsEditing(false);
    setEditedSummary(currentReport.aiSummary);
  };

  const resetReview = () => {
    setStatus("pending");
    if (currentReport) {
      setEditedSummary(currentReport.aiSummary);
    }
    setIsEditing(false);
  };

  // Loading state
  if (loadingReports) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-muted-foreground">Loading reports...</p>
      </div>
    );
  }

  // Error state - backend not running or connection failed
  if (error && reports.length === 0 && !loadingReports) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background p-8">
        <AlertCircle className="h-8 w-8 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-foreground mb-2">Unable to Connect to Backend</h2>
        <p className="text-muted-foreground mb-2 max-w-md text-center">{error}</p>
        {error.includes("not running") && (
          <p className="text-sm text-muted-foreground mb-4 max-w-md text-center">
            Make sure the backend server is running on <code className="bg-muted px-1 rounded">http://localhost:8000</code>
          </p>
        )}
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  // Status screens
  if (status !== "pending") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background p-8">
        <div className="rounded-lg border border-border bg-card p-8 text-center shadow-sm">
          <div
            className={cn(
              "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full",
              status === "approved" ? "bg-primary/10" : "bg-destructive/10"
            )}
          >
            {status === "approved" ? (
              <Check className="h-8 w-8 text-primary" />
            ) : (
              <AlertCircle className="h-8 w-8 text-destructive" />
            )}
          </div>
          <h2 className="mb-2 text-xl font-semibold text-foreground">
            {status === "approved"
              ? "Summary Approved & Sent"
              : "Summary Flagged for Review"}
          </h2>
          <p className="mb-6 text-muted-foreground">
            {status === "approved"
              ? "The patient summary has been approved and queued for delivery."
              : "This report has been flagged and returned to the processing queue."}
          </p>
          <Button 
            onClick={resetReview} 
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Review Another Report
          </Button>
        </div>
      </div>
    );
  }

  // No reports available (but backend is connected)
  if (reports.length === 0 && !error && !isCreatingNew) {
    return (
      <div className="flex h-screen flex-col bg-background">
        <header className="border-b border-border bg-primary px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-foreground" />
            <h1 className="text-lg font-semibold text-primary-foreground">
              Radiology AI Summary Review
            </h1>
          </div>
        </header>
        <div className="flex flex-1 overflow-hidden">
          <ReportsSidebar
            reports={reports}
            currentReportId={selectedReportId || ""}
            onReportSelect={(id) => {
              setSelectedReportId(id);
              setIsCreatingNew(false);
            }}
            onCreateNew={() => {
              setIsCreatingNew(true);
              setSelectedReportId(null);
              setCurrentReport(null);
            }}
          />
          <main className="flex-1 overflow-y-auto px-6 py-6">
            <div className="mx-auto max-w-2xl">
              <div className="text-center mb-8">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-foreground mb-2">No Reports Available</h2>
                <p className="text-muted-foreground mb-6">
                  Click "Submit New Report" in the sidebar to get started.
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  // Creating new report mode
  if (isCreatingNew) {
    return (
      <div className="flex h-screen flex-col bg-background">
        <header className="border-b border-border bg-primary px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-foreground" />
            <h1 className="text-lg font-semibold text-primary-foreground">
              Radiology AI Summary Review
            </h1>
          </div>
        </header>
        <div className="flex flex-1 overflow-hidden">
          <ReportsSidebar
            reports={reports}
            currentReportId={selectedReportId || ""}
            onReportSelect={(id) => {
              setSelectedReportId(id);
              setIsCreatingNew(false);
            }}
            onCreateNew={() => {
              setIsCreatingNew(true);
              setSelectedReportId(null);
              setCurrentReport(null);
            }}
          />
          <main className="flex-1 overflow-y-auto px-6 py-6">
            <div className="mx-auto max-w-2xl">
              <SubmitReportForm 
                forceOpen={true}
                onSuccess={(summaryId) => {
                  refreshReports(summaryId);
                  setIsCreatingNew(false);
                }} 
              />
            </div>
          </main>
        </div>
      </div>
    );
  }

  // No report selected or loading
  if (!currentReport || loadingReport) {
    return (
      <div className="flex h-screen flex-col bg-background">
        <header className="border-b border-border bg-primary px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-foreground" />
            <h1 className="text-lg font-semibold text-primary-foreground">
              Radiology AI Summary Review
            </h1>
          </div>
        </header>
        <div className="flex flex-1 overflow-hidden">
          <ReportsSidebar
            reports={reports}
            currentReportId={selectedReportId || ""}
            onReportSelect={(id) => {
              setSelectedReportId(id);
              setIsCreatingNew(false);
            }}
            onCreateNew={() => {
              setIsCreatingNew(true);
              setSelectedReportId(null);
              setCurrentReport(null);
            }}
          />
          <main className="flex-1 overflow-y-auto px-6 py-6">
            {loadingReport ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
                  <p className="text-muted-foreground">Loading report...</p>
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-2xl">
                <div className="text-center mb-8">
                  <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h2 className="text-xl font-semibold text-foreground mb-2">Select a Report</h2>
                  <p className="text-muted-foreground mb-6">
                    Choose a report from the sidebar, or submit a new one to generate an AI summary.
                  </p>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-primary px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary-foreground" />
              <h1 className="text-lg font-semibold text-primary-foreground">
                Radiology AI Summary Review
              </h1>
            </div>
            <span className="text-primary-foreground/70">|</span>
            <span className="text-sm text-primary-foreground/80">
              Patient ID: {currentReport?.patientId || "Unknown"}
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-primary-foreground/80">
              <User className="h-4 w-4" />
              <span>Dr. Sarah Chen</span>
            </div>
            <div className="flex items-center gap-2 rounded-md bg-primary-foreground/10 px-3 py-1.5">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-primary-foreground hover:bg-primary-foreground/20"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm font-medium text-primary-foreground">
                {queuePosition.current} / {queuePosition.total}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-primary-foreground hover:bg-primary-foreground/20"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content with Sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <ReportsSidebar
          reports={reports}
          currentReportId={selectedReportId || ""}
          onReportSelect={(id) => {
            setSelectedReportId(id);
            setIsCreatingNew(false);
          }}
          onCreateNew={() => {
            setIsCreatingNew(true);
            setSelectedReportId(null);
            setCurrentReport(null);
          }}
        />

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-7xl space-y-6">
          {/* Validation Status */}
          <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-muted-foreground">
                Validation Checks:
              </span>
              <ValidationBadges checks={currentReport?.validationChecks || []} />
            </div>
            <div className="text-xs text-muted-foreground">
              Report Date: {currentReport?.date || "N/A"}
            </div>
          </div>

          {/* Two-Column Layout */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Original Report */}
            <ReportPanel
              title="Original Radiologist Report"
              content={currentReport?.originalReport || ""}
              highlightedSentences={getHighlightedOriginalSentences()}
              variant="original"
            />

            {/* AI Summary or Edit Panel */}
            {isEditing ? (
              <EditPanel
                value={editedSummary}
                onChange={setEditedSummary}
              />
            ) : (
              <ReportPanel
                title="Validated AI Patient Summary"
                content={currentReport?.aiSummary || ""}
                highlightedSentences={getHighlightedSummarySentences()}
                onSentenceHover={setHoveredSentence}
                variant="summary"
              />
            )}
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between rounded-lg border-t border-border/50 bg-card p-4">
            <div className="flex items-center gap-2 rounded-lg bg-primary/5 border border-primary/20 px-3 py-2">
              <Lightbulb className="h-4 w-4 text-amber-500 shrink-0" />
              <div className="text-xs">
                <span className="font-semibold text-foreground">Tip: </span>
                <span className="text-muted-foreground">Hover over summary sentences to see their source in the original report</span>
              </div>
            </div>
            
            <ActionButtons
              isEditing={isEditing}
              onApprove={handleApprove}
              onEdit={handleEdit}
              onReject={handleReject}
              onSaveEdit={handleSaveEdit}
              onCancelEdit={handleCancelEdit}
            />
          </div>

          {/* Entity Extraction Panel */}
          <EntityList entities={currentReport?.entities || {
            findings: [],
            anatomy: [],
            measurements: [],
            uncertainty: [],
          }} />
          </div>
        </main>
      </div>
    </div>
  );
}
